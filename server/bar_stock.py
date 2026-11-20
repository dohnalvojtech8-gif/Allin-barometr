"""Bottle-size summaries, stock snapshots and durable zero-bottle archival."""
import copy
import json
import math
import time
from collections import defaultdict
from datetime import datetime,timezone
from flask import g,request,jsonify,send_from_directory

TABLES=[
"""CREATE TABLE IF NOT EXISTS bar_bottle_depletions (id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,user_id TEXT NOT NULL,row_id TEXT NOT NULL,catalog_product_id TEXT NOT NULL,capacity_ml INTEGER NOT NULL,bottle_json TEXT NOT NULL,emptied_at DOUBLE PRECISION NOT NULL,actor_name TEXT NOT NULL,reported_inventory_id TEXT,voided_at DOUBLE PRECISION)""",
'CREATE INDEX IF NOT EXISTS bar_bottle_period ON bar_bottle_depletions(owner_id,reported_inventory_id,emptied_at)',
"""CREATE TABLE IF NOT EXISTS bar_archived_bottles (owner_id TEXT NOT NULL,user_id TEXT NOT NULL,row_id TEXT NOT NULL,inventory_id TEXT NOT NULL,bottle_json TEXT NOT NULL,archived_at DOUBLE PRECISION NOT NULL,PRIMARY KEY(user_id,row_id,inventory_id))"""]

def state_user(user):
    return (user.get('stock_owner_id') or user['id']) if user['role']=='admin' else user['id']

def protect_archived(c,user,before,after):
    from server.app import allrows,ApiError
    active={r['id'] for r in before.get('rows',[])}
    archived={r['row_id'] for r in allrows(c,'SELECT DISTINCT row_id FROM bar_archived_bottles WHERE user_id=%s',(state_user(user),))}
    if any(r['id'] in archived and r['id'] not in active for r in after.get('rows',[])):
        raise ApiError('Prázdná lahev už byla archivována s inventurou. Obnovte stránku; novou lahev založte samostatně.',409)

def record_depletions(c,user,before,after):
    from server.app import execute,uid
    owner=user.get('stock_owner_id') or user['id'];previous={r['id']:r for r in before.get('rows',[])};created=[]
    for row in after.get('rows',[]):
        old=previous.get(row['id'])
        if old and old.get('ml')==0 and row.get('ml',0)>0:
            execute(c,'UPDATE bar_bottle_depletions SET voided_at=%s WHERE owner_id=%s AND user_id=%s AND row_id=%s AND reported_inventory_id IS NULL AND voided_at IS NULL',(time.time(),owner,state_user(user),row['id']))
        if old and old.get('ml',0)>0 and row.get('ml')==0:
            id=uid();created.append(id)
            execute(c,'INSERT INTO bar_bottle_depletions (id,owner_id,user_id,row_id,catalog_product_id,capacity_ml,bottle_json,emptied_at,actor_name) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                    (id,owner,state_user(user),row['id'],row['productId'],row['capacity'],json.dumps(row,ensure_ascii=False),time.time(),(user['first_name']+' '+user['last_name']).strip() or user['username']))
    return created

def summarize(items,depletions):
    from server.app import PRODUCTS
    groups={}
    def group(id,size):
        key=(id,size)
        return groups.setdefault(key,{'catalogProductId':id,'name':PRODUCTS.get(id,{}).get('name',id),'bottleMl':size,'barMl':0,'stockMl':0,'barBottles':0,'stockBottles':0,'fullBottles':0,'partialBottles':0,'emptyBottles':0,'consumedBottles':0,'countsKnown':True,'volumeKnown':True})
    for item in items:
        id=item.get('catalogProductId');size=item.get('bottleMl')
        if not id or not size:continue
        row=group(id,size);qty=item['qty']
        if item.get('source')=='bar':
            ml=qty*1000 if item['unit']=='l' else qty
            row['barMl']+=ml;row['barBottles']+=1
            row['emptyBottles' if ml==0 else 'fullBottles' if abs(ml-size)<.001 else 'partialBottles']+=1
        elif item.get('source')=='stock_snapshot':
            unit=item['unit'];known=item.get('known',True)
            if known and unit in ('ks','balení'):
                number=qty*(item.get('packSize',1) if unit=='balení' else 1)
                if abs(number-round(number))<1e-8:row['stockBottles']+=round(number);row['fullBottles']+=round(number)
                else:row['countsKnown']=False
                row['stockMl']+=number*size
            elif known and unit in ('l','ml'):
                row['stockMl']+=qty*(1000 if unit=='l' else 1);row['countsKnown']=False
            else:row['countsKnown']=False;row['volumeKnown']=False
    for event in depletions:group(event['catalog_product_id'],event['capacity_ml'])['consumedBottles']+=1
    for row in groups.values():
        row['totalBottles']=row['barBottles']+row['stockBottles'] if row['countsKnown'] else None
        row['totalMl']=row['barMl']+row['stockMl'] if row['volumeKnown'] else None
    return list(groups.values())

def prepare_run(c,document,run,user,include_live=True):
    from server.app import one,allrows,uid,ApiError,PRODUCTS,has_permission
    from server.stock import current_quantity
    owner=user.get('stock_owner_id') or user['id'];run=copy.deepcopy(run)
    run['items']=[item for item in run['items'] if item.get('source')!='stock_snapshot']
    user_row=one(c,'SELECT state_json FROM users WHERE id=%s',(state_user(user),));state=json.loads(user_row['state_json']) if user_row else {}
    active={r['id']:r for r in state.get('rows',[])};seen=set();archived=[];projected=[]
    for item in run['items']:
        if item.get('source')!='bar':continue
        id=item.get('catalogProductId');size=item.get('bottleMl');catalog=PRODUCTS.get(id)
        if not catalog or size not in [v['ml'] for v in catalog['variants']] or item['unit'] not in ('l','ml'):raise ApiError('Neplatné propojení nebo velikost lahve na baru.')
        ml=item['qty']*(1000 if item['unit']=='l' else 1)
        if not 0<=ml<=size:raise ApiError('Obsah lahve překračuje její velikost.')
        item['name']=catalog['name'];row_id=item.get('barRowId') or item['id'];item['barRowId']=row_id;seen.add(row_id)
        row=active.get(row_id)
        if not row and 'originalMl' in item:raise ApiError('Lahev již není v aktivním provozu. Obnovte přehled.',409)
        if row and (row['productId']!=id or row['capacity']!=size):raise ApiError('Lahev neodpovídá aktivnímu měření.')
        if row:
            if 'originalMl' in item and item['originalMl']!=row['ml']:raise ApiError('Měření lahve se mezitím změnilo. Obnovte přehled.',409)
            item['originalMl']=row['ml']
            if ml!=row['ml'] and (not isinstance(run.get('adjustmentReason'),str) or not 5<=len(run['adjustmentReason'].strip())<=500):raise ApiError('U úpravy měření uveďte důvod (5–500 znaků).')
            if row['ml']>0 and ml==0:projected.append({'catalog_product_id':id,'capacity_ml':size})
            if ml==0:archived.append({'userId':state_user(user),'bottle':{**row,'ml':0}})
    if include_live:
        for row in active.values():
            if row.get('ml')!=0:continue
            if row['id'] in seen and any(i.get('barRowId')==row['id'] and i['qty']>0 for i in run['items']):continue
            if not any(a['bottle']['id']==row['id'] for a in archived):archived.append({'userId':state_user(user),'bottle':copy.deepcopy(row)})
            if row['id'] not in seen:
                run['items'].append({'id':'empty:'+row['id'],'barRowId':row['id'],'catalogProductId':row['productId'],'bottleMl':row['capacity'],'name':PRODUCTS[row['productId']]['name'],'qty':0,'unit':'ml','expected':None,'cost':0,'source':'bar'})
        events=allrows(c,'SELECT * FROM bar_bottle_depletions WHERE owner_id=%s AND reported_inventory_id IS NULL AND voided_at IS NULL ORDER BY emptied_at,id',(owner,))
        restored={i['barRowId'] for i in run['items'] if i.get('source')=='bar' and i.get('originalMl')==0 and i['qty']>0}
        events=[e for e in events if not(e['user_id']==state_user(user) and e['row_id'] in restored)]
    else:
        events=allrows(c,'SELECT * FROM bar_bottle_depletions WHERE owner_id=%s AND reported_inventory_id=%s AND voided_at IS NULL ORDER BY emptied_at,id',(owner,run['id']))
    for event in events:
        archived.append({'userId':event['user_id'],'bottle':json.loads(event['bottle_json']),'depletionId':event['id'],'emptiedAt':event['emptied_at']})
    run['archivedEmptyBottles']=archived;run['consumptionEventIds']=[event['id'] for event in events]
    selected={item['catalogProductId'] for item in run['items'] if item.get('source')=='bar'}|{e['catalog_product_id'] for e in events}
    overrides=run.get('stockCounts',{})
    if not isinstance(overrides,dict):raise ApiError('Neplatné počty skladových lahví.')
    applicable={p['id']:p for p in document['products'] if p.get('catalogProductId') in selected and p.get('catalogCapacityMl') and any(s['id']==p.get('store') and not s.get('archivedAt') for s in document['stores'])}
    if set(overrides)-set(applicable):raise ApiError('Úprava obsahuje nesouvisející skladový produkt.')
    counts=[]
    for p in applicable.values():
        current=current_quantity(document,p['id'],p['store']);quantity=overrides.get(p['id'],current)
        if p['id'] in overrides:
            if not has_permission(user,'inventory.warehouse') or not has_permission(user,'inventory.run'):raise ApiError('Nemáte oprávnění upravovat skladovou inventuru.',403)
            if type(quantity) not in (int,float) or not math.isfinite(quantity) or not 0<=quantity<=1e12:raise ApiError('Zadejte nezáporné množství ve skladu.')
            if p['unit'] in ('ks','balení') and not float(quantity).is_integer():raise ApiError('Počet skladových lahví nebo balení musí být celé číslo.')
            if quantity!=current:counts.append({'id':uid(),'inventoryId':run['id'],'store':p['store'],'product':p['id'],'kind':'warehouse','qty':quantity,'at':run['at'],'method':'Kontrola skladových lahví při inventuře baru'})
        run['items'].append({'id':'stock:'+p['id'],'source':'stock_snapshot','stockProductId':p['id'],'store':p['store'],'catalogProductId':p['catalogProductId'],'bottleMl':p['catalogCapacityMl'],'name':p['name'],'qty':quantity if quantity is not None else 0,'known':quantity is not None,'unit':p['unit'],'packSize':p.get('packSize',1),'expected':None,'cost':0})
    run['bottleSummary']=summarize(run['items'],events+projected)
    return run,counts

def prepare_new_runs(c,before,after,user):
    previous={r['id'] for r in before.get('barInventories',[])}
    for index,run in enumerate(after.get('barInventories',[])):
        if run['id'] not in previous:
            prepared,counts=prepare_run(c,before,run,user);after['barInventories'][index]=prepared;after['counts'].extend(counts)
    return after

def archive_runs(c,before,after,user):
    from server.app import execute,one,allrows,ApiError,audit
    previous={r['id'] for r in before.get('barInventories',[])};owner=user.get('stock_owner_id') or user['id']
    for run in after.get('barInventories',[]):
        if run['id'] in previous:continue
        for id in run.get('consumptionEventIds',[]):
            n=execute(c,'UPDATE bar_bottle_depletions SET reported_inventory_id=%s WHERE id=%s AND owner_id=%s AND reported_inventory_id IS NULL AND voided_at IS NULL',(run['id'],id,owner)).rowcount
            if n!=1:raise ApiError('Prázdnou lahev již zahrnula jiná inventura. Zkontrolujte nový přehled.',409)
        by_user=defaultdict(set)
        for item in run.get('archivedEmptyBottles',[]):by_user[item['userId']].add(item['bottle']['id'])
        changes={item['barRowId']:item for item in run['items'] if item.get('source')=='bar' and 'originalMl' in item and item['qty']*(1000 if item['unit']=='l' else 1)!=item['originalMl']}
        if changes:by_user[state_user(user)].update(changes)
        for user_id,ids in by_user.items():
            account=one(c,'SELECT * FROM users WHERE id=%s AND (id=%s OR stock_owner_id=%s)',(user_id,owner,owner))
            if not account:continue
            state=json.loads(account['state_json']);previous_state=copy.deepcopy(state)
            if user_id==state_user(user):
                for row in state.get('rows',[]):
                    item=changes.get(row['id'])
                    if not item:continue
                    if row['ml']!=item['originalMl']:raise ApiError('Měření se mezitím změnilo. Obnovte přehled.',409)
                    row['ml']=item['qty']*(1000 if item['unit']=='l' else 1)
                new_events=record_depletions(c,user,previous_state,state)
                for event_id in new_events:
                    execute(c,'UPDATE bar_bottle_depletions SET reported_inventory_id=%s WHERE id=%s',(run['id'],event_id));run['consumptionEventIds'].append(event_id)
                if changes:audit(c,user['id'],'bar_measurement_adjusted',run['adjustmentReason'].strip())
            removed={r['id'] for r in state.get('rows',[]) if r['id'] in ids and r.get('ml')==0}
            if not removed and state==previous_state:continue
            for bottle in state.get('rows',[]):
                if bottle['id'] in removed:
                    execute(c,'INSERT INTO bar_archived_bottles (owner_id,user_id,row_id,inventory_id,bottle_json,archived_at) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(user_id,row_id,inventory_id) DO NOTHING',(owner,user_id,bottle['id'],run['id'],json.dumps(bottle,ensure_ascii=False),time.time()))
            state['rows']=[r for r in state.get('rows',[]) if r['id'] not in removed]
            if state.get('inventoryPlan'):state['inventoryPlan']['entries']=[e for e in state['inventoryPlan']['entries'] if e.get('rowId') not in removed]
            n=execute(c,'UPDATE users SET state_json=%s WHERE id=%s AND state_json=%s',(json.dumps(state,ensure_ascii=False),user_id,account['state_json'])).rowcount
            if n!=1:raise ApiError('Bar se mezitím změnil. Zopakujte kontrolu inventury.',409)
            audit(c,user['id'],'empty_bottles_archived','Archivace prázdných lahví s inventurou '+run['id']+': '+str(len(removed)))
        events=allrows(c,'SELECT * FROM bar_bottle_depletions WHERE owner_id=%s AND reported_inventory_id=%s AND voided_at IS NULL',(owner,run['id']))
        run['bottleSummary']=summarize(run['items'],events)

def restore_corrections(c,owner,author,content,reason):
    from server.app import one,allrows,execute,ApiError,has_permission,uid
    for run in content.get('bars',[]):
        original=one(c,'SELECT content_json FROM inventory_submissions WHERE id=%s',(run['id'],))
        old_bars=json.loads(original['content_json'])['bars'] if original else []
        old_items={item['id']:item for bar in old_bars for item in bar['items']}
        for item in run['items']:
            if item.get('source')!='stock_snapshot':continue
            matched=next((r for r in content['counts'] if r.get('inventoryId')==run['id'] and r['product']==item['stockProductId'] and r['store']==item['store']),None)
            if matched and matched['qty']!=item['qty']:raise ApiError('Počet skladových lahví a souhrn se musí shodovat.')
            if item['qty']!=old_items.get(item['id'],{}).get('qty'):
                if not has_permission(g.user,'inventory.warehouse'):raise ApiError('Nemáte oprávnění opravovat počty ve skladu.',403)
                if item['unit'] in ('ks','balení') and not float(item['qty']).is_integer():raise ApiError('Počet lahví musí být celé číslo.')
                if not matched:content['counts'].append({'id':uid(),'inventoryId':run['id'],'product':item['stockProductId'],'store':item['store'],'qty':item['qty'],'at':run['at'],'kind':'warehouse','actorId':author,'actorName':g.user['first_name']+' '+g.user['last_name'],'recordedAt':time.time(),'method':'Oprava počtu skladových lahví'})
        templates={entry['bottle']['id']:entry['bottle'] for entry in run.get('archivedEmptyBottles',[]) if entry['userId']==author}
        account=one(c,'SELECT * FROM users WHERE id=%s AND (id=%s OR stock_owner_id=%s)',(author,owner,owner))
        if not account:continue
        state=json.loads(account['state_json']);ids={r['id'] for r in state.get('rows',[])};changed=False
        for item in run['items']:
            row_id=item.get('barRowId');template=templates.get(row_id)
            if item.get('source')!='bar' or not template:continue
            ml=item['qty']*(1000 if item['unit']=='l' else 1)
            if not 0<=ml<=template['capacity']:raise ApiError('Opravený obsah překračuje velikost lahve.')
            if ml>0 and row_id not in ids:
                state.setdefault('rows',[]).append({**template,'ml':ml});ids.add(row_id);changed=True
                last=one(c,'SELECT id FROM bar_bottle_depletions WHERE owner_id=%s AND user_id=%s AND row_id=%s AND reported_inventory_id=%s AND voided_at IS NULL ORDER BY emptied_at DESC LIMIT 1',(owner,author,row_id,run['id']))
                if last:execute(c,'UPDATE bar_bottle_depletions SET voided_at=%s WHERE id=%s',(time.time(),last['id']))
        if changed:
            if execute(c,'UPDATE users SET state_json=%s WHERE id=%s AND state_json=%s',(json.dumps(state,ensure_ascii=False),author,account['state_json'])).rowcount!=1:raise ApiError('Bar se mezitím změnil.',409)
        events=allrows(c,'SELECT * FROM bar_bottle_depletions WHERE owner_id=%s AND reported_inventory_id=%s AND voided_at IS NULL',(owner,run['id']))
        run['bottleSummary']=summarize(run['items'],events)

def register(app):
    from server.app import db,allrows,execute,one,authenticated,body,ApiError,TEST_DB,SUPABASE_DATABASE_URL,WEB,has_permission
    from server.allin import venue_context
    from server.work import store_scope
    with db(central=True) as c:venues=allrows(c,'SELECT * FROM allin_venues')
    for venue in venues:
        with app.test_request_context(),venue_context(venue),db() as c:
            for sql in TABLES:execute(c,sql)
            if not TEST_DB:
                for table in ('bar_bottle_depletions','bar_archived_bottles'):
                    execute(c,'ALTER TABLE '+table+' ENABLE ROW LEVEL SECURITY');execute(c,'REVOKE ALL ON '+table+' FROM PUBLIC')
                    if SUPABASE_DATABASE_URL:execute(c,'REVOKE ALL ON '+table+' FROM anon,authenticated')
    @app.post('/api/stock/bar-preview')
    @authenticated(permission='inventory.bar')
    def preview():
        if not has_permission(g.user,'inventory.run') or not has_permission(g.user,'stock.view'):raise ApiError('Nemáte oprávnění provádět inventuru baru.',403)
        values=body();run=values.get('bar')
        if not isinstance(run,dict) or not isinstance(run.get('id'),str) or not isinstance(run.get('items'),list) or len(run['items'])>1000:raise ApiError('Neplatná inventura baru.')
        with db() as c:
            owner=g.user.get('stock_owner_id') or g.user['id'];row=one(c,'SELECT * FROM stock_documents WHERE user_id=%s',(owner,))
            if type(values.get('revision')) is not int or values['revision']!=(row['revision'] if row else 0):raise ApiError('Sklad se mezitím změnil. Obnovte přehled.',409)
            if store_scope(c,g.user) is not None:raise ApiError('Inventura celého baru vyžaduje přístup ke všem skladům.',403)
            document=json.loads(row['data_json']) if row else {'stores':[{'id':'main','name':'Hlavní sklad'}],'products':[],'counts':[],'moves':[],'draft':None,'barInventories':[]}
            from server.stock import validate_stock
            test=copy.deepcopy(document);test.setdefault('barInventories',[]).append(run)
            try:validate_stock(test)
            except ValueError as error:raise ApiError(str(error))
            prepared,counts=prepare_run(c,document,run,g.user)
        return jsonify(bar=prepared)
    @app.get('/bar-stock.js')
    def bar_stock_script():return send_from_directory(WEB,'bar-stock.js')
