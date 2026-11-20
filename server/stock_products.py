"""Warehouse product setup, activated bar catalog and venue-local keg calibration."""
import copy
import json
import math
import time
from datetime import datetime,timezone
from flask import g,request,jsonify,send_from_directory

DEFAULT_CATEGORIES=[{'name':'Obal','kind':'piece'},{'name':'Sud','kind':'keg'},{'name':'Lihoviny','kind':'liquid'}]
TABLES=[
"""CREATE TABLE IF NOT EXISTS stock_keg_profiles (id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,origin_store TEXT NOT NULL,source_product TEXT NOT NULL,name TEXT NOT NULL,reference_id TEXT NOT NULL,capacity DOUBLE PRECISION NOT NULL,tare DOUBLE PRECISION NOT NULL,full_weight DOUBLE PRECISION NOT NULL,density DOUBLE PRECISION NOT NULL,updated_at DOUBLE PRECISION NOT NULL,actor_id TEXT NOT NULL,actor_name TEXT NOT NULL)""",
'CREATE INDEX IF NOT EXISTS stock_keg_owner ON stock_keg_profiles(owner_id,origin_store)',
"""CREATE TABLE IF NOT EXISTS stock_keg_readings (id TEXT PRIMARY KEY,profile_id TEXT NOT NULL REFERENCES stock_keg_profiles(id),owner_id TEXT NOT NULL,store_id TEXT NOT NULL,product_id TEXT NOT NULL,gross DOUBLE PRECISION NOT NULL,reading_role TEXT NOT NULL,parameters_json TEXT NOT NULL,actor_id TEXT NOT NULL,actor_name TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL)""",
'CREATE INDEX IF NOT EXISTS stock_keg_history ON stock_keg_readings(profile_id,created_at)']

def categories(store):
    return copy.deepcopy(store.get('categories',DEFAULT_CATEGORIES))

def active_catalog(c,owner):
    from server.app import allrows,PRODUCTS
    ids={r['product_id'] for r in allrows(c,'SELECT DISTINCT l.product_id FROM unlocks l JOIN users u ON u.id=l.user_id WHERE u.id=%s OR u.stock_owner_id=%s',(owner,owner))}
    return [{'id':p['id'],'name':p['name'],'variants':[{'ml':v['ml']} for v in p['variants']]} for id,p in PRODUCTS.items() if id in ids]

def validate_links(c,before,after,owner):
    from server.app import ApiError,PRODUCTS
    previous={p['id']:p for p in before.get('products',[])};active={p['id'] for p in active_catalog(c,owner)}
    from server.work import store_scope
    available={r['id'] for r in profiles(c,before,owner,store_scope(c,g.user))}
    for p in after['products']:
        if p.get('kegProfileId') and p.get('kegProfileId')!=previous.get(p['id'],{}).get('kegProfileId') and p['kegProfileId'] not in available:raise ApiError('Vyberte uložený sud dostupný v tomto provozu.')
        id=p.get('catalogProductId');old=previous.get(p['id'],{})
        if not id:continue
        if (id,p.get('catalogCapacityMl'))!=(old.get('catalogProductId'),old.get('catalogCapacityMl')):
            if id not in active:raise ApiError('Vyberte lihovinu aktivovanou pro tento bar.')
        if id not in PRODUCTS or p.get('catalogCapacityMl') not in [v['ml'] for v in PRODUCTS[id]['variants']]:raise ApiError('Neplatná velikost propojené lahve.')

def profiles(c,data,owner,scope=None):
    from server.app import allrows
    allowed={s['id'] for s in data['stores'] if scope is None or s['id'] in scope};out={}
    for p in data['products']:
        if p.get('kind')!='keg' or p.get('store') not in allowed:continue
        id=p.get('kegProfileId') or 'keg:'+p['id']
        out.setdefault(id,{'id':id,'name':p['name'],'capacity':p['capacity'],'tare':p['tare'],'fullWeightKg':p.get('fullWeightKg',0),'density':p['density'],'referenceId':p.get('referenceId',''),'measured':False})
    for row in allrows(c,'SELECT * FROM stock_keg_profiles WHERE owner_id=%s ORDER BY name,id',(owner,)):
        if row['origin_store'] in allowed:
            out[row['id']]={'id':row['id'],'name':row['name'],'capacity':row['capacity'],'tare':row['tare'],'fullWeightKg':row['full_weight'],'density':row['density'],'referenceId':row['reference_id'],'measured':True,'updatedAt':row['updated_at']}
    return list(out.values())

def save_keg_reading(c,data,owner,values):
    from server.app import ApiError,has_permission,execute,one,uid,audit
    from server.work import store_scope
    if not isinstance(values,dict):raise ApiError('Neplatný záznam vážení sudu.')
    target=values.get('target','stock');permission='inventory.bar' if target=='bar' else 'inventory.warehouse'
    if not has_permission(g.user,'inventory.run') or not has_permission(g.user,permission):raise ApiError('Nemáte oprávnění ukládat vážení.',403)
    p=next((p for p in data['products'] if p['id']==values.get('productId') and p['kind']=='keg'),None)
    sid=values.get('storeId');scope=store_scope(c,g.user)
    if not p or p.get('store')!=sid or (scope is not None and sid not in scope):raise ApiError('Sud nepatří do dostupného skladu.',403)
    fields={k:values.get(k) for k in ('gross','tare','fullWeightKg','capacity','density')}
    if any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1e9 for v in fields.values()) or fields['density']<=0:raise ApiError('Neplatné hmotnosti nebo objem sudu.')
    role=values.get('readingRole','partial')
    if role not in ('partial','full','empty'):raise ApiError('Vyberte typ váženého sudu.')
    if role=='empty':fields['tare']=fields['gross']
    if role=='full':fields['fullWeightKg']=fields['gross']
    if fields['fullWeightKg'] and fields['fullWeightKg']<=fields['tare']:raise ApiError('Plný sud musí vážit více než prázdný.')
    if fields['gross']<fields['tare']:raise ApiError('Aktuální hmotnost je menší než hmotnost prázdného sudu.')
    id=p.get('kegProfileId') or 'keg:'+p['id'];existing=one(c,'SELECT * FROM stock_keg_profiles WHERE id=%s',(id,))
    if existing and existing['owner_id']!=owner:raise ApiError('Profil sudu nepatří do tohoto provozu.',403)
    name=existing['name'] if existing else p['name'];source=existing['source_product'] if existing else p['id'];origin=existing['origin_store'] if existing else sid
    actor=(g.user['first_name']+' '+g.user['last_name']).strip() or g.user['username'];now=time.time()
    execute(c,'INSERT INTO stock_keg_profiles (id,owner_id,origin_store,source_product,name,reference_id,capacity,tare,full_weight,density,updated_at,actor_id,actor_name) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET capacity=excluded.capacity,tare=excluded.tare,full_weight=excluded.full_weight,density=excluded.density,updated_at=excluded.updated_at,actor_id=excluded.actor_id,actor_name=excluded.actor_name',
            (id,owner,origin,source,name,p.get('referenceId',''),fields['capacity'],fields['tare'],fields['fullWeightKg'],fields['density'],now,g.user['id'],actor))
    execute(c,'INSERT INTO stock_keg_readings (id,profile_id,owner_id,store_id,product_id,gross,reading_role,parameters_json,actor_id,actor_name,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(uid(),id,owner,sid,p['id'],fields['gross'],role,json.dumps(fields),g.user['id'],actor,now))
    p.update(tare=fields['tare'],fullWeightKg=fields['fullWeightKg'],capacity=fields['capacity'],density=fields['density'],kegProfileId=id)
    audit(c,g.user['id'],'keg_weighed','Uložení vážení sudu: '+name)

def register(app):
    from server.app import authenticated,db,one,allrows,execute,body,ApiError,uid,TEST_DB,SUPABASE_DATABASE_URL,WEB,has_permission,audit,write_stock_changes,stock_latest_changes
    from server.work import store_scope,scoped_stock
    from server.allin import venue_context
    from server.stock import validate_stock,prepare_counts,attribute_records
    with db(central=True) as c:venues=allrows(c,'SELECT * FROM allin_venues')
    for venue in venues:
        with app.test_request_context(),venue_context(venue),db() as c:
            for sql in TABLES:execute(c,sql)
            if not TEST_DB:
                for table in ('stock_keg_profiles','stock_keg_readings'):
                    execute(c,'ALTER TABLE '+table+' ENABLE ROW LEVEL SECURITY');execute(c,'REVOKE ALL ON '+table+' FROM PUBLIC')
                    if SUPABASE_DATABASE_URL:execute(c,'REVOKE ALL ON '+table+' FROM anon,authenticated')
    def owner():return g.user.get('stock_owner_id') or g.user['id']
    def document(c):
        row=one(c,'SELECT * FROM stock_documents WHERE user_id=%s',(owner(),))
        return row,json.loads(row['data_json']) if row else {'stores':[{'id':'main','name':'Hlavní sklad'}],'products':[],'counts':[],'moves':[],'draft':None,'barInventories':[]}
    @app.get('/api/stock/resources')
    @authenticated(permission='stock.view')
    def resources():
        with db() as c:
            row,data=document(c);scope=store_scope(c,g.user);sid=request.args.get('store','')
            target=next((s for s in data['stores'] if s['id']==sid),None) if sid else None
            if sid and (not target or (scope is not None and sid not in scope)):raise ApiError('Ke skladu nemáte přístup.',403)
            return jsonify(categories=categories(target) if target else DEFAULT_CATEGORIES,kegs=profiles(c,data,owner(),scope),catalog=active_catalog(c,owner()))
    @app.post('/api/stock/products')
    @authenticated(permission='stock.edit')
    def create_product():
        if not has_permission(g.user,'stock.view'):raise ApiError('Nemáte přístup ke skladu.',403)
        values=body();quantity=values.get('openingQty',0)
        if type(quantity) not in (int,float) or not math.isfinite(quantity) or not 0<=quantity<=1e12:raise ApiError('Zadejte nezáporný prvotní stav.')
        if quantity>0 and not has_permission(g.user,'stock.receive'):raise ApiError('Nemáte oprávnění k prvotnímu zaskladnění.',403)
        if not isinstance(values.get('product'),dict) or type(values.get('revision')) is not int:raise ApiError('Neplatné údaje produktu.')
        with db() as c:
            row,before=document(c);revision=row['revision'] if row else 0
            if revision!=values['revision']:raise ApiError('Sklad se mezitím změnil. Obnovte formulář.',409)
            product={**values['product'],'id':values['product'].get('id') or uid()};sid=product.get('store');scope=store_scope(c,g.user)
            if not any(s['id']==sid and not s.get('archivedAt') for s in before['stores']) or (scope is not None and sid not in scope):raise ApiError('Ke skladu nemáte přístup.',403)
            if any(p['id']==product['id'] for p in before['products']):raise ApiError('Produkt již existuje.',409)
            after=copy.deepcopy(before);after['products'].append(product)
            try:after=validate_stock(after);validate_links(c,before,after,owner())
            except ValueError as error:raise ApiError(str(error))
            if product.get('catalogProductId') and product['unit'] in ('ks','balení') and not float(quantity).is_integer():raise ApiError('Počet lahví nebo balení musí být celé číslo.')
            count={'id':uid(),'inventoryId':'opening-'+product['id'],'store':sid,'product':product['id'],'qty':quantity,'at':datetime.now(timezone.utc).isoformat(),'kind':'warehouse','method':'Prvotní stav při vytvoření produktu'}
            after['counts'].append(count);after=validate_stock(after);after=prepare_counts(before,attribute_records(before,after,g.user));count['opening']=True
            if not row:execute(c,'INSERT INTO stock_documents (user_id,revision,data_json,updated_at) VALUES (%s,0,%s,%s)',(owner(),json.dumps(before),time.time()))
            changed=execute(c,'UPDATE stock_documents SET data_json=%s,revision=revision+1,updated_at=%s WHERE user_id=%s AND revision=%s',(json.dumps(after,ensure_ascii=False),time.time(),owner(),revision)).rowcount
            if changed!=1:raise ApiError('Sklad se mezitím změnil. Zopakujte založení produktu.',409)
            write_stock_changes(c,owner(),before,after,revision+1);audit(c,g.user['id'],'stock_product_created','Vytvoření skladového produktu: '+product['name'])
            visible=scoped_stock(after,scope)
            return jsonify(ok=True,revision=revision+1,data=visible,latestChanges=stock_latest_changes(c,owner(),visible),productId=product['id']),201
    @app.get('/stock-products.js')
    def stock_products_script():return send_from_directory(WEB,'stock-products.js')
    @app.get('/stock-products.css')
    def stock_products_styles():return send_from_directory(WEB,'stock-products.css')
