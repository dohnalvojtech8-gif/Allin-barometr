"""Private delivery history, atomic multi-store receipts and physical bar transfers."""
import base64
import binascii
import copy
import hashlib
import json
import math
import re
import time
from datetime import datetime,timezone
from flask import g,request,jsonify,send_from_directory,make_response

TABLES=[
'''CREATE TABLE IF NOT EXISTS stock_deliveries (id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,supplier TEXT NOT NULL,reference TEXT NOT NULL,note TEXT NOT NULL,delivered_at TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL,actor_id TEXT NOT NULL,actor_name TEXT NOT NULL,items_json TEXT NOT NULL,request_hash TEXT NOT NULL,source_key TEXT,UNIQUE(owner_id,source_key))''',
'CREATE INDEX IF NOT EXISTS delivery_owner_date ON stock_deliveries(owner_id,delivered_at,id)',
'''CREATE TABLE IF NOT EXISTS delivery_attachments (id TEXT PRIMARY KEY,delivery_id TEXT NOT NULL REFERENCES stock_deliveries(id),owner_id TEXT NOT NULL,jpeg TEXT NOT NULL,filename TEXT NOT NULL,byte_count INTEGER NOT NULL,created_at DOUBLE PRECISION NOT NULL,actor_id TEXT NOT NULL,actor_name TEXT NOT NULL)''',
'CREATE INDEX IF NOT EXISTS delivery_attachment_parent ON delivery_attachments(delivery_id,created_at)',
'''CREATE TABLE IF NOT EXISTS bar_stock_transfers (id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,target_user_id TEXT NOT NULL,details_json TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL,actor_id TEXT NOT NULL,actor_name TEXT NOT NULL,request_hash TEXT NOT NULL)''',
'CREATE INDEX IF NOT EXISTS bar_transfer_owner_time ON bar_stock_transfers(owner_id,created_at)']
COLOR_TABLE='''CREATE TABLE IF NOT EXISTS owner_delivery_colors (owner_id TEXT NOT NULL,venue_id TEXT NOT NULL REFERENCES allin_venues(id) ON DELETE CASCADE,color TEXT NOT NULL,PRIMARY KEY(owner_id,venue_id))'''
PALETTE=['#2563eb','#0f766e','#9333ea','#c2410c','#be185d','#047857','#b45309','#4f46e5']

def fingerprint(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def actor(user):return (user.get('first_name','')+' '+user.get('last_name','')).strip() or user['username']
def owner():return g.user.get('stock_owner_id') or g.user['id']

def photo(value):
    from server.app import ApiError
    if not isinstance(value,dict):raise ApiError('Neplatná fotografie faktury.')
    image=value.get('image','');name=value.get('name','Faktura.jpg');id=value.get('id')
    if not isinstance(id,str) or not re.fullmatch(r'[a-zA-Z0-9-]{10,100}',id):raise ApiError('Neplatné označení přílohy.')
    if not isinstance(name,str) or len(name)>150 or any(ord(c)<32 for c in name):raise ApiError('Neplatný název přílohy.')
    if not isinstance(image,str) or not image.startswith('data:image/jpeg;base64,') or len(image)>600000:raise ApiError('Fotografie musí být JPEG do 450 kB.')
    try:raw=base64.b64decode(image.split(',',1)[1],validate=True)
    except (ValueError,binascii.Error):raise ApiError('Neplatná fotografie faktury.')
    if len(raw)>450000 or not raw.startswith(b'\xff\xd8') or not raw.endswith(b'\xff\xd9'):raise ApiError('Fotografie musí být JPEG do 450 kB.')
    return {'id':id,'name':name,'image':image,'bytes':len(raw)}

def insert_photo(c,delivery,p,user):
    from server.app import execute,one,ApiError
    execute(c,'UPDATE stock_deliveries SET created_at=created_at WHERE id=%s',(delivery['id'],))
    existing=one(c,'SELECT * FROM delivery_attachments WHERE id=%s',(p['id'],))
    if existing:
        if existing['delivery_id']!=delivery['id'] or existing['owner_id']!=delivery['owner_id'] or existing['jpeg']!=p['image'] or existing['filename']!=p['name']:raise ApiError('Označení přílohy už bylo použito.',409)
        return
    if one(c,'SELECT COUNT(*) AS n FROM delivery_attachments WHERE delivery_id=%s',(delivery['id'],))['n']>=6:raise ApiError('U dodávky může být nejvýše 6 fotografií.')
    execute(c,'INSERT INTO delivery_attachments (id,delivery_id,owner_id,jpeg,filename,byte_count,created_at,actor_id,actor_name) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',(p['id'],delivery['id'],delivery['owner_id'],p['image'],p['name'],p['bytes'],time.time(),user['id'],actor(user)))

def snapshot(c,owner_id,id,supplier,reference,note,at,items,user,request_hash,source=None,created=None):
    from server.app import execute
    row={'id':id,'owner_id':owner_id}
    execute(c,'INSERT INTO stock_deliveries (id,owner_id,supplier,reference,note,delivered_at,created_at,actor_id,actor_name,items_json,request_hash,source_key) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(id,owner_id,supplier,reference,note,at,created or time.time(),user['id'],actor(user),json.dumps(items,ensure_ascii=False),request_hash,source))
    return row

def capture_receipts(c,before,after,owner_id):
    """Backfill legacy receipts and capture receipts written by the PIN terminal."""
    from server.app import allrows
    prior={r['id'] for r in before.get('moves',[])};known=allrows(c,'SELECT id,source_key FROM stock_deliveries WHERE owner_id=%s',(owner_id,))
    ids={r['id'] for r in known};sources={r['source_key'] for r in known};groups={}
    for m in after.get('moves',[]):
        if m['id'] in prior or m['reason']!='Příjem' or m['qty']<=0 or m.get('deliveryId') in ids:continue
        key='delivery:'+m['deliveryId'] if m.get('deliveryId') else 'move:'+m['id']
        if key not in sources:groups.setdefault(key,[]).append(m)
    products={p['id']:p for p in after['products']};stores={s['id']:s for s in after['stores']}
    for key,moves in groups.items():
        first=moves[0];items=[{'id':m['id'],'product':m['product'],'store':m['store'],'name':products.get(m['product'],{}).get('name','Produkt'),'storeName':stores.get(m['store'],{}).get('name','Sklad'),'unit':products.get(m['product'],{}).get('unit','ks'),'qty':m['qty']} for m in moves]
        user={'id':first.get('actorId',''),'first_name':first.get('actorName',''),'last_name':'','username':'Autor staršího záznamu není evidován'}
        snapshot(c,owner_id,'legacy-'+fingerprint([owner_id,key])[:32],first.get('supplier',''),first.get('reference',''),first.get('note',''),first['at'],items,user,fingerprint(moves),key,first.get('recordedAt'))

def visible(row,scope):return scope is None or {i['store'] for i in json.loads(row['items_json'])}.issubset(scope)

def public(row):
    items=json.loads(row['items_json'])
    return {'id':row['id'],'supplier':row['supplier'],'reference':row['reference'],'note':row['note'],'at':row['delivered_at'],'createdAt':row['created_at'],'actorId':row['actor_id'],'actorName':row['actor_name'],'items':items,'stores':list({i['store']:i['storeName'] for i in items}.items()),'photoCount':row.get('photo_count',0),'legacy':bool(row['source_key'])}

def rows(c,owner_id,scope=None):
    from server.app import allrows
    return [public(r) for r in allrows(c,'SELECT d.*,(SELECT COUNT(*) FROM delivery_attachments a WHERE a.delivery_id=d.id) AS photo_count FROM stock_deliveries d WHERE d.owner_id=%s ORDER BY d.delivered_at DESC,d.id DESC',(owner_id,)) if visible(r,scope)]

def filtered(items,args):
    from server.app import ApiError
    from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
    def normalized(s):
        import unicodedata
        return ''.join(c for c in unicodedata.normalize('NFD',s.casefold()) if not unicodedata.combining(c))
    q=normalized(args.get('q','').strip()[:200]);start=args.get('from','');end=args.get('to','');store=args.get('store','');author=args.get('actor','');supplier=args.get('supplier','')
    try:zone=ZoneInfo(args.get('timeZone','Europe/Prague'))
    except (ZoneInfoNotFoundError,ValueError):raise ApiError('Neplatné časové pásmo.')
    def day(d):return datetime.fromisoformat(d['at'].replace('Z','+00:00')).astimezone(zone).date().isoformat()
    for value in (start,end):
        if value:
            try:datetime.strptime(value,'%Y-%m-%d')
            except ValueError:raise ApiError('Neplatné datum filtru.')
    if start and end and start>end:raise ApiError('Začátek období musí být před jeho koncem.')
    return [d for d in items if (not q or q in normalized(' '.join([d['supplier'],d['reference'],d['note'],d['actorName'],d.get('venueName','')]+[i['name']+' '+i['storeName'] for i in d['items']]))) and (not start or day(d)>=start) and (not end or day(d)<=end) and (not store or any((d.get('venueId','')+':'+i['store'] if d.get('venueId') else i['store'])==store for i in d['items'])) and (not author or d['actorId']==author) and (not supplier or d['supplier']==supplier)]

def page(items,args):
    try:offset=max(0,int(args.get('offset',0)))
    except ValueError:offset=0
    selected=sorted(filtered(items,args),key=lambda d:(d['at'],d['id']),reverse=True)
    options={'suppliers':sorted({d['supplier'] for d in items if d['supplier']}),'actors':list({d['actorId']:d['actorName'] for d in items if d['actorId']}.items()),'stores':list({(d['venueId']+':'+i['store'] if d.get('venueId') else i['store']):((d['venueName']+' · ') if d.get('venueId') else '')+i['storeName'] for d in items for i in d['items']}.items())}
    summaries=[{**{k:v for k,v in d.items() if k!='items'},'itemCount':len(d['items'])} for d in selected[offset:offset+50]]
    return {'deliveries':summaries,'total':len(selected),'offset':offset,'hasMore':offset+50<len(selected),'options':options}

def details(c,row):
    from server.app import allrows
    result=public(row);result['photos']=allrows(c,'SELECT id,filename,byte_count,created_at,actor_id,actor_name FROM delivery_attachments WHERE delivery_id=%s ORDER BY created_at,id',(row['id'],));result['photoCount']=len(result['photos'])
    ids=[i['id'] for i in result['items']];marks=','.join(['%s']*len(ids))
    result['changes']=allrows(c,'SELECT actor_name,created_at,label,field,before_json,after_json FROM stock_change_log WHERE owner_id=%s AND entity_id IN ('+marks+') AND field<>\'cost\' AND (field=\'qty\' OR before_json<>\'null\') ORDER BY created_at DESC,id DESC LIMIT 100',tuple([row['owner_id']]+ids)) if ids else []
    for event in result['changes']:
        event['before']=json.loads(event.pop('before_json'));event['after']=json.loads(event.pop('after_json'))
    return result

def register(app):
    from server.app import db,allrows,one,execute,authenticated,body,ApiError,has_permission,uid,WEB,TEST_DB,SUPABASE_DATABASE_URL,audit,write_stock_changes,stock_latest_changes
    from server.work import store_scope,scoped_stock,local_products
    from server.stock import validate_stock,attribute_records,current_quantity,validate_active_changes
    from server.allin import venue_context
    from server.coowners import owner_scope
    def private(c,tables):
        if not TEST_DB:
            for table in tables:
                execute(c,'ALTER TABLE '+table+' ENABLE ROW LEVEL SECURITY');execute(c,'REVOKE ALL ON '+table+' FROM PUBLIC')
                if SUPABASE_DATABASE_URL:execute(c,'REVOKE ALL ON '+table+' FROM anon,authenticated')
    with db(central=True) as c:
        execute(c,COLOR_TABLE);private(c,['owner_delivery_colors']);venues=allrows(c,'SELECT * FROM allin_venues')
    for venue in venues:
        with app.test_request_context(),venue_context(venue),db() as c:
            for sql in TABLES:execute(c,sql)
            private(c,['stock_deliveries','delivery_attachments','bar_stock_transfers'])
            for doc in allrows(c,'SELECT * FROM stock_documents'):capture_receipts(c,{},json.loads(doc['data_json']),doc['user_id'])
    def load(c):
        if not getattr(g,'venue',None):raise ApiError('Nejprve otevřete provoz.',403)
        row=one(c,'SELECT * FROM stock_documents WHERE user_id=%s',(owner(),))
        return row,json.loads(row['data_json']) if row else {'stores':[{'id':'main','name':'Hlavní sklad'}],'products':[],'counts':[],'moves':[],'draft':None,'barInventories':[],'barDraft':None}
    def get_delivery(c,id):
        if not getattr(g,'venue',None):raise ApiError('Nejprve otevřete provoz.',403)
        row=one(c,'SELECT * FROM stock_deliveries WHERE id=%s AND owner_id=%s',(id,owner()))
        if not row or not visible(row,store_scope(c,g.user)):raise ApiError('Dodávka není dostupná.',404)
        return row
    def save(c,original,data,revision):
        execute(c,'INSERT INTO stock_documents (user_id,revision,data_json,updated_at) VALUES (%s,0,%s,%s) ON CONFLICT(user_id) DO NOTHING',(owner(),json.dumps(original),time.time()))
        n=execute(c,'UPDATE stock_documents SET data_json=%s,revision=revision+1,updated_at=%s WHERE user_id=%s AND revision=%s',(json.dumps(data,ensure_ascii=False),time.time(),owner(),revision)).rowcount
        if n!=1:raise ApiError('Sklad se mezitím změnil. Obnovte přehled a potvrďte znovu.',409)
        write_stock_changes(c,owner(),original,data,revision+1)
        out=scoped_stock(data,store_scope(c,g.user));return {'ok':True,'data':out,'revision':revision+1,'latestChanges':stock_latest_changes(c,owner(),out)}
    def text(values,key,limit):
        value=values.get(key,'')
        if not isinstance(value,str) or len(value)>limit or any(ord(c)<32 and c not in '\n\t' for c in value):raise ApiError('Neplatný údaj: '+key)
        return value.strip()

    @app.get('/api/deliveries')
    @authenticated(permission='deliveries.view')
    def delivery_history():
        if not getattr(g,'venue',None):raise ApiError('Nejprve otevřete provoz.',403)
        with db() as c:result=page(rows(c,owner(),store_scope(c,g.user)),request.args)
        return jsonify(**result)
    @app.get('/api/deliveries/<id>')
    @authenticated(permission='deliveries.view')
    def delivery_detail(id):
        with db() as c:result=details(c,get_delivery(c,id))
        return jsonify(delivery=result)
    @app.post('/api/deliveries')
    @authenticated(permission='stock.receive')
    def delivery_receive():
        if not has_permission(g.user,'stock.view'):raise ApiError('Nemáte přístup ke skladu.',403)
        values=body();id=values.get('id');lines=values.get('items');photos=values.get('photos',[])
        if not isinstance(id,str) or not re.fullmatch(r'[a-zA-Z0-9-]{10,100}',id) or not isinstance(lines,list) or not 1<=len(lines)<=1000 or not isinstance(photos,list) or len(photos)>6 or type(values.get('revision')) is not int:raise ApiError('Vyplňte položky dodávky.')
        supplier=text(values,'supplier',150);reference=text(values,'reference',150);note=text(values,'note',500);photos=[photo(p) for p in photos]
        if len({p['id'] for p in photos})!=len(photos):raise ApiError('Přílohy nesmějí mít stejné označení.')
        request_hash=fingerprint({'items':lines,'supplier':supplier,'reference':reference,'note':note,'photos':photos})
        with db() as c:
            execute(c,'UPDATE users SET last_seen=last_seen WHERE id=%s',(owner(),))
            previous=one(c,'SELECT * FROM stock_deliveries WHERE id=%s',(id,))
            if previous:
                if previous['owner_id']!=owner() or not visible(previous,store_scope(c,g.user)):raise ApiError('Dodávka není dostupná.',404)
                if previous['request_hash']!=request_hash:raise ApiError('Toto označení dodávky už bylo použito.',409)
                row,data=load(c);return jsonify(ok=True,duplicate=True,deliveryId=id,data=scoped_stock(data,store_scope(c,g.user)),revision=row['revision'],latestChanges=stock_latest_changes(c,owner(),scoped_stock(data,store_scope(c,g.user))))
            row,original=load(c);revision=row['revision'] if row else 0
            if revision!=values['revision']:raise ApiError('Stav skladu se změnil. Obnovte přehled dodávky.',409)
            data=copy.deepcopy(original);scope=store_scope(c,g.user);at=datetime.now(timezone.utc).isoformat();items=[];seen=set()
            for line in lines:
                if not isinstance(line,dict) or type(line.get('qty')) not in (float,int) or not math.isfinite(line['qty']) or not 0<line['qty']<=1e12:raise ApiError('Zadejte kladné přijímané množství.')
                sid=line.get('store');p=next((p for p in local_products(data,sid) if p['id']==line.get('product')),None);s=next((s for s in data['stores'] if s['id']==sid and not s.get('archivedAt')),None)
                if not p or not s or (scope is not None and sid not in scope):raise ApiError('Položka nepatří do dostupného aktivního skladu.',403)
                key=(sid,p['id'])
                if key in seen:raise ApiError('Stejnou položku ve skladu uveďte pouze jednou.')
                seen.add(key);qty=line['qty']
                physical=qty*(p.get('packSize',1) if p['unit']=='balení' else 1)
                if p.get('catalogProductId') and p['unit'] in ('ks','balení') and abs(physical-round(physical))>1e-8:raise ApiError('Počet lahví musí být celé číslo.')
                move={'id':uid(),'deliveryId':id,'store':sid,'product':p['id'],'qty':qty,'reason':'Příjem','supplier':supplier,'reference':reference,'at':at}
                data['moves'].append(move);items.append({'id':move['id'],'store':sid,'storeName':s['name'],'product':p['id'],'name':p['name'],'qty':qty,'unit':p['unit']})
            try:data=attribute_records(original,validate_stock(data),g.user);validate_active_changes(original,data)
            except ValueError as error:raise ApiError(str(error))
            delivery=snapshot(c,owner(),id,supplier,reference,note,at,items,g.user,request_hash)
            for p in photos:insert_photo(c,delivery,p,g.user)
            result=save(c,original,data,revision);audit(c,g.user['id'],'delivery_received','Příjem celé dodávky '+id+' do '+str(len({i['store'] for i in items}))+' skladů')
        return jsonify(**result,deliveryId=id),201
    @app.post('/api/deliveries/<id>/photos')
    @authenticated(permission='stock.receive')
    def delivery_attach(id):
        if not has_permission(g.user,'deliveries.view'):raise ApiError('Nemáte přístup k historii dodávek.',403)
        p=photo(body())
        with db() as c:
            delivery=get_delivery(c,id);insert_photo(c,delivery,p,g.user);audit(c,g.user['id'],'invoice_attached','Přiložení fotografie faktury k dodávce '+id)
        return jsonify(ok=True,id=p['id'])
    @app.get('/api/deliveries/<id>/photos/<photo_id>')
    @authenticated(permission='deliveries.view')
    def delivery_download(id,photo_id):
        with db() as c:
            get_delivery(c,id);p=one(c,'SELECT jpeg FROM delivery_attachments WHERE id=%s AND delivery_id=%s AND owner_id=%s',(photo_id,id,owner()))
        if not p:raise ApiError('Fotografie není dostupná.',404)
        response=make_response(base64.b64decode(p['jpeg'].split(',',1)[1]));response.headers.update({'Content-Type':'image/jpeg','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'});return response

    @app.post('/api/stock/to-bar')
    @authenticated(permission='stock.move')
    def delivery_to_bar():
        if not has_permission(g.user,'inventory.bar') or not has_permission(g.user,'inventory.run') or not has_permission(g.user,'stock.view'):raise ApiError('Nemáte oprávnění používat bar.',403)
        values=body();id=values.get('id');number=values.get('bottles');request_hash=fingerprint({k:values.get(k) for k in ('store','product','bottles')})
        if not isinstance(id,str) or not re.fullmatch(r'[a-zA-Z0-9-]{10,100}',id) or type(number) is not int or not 1<=number<=100 or type(values.get('revision')) is not int:raise ApiError('Zadejte celý počet lahví (1–100).')
        from server.bar_stock import state_user
        with db() as c:
            execute(c,'UPDATE users SET last_seen=last_seen WHERE id=%s',(owner(),))
            prior=one(c,'SELECT * FROM bar_stock_transfers WHERE id=%s',(id,))
            if prior:
                if prior['owner_id']!=owner() or prior['target_user_id']!=state_user(g.user) or prior['request_hash']!=request_hash:raise ApiError('Označení přesunu už bylo použito.',409)
                row,data=load(c);return jsonify(ok=True,duplicate=True,data=scoped_stock(data,store_scope(c,g.user)),revision=row['revision'],latestChanges=stock_latest_changes(c,owner(),scoped_stock(data,store_scope(c,g.user))),transfer=json.loads(prior['details_json']))
            row,original=load(c);revision=row['revision'] if row else 0
            if revision!=values['revision']:raise ApiError('Sklad se mezitím změnil. Obnovte přehled přesunu.',409)
            sid=values.get('store');p=next((p for p in local_products(original,sid) if p['id']==values.get('product')),None);s=next((s for s in original['stores'] if s['id']==sid and not s.get('archivedAt')),None);scope=store_scope(c,g.user)
            if not p or not s or (scope is not None and sid not in scope):raise ApiError('Ke skladu nemáte přístup.',403)
            from server.app import PRODUCTS
            catalog=PRODUCTS.get(p.get('catalogProductId'));size=p.get('catalogCapacityMl')
            if not catalog or size not in [v['ml'] for v in catalog['variants']]:raise ApiError('Nejprve propojte produkt s lahví a její velikostí v úpravě produktu.')
            unit=p['unit'];pack=p.get('packSize',1)
            if unit not in ('ks','balení','l','ml') or (unit=='balení' and (pack<=0 or not float(pack).is_integer())):raise ApiError('Pro přesun lahví použijte kusy, celá balení, litry nebo mililitry.')
            amount=number if unit=='ks' else number/pack if unit=='balení' else number*size/(1000 if unit=='l' else 1)
            current=current_quantity(original,p['id'],sid)
            if current is None or current+1e-9<amount:raise ApiError('Ve skladu není dostatek lahví.')
            account=one(c,'SELECT * FROM users WHERE id=%s',(state_user(g.user),));old_state=account['state_json'];state=json.loads(old_state);state.setdefault('rows',[])
            if len(state['rows'])+number>500:raise ApiError('Bar obsahuje příliš mnoho lahví. Nejprve dokončete inventuru.')
            if len(state.get('inventoryPlan',{}).get('entries',[]))+number>500:raise ApiError('Plán inventury obsahuje příliš mnoho lahví.')
            bottle_ids=[]
            for index in range(number):
                bottle_id='b-'+uid();bottle_ids.append(bottle_id);state['rows'].append({'id':bottle_id,'productId':catalog['id'],'capacity':size,'label':p['name']+' · '+str(index+1),'start':size,'ml':size,'sold40':0,'sold20':0,'otherMl':0,'stockTransferId':id})
                if state.get('inventoryPlan',{}).get('entries') is not None:state['inventoryPlan']['entries'].append({'id':uid(),'rowId':bottle_id,'productId':catalog['id'],'capacity':size,'label':p['name'],'status':'pending'})
            now=time.time();at=datetime.now(timezone.utc).isoformat();data=copy.deepcopy(original)
            data['moves'].append({'id':id,'transferId':id,'transferTarget':'bar','barBottles':number,'bottleMl':size,'product':p['id'],'store':sid,'qty':-amount,'reason':'Přesun','note':'Přesun lahví ze skladu na bar','at':at})
            try:data=attribute_records(original,validate_stock(data),g.user)
            except ValueError as error:raise ApiError(str(error))
            details={'id':id,'name':p['name'],'store':sid,'storeName':s['name'],'bottles':number,'bottleMl':size,'before':current,'after':max(0,current-amount),'unit':unit,'rowIds':bottle_ids,'actorName':actor(g.user),'at':at}
            result=save(c,original,data,revision)
            if execute(c,'UPDATE users SET state_json=%s WHERE id=%s AND state_json=%s',(json.dumps(state,ensure_ascii=False),state_user(g.user),old_state)).rowcount!=1:raise ApiError('Bar se mezitím změnil. Obnovte přehled.',409)
            for product_id in [catalog['id']]:execute(c,'INSERT INTO unlocks (user_id,product_id,created_at) VALUES (%s,%s,%s) ON CONFLICT(user_id,product_id) DO NOTHING',(state_user(g.user),product_id,now))
            execute(c,'INSERT INTO bar_stock_transfers (id,owner_id,target_user_id,details_json,created_at,actor_id,actor_name,request_hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',(id,owner(),state_user(g.user),json.dumps(details,ensure_ascii=False),now,g.user['id'],actor(g.user),request_hash));audit(c,g.user['id'],'bottles_to_bar','Přesun '+str(number)+' lahví '+p['name']+' ze skladu '+s['name']+' na bar')
        return jsonify(**result,transfer=details)

    @app.get('/api/owner/deliveries')
    @authenticated(admin=True)
    def delivery_owner_history():
        if getattr(g,'venue',None):raise ApiError('Otevřete centrální panel majitele.',403)
        with db(central=True) as c:
            venues=allrows(c,'SELECT * FROM allin_venues WHERE owner_id=%s ORDER BY created_at,id',(owner_scope(),));colors={r['venue_id']:r['color'] for r in allrows(c,'SELECT * FROM owner_delivery_colors WHERE owner_id=%s',(owner_scope(),))}
        choice=request.args.get('venue','all')
        if choice!='all' and choice not in {v['id'] for v in venues}:raise ApiError('Provoz není dostupný.',404)
        items=[];options=[]
        for index,venue in enumerate(venues):
            color=colors.get(venue['id'],PALETTE[index%len(PALETTE)]);options.append({'id':venue['id'],'name':venue['name'],'color':color})
            if choice!='all' and choice!=venue['id']:continue
            with venue_context(venue),db() as c:items.extend({**r,'venueId':venue['id'],'venueName':venue['name'],'color':color} for r in rows(c,owner_scope()))
        result=page(items,request.args);result['venues']=options
        return jsonify(**result)
    @app.put('/api/owner/venues/<id>/delivery-color')
    @authenticated(admin=True)
    def delivery_color(id):
        if getattr(g,'venue',None):raise ApiError('Otevřete centrální panel majitele.',403)
        value=body().get('color')
        if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value):raise ApiError('Vyberte platnou barvu.')
        with db(central=True) as c:
            if not one(c,'SELECT id FROM allin_venues WHERE id=%s AND owner_id=%s',(id,owner_scope())):raise ApiError('Provoz není dostupný.',404)
            execute(c,'INSERT INTO owner_delivery_colors (owner_id,venue_id,color) VALUES (%s,%s,%s) ON CONFLICT(owner_id,venue_id) DO UPDATE SET color=excluded.color',(owner_scope(),id,value));audit(c,g.user['id'],'delivery_color_changed','Změna barvy dodávek provozu '+id+' na '+value)
        return jsonify(ok=True,color=value)
    def owned_venue(id):
        if getattr(g,'venue',None):raise ApiError('Otevřete centrální panel majitele.',403)
        with db(central=True) as c:venue=one(c,'SELECT * FROM allin_venues WHERE id=%s AND owner_id=%s',(id,owner_scope()))
        if not venue:raise ApiError('Provoz není dostupný.',404)
        return venue
    @app.get('/api/owner/deliveries/<venue_id>/<id>')
    @authenticated(admin=True)
    def delivery_owner_detail(venue_id,id):
        venue=owned_venue(venue_id)
        with venue_context(venue),db() as c:result=details(c,get_delivery(c,id))
        return jsonify(delivery={**result,'venueId':venue_id,'venueName':venue['name']})
    @app.get('/api/owner/deliveries/<venue_id>/<id>/photos/<photo_id>')
    @authenticated(admin=True)
    def delivery_owner_photo(venue_id,id,photo_id):
        venue=owned_venue(venue_id)
        with venue_context(venue):return delivery_download.__wrapped__(id,photo_id)
    @app.post('/api/owner/deliveries/<venue_id>/<id>/photos')
    @authenticated(admin=True)
    def delivery_owner_attach(venue_id,id):
        venue=owned_venue(venue_id)
        with venue_context(venue):return delivery_attach.__wrapped__(id)
    @app.get('/deliveries.js')
    def delivery_script():return send_from_directory(WEB,'deliveries.js')
    @app.get('/api/owner/opening-status')
    @authenticated(admin=True)
    def opening_owner_status():
        if getattr(g,'venue',None):raise ApiError('Otevřete centrální panel majitele.',403)
        from server.controls import opening_status
        with db(central=True) as c:venues=allrows(c,'SELECT id,opening_hours_json FROM allin_venues WHERE owner_id=%s AND archived_at IS NULL',(owner_scope(),))
        return jsonify(venues=[{'id':v['id'],'status':opening_status(json.loads(v['opening_hours_json'] or '{}'))} for v in venues])
    @app.get('/api/venue/opening-status')
    @authenticated()
    def opening_venue_status():
        if not getattr(g,'venue',None):raise ApiError('Otevřete svůj provoz.',404)
        from server.controls import opening_status
        return jsonify(status=opening_status(json.loads(g.venue.get('opening_hours_json') or '{}')))
    @app.get('/opening-hours.js')
    def opening_hours_script():return send_from_directory(WEB,'opening-hours.js')
    @app.get('/daylight.css')
    def daylight_styles():return send_from_directory(WEB,'daylight.css')
