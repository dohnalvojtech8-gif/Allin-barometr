"""Venue-scoped inventory submission, review and append-only decision audit."""
import copy
import json
import math
import time
from flask import g,request,jsonify,send_from_directory

TABLES=[
"""CREATE TABLE IF NOT EXISTS inventory_submissions (id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,kind TEXT NOT NULL,stores_json TEXT NOT NULL,content_json TEXT NOT NULL,status TEXT NOT NULL,revision INTEGER NOT NULL,submitted_by TEXT NOT NULL,submitted_name TEXT NOT NULL,submitted_at DOUBLE PRECISION NOT NULL,updated_at DOUBLE PRECISION NOT NULL,reviewed_by TEXT,reviewed_name TEXT,reviewed_at DOUBLE PRECISION,decision_reason TEXT NOT NULL DEFAULT '')""",
'CREATE INDEX IF NOT EXISTS inventory_submission_status ON inventory_submissions(owner_id,status,submitted_at)',
"""CREATE TABLE IF NOT EXISTS inventory_review_events (id TEXT PRIMARY KEY,submission_id TEXT NOT NULL REFERENCES inventory_submissions(id),action TEXT NOT NULL,actor_id TEXT NOT NULL,actor_name TEXT NOT NULL,reason TEXT NOT NULL,snapshot_json TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL)""",
'CREATE INDEX IF NOT EXISTS inventory_review_history ON inventory_review_events(submission_id,created_at,id)']

def actor_name(user):
    return (user.get('first_name','')+' '+user.get('last_name','')).strip() or user['username']

def event(c,row,action,reason,content):
    from server.app import execute,uid,audit
    execute(c,'INSERT INTO inventory_review_events (id,submission_id,action,actor_id,actor_name,reason,snapshot_json,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
            (uid(),row['id'],action,g.user['id'],actor_name(g.user),reason,json.dumps(content,ensure_ascii=False),time.time()))
    audit(c,g.user['id'],'inventory_'+action,reason+' · '+row['id'])

def notify(c,row):
    from server.app import execute,uid
    venue=getattr(g,'venue',None)
    if not venue:return
    payload={'title':venue['name']+' · inventura ke kontrole','body':'Zaměstnanec odeslal inventuru ke schválení.','url':'/v/'+venue['id']+'/#audits','stores':json.loads(row['stores_json']),'requiredPermission':'inventory.review'}
    execute(c,'INSERT INTO notification_outbox (id,kind,payload_json,created_at) VALUES (%s,%s,%s,%s)',(uid(),'inventory_review',json.dumps(payload,ensure_ascii=False),time.time()))
    g.notification_changes=True

def stage(c,before,after,owner):
    """Employee measurement is durable but does not change approved stock balances."""
    from server.app import execute,one,ApiError,uid
    if not getattr(g,'venue',None) or g.user['role']=='admin':return after
    old_counts={r['id'] for r in before.get('counts',[])}
    old_bars={r['id'] for r in before.get('barInventories',[])}
    new_counts=[r for r in after['counts'] if r['id'] not in old_counts]
    new_bars=[r for r in after['barInventories'] if r['id'] not in old_bars]
    groups={}
    for bar in new_bars:
        groups[bar['id']]={'counts':[],'bars':[bar]}
    for count in new_counts:
        key=count.get('inventoryId') or count['id']
        groups.setdefault(key,{'counts':[],'bars':[]})['counts'].append(count)
    for key,content in groups.items():
        if one(c,'SELECT id FROM inventory_submissions WHERE id=%s',(key,)):
            raise ApiError('Tato inventura již byla odeslána ke kontrole.',409)
        for collection in content.values():
            for item in collection:item.pop('reviewId',None)
        stores={r['store'] for r in content['counts']}
        for bar in content['bars']:
            for item in bar.get('items',[]):
                if item.get('store'):stores.add(item['store'])
        # Unassigned bottle measurements require access to the complete venue.
        if any(not i.get('store') for b in content['bars'] for i in b.get('items',[])):
            stores.update(s['id'] for s in after['stores'])
        from server.work import store_scope
        scope=store_scope(c,g.user)
        if scope is not None and not stores.issubset(scope):raise ApiError('Přiřaďte každé položce inventury dostupný sklad.',403)
        now=time.time();row={'id':key,'stores_json':json.dumps(sorted(stores))}
        kind='bar' if content['bars'] or any(r.get('kind')=='bar' for r in content['counts']) else 'warehouse'
        execute(c,'INSERT INTO inventory_submissions (id,owner_id,kind,stores_json,content_json,status,revision,submitted_by,submitted_name,submitted_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,1,%s,%s,%s,%s)',
                (key,owner,kind,row['stores_json'],json.dumps(content,ensure_ascii=False),'pending',g.user['id'],actor_name(g.user),now,now))
        event(c,row,'submitted','Odeslání inventury ke schválení',content);notify(c,row)
        g.pending_inventory_ids=getattr(g,'pending_inventory_ids',[])+[key]
    after['counts']=[r for r in after['counts'] if r['id'] in old_counts]
    after['barInventories']=[r for r in after['barInventories'] if r['id'] in old_bars]
    return after

def protect_closed(before,after,reason):
    from server.app import ApiError
    for key in ('counts','barInventories'):
        previous={r['id']:r for r in before.get(key,[])}
        current={r['id']:r for r in after.get(key,[])}
        if any(r.get('reviewId') and current.get(id)!=r for id,r in previous.items()):
            if not isinstance(reason,str) or not 5<=len(reason.strip())<=500:
                raise ApiError('U opravy schválené inventury uveďte důvod (5–500 znaků).')
            return True
    return False

def register(app):
    from server.app import db,execute,one,allrows,ApiError,authenticated,body,uid,TEST_DB,SUPABASE_DATABASE_URL,WEB,write_stock_changes
    from server.permissions import has_permission
    from server.work import store_scope
    from server.allin import venue_context
    from server.stock import validate_stock,current_quantity
    with db(central=True) as c:venues=allrows(c,'SELECT * FROM allin_venues')
    for venue in venues:
        with app.test_request_context(),venue_context(venue),db() as c:
            for sql in TABLES:execute(c,sql)
            if not TEST_DB:
                for table in ('inventory_submissions','inventory_review_events'):
                    execute(c,'ALTER TABLE '+table+' ENABLE ROW LEVEL SECURITY');execute(c,'REVOKE ALL ON '+table+' FROM PUBLIC')
                    if SUPABASE_DATABASE_URL:execute(c,'REVOKE ALL ON '+table+' FROM anon,authenticated')

    def owner_id():return g.user.get('stock_owner_id') or g.user['id']
    def allowed(c,row,review=False):
        if not row or row['owner_id']!=owner_id():raise ApiError('Inventura neexistuje.',404)
        scope=store_scope(c,g.user)
        if scope is not None and not set(json.loads(row['stores_json'])).issubset(scope):raise ApiError('Ke všem skladům inventury nemáte přístup.',403)
        if review:
            if not has_permission(g.user,'inventory.review'):raise ApiError('Nemáte oprávnění schvalovat inventury.',403)
            if row['submitted_by']==g.user['id'] and g.user['role']!='admin':raise ApiError('Vlastní inventuru musí zkontrolovat jiný schvalovatel.',403)
        elif row['submitted_by']!=g.user['id'] and not (has_permission(g.user,'inventory.history') or has_permission(g.user,'inventory.review')):raise ApiError('Nemáte oprávnění zobrazit tuto inventuru.',403)
    def public(row):
        result=dict(row);result['content']=json.loads(result.pop('content_json'));result['stores']=json.loads(result.pop('stores_json'));return result

    @app.get('/api/inventory/submissions')
    @authenticated(permission='stock.view')
    def submissions():
        with db() as c:
            rows=allrows(c,'SELECT * FROM inventory_submissions WHERE owner_id=%s ORDER BY submitted_at DESC,id',(owner_id(),))
            visible=[]
            for row in rows:
                try:allowed(c,row)
                except ApiError:continue
                visible.append(public(row))
        return jsonify(submissions=visible,canReview=has_permission(g.user,'inventory.review'))

    @app.get('/api/inventory/submissions/<id>')
    @authenticated(permission='stock.view')
    def detail(id):
        with db() as c:
            row=one(c,'SELECT * FROM inventory_submissions WHERE id=%s',(id,));allowed(c,row)
            if row['status']=='approved':
                saved=one(c,'SELECT data_json FROM stock_documents WHERE user_id=%s',(owner_id(),))
                current=json.loads(saved['data_json']) if saved else {}
                row['content_json']=json.dumps({'counts':[r for r in current.get('counts',[]) if r.get('reviewId')==id],'bars':[r for r in current.get('barInventories',[]) if r.get('reviewId')==id]})
            events=allrows(c,'SELECT id,action,actor_id,actor_name,reason,snapshot_json,created_at FROM inventory_review_events WHERE submission_id=%s ORDER BY created_at,id',(id,))
        return jsonify(submission=public(row),events=[{**{k:v for k,v in e.items() if k!='snapshot_json'},'snapshot':json.loads(e['snapshot_json'])} for e in events])

    @app.post('/api/inventory/submissions/<id>/decision')
    @authenticated(permission='inventory.review')
    def decision(id):
        values=body();action=values.get('action');reason=values.get('reason','').strip() if isinstance(values.get('reason',''),str) else ''
        if action not in ('approve','return'):raise ApiError('Vyberte schválení nebo vrácení k opravě.')
        if type(values.get('revision')) is not int:raise ApiError('Chybí revize inventury.')
        if len(reason)>500 or (action=='return' and len(reason)<5):raise ApiError('U vrácení uveďte důvod (5–500 znaků).')
        with db() as c:
            execute(c,'UPDATE users SET last_seen=last_seen WHERE id=%s',(owner_id(),))
            row=one(c,'SELECT * FROM inventory_submissions WHERE id=%s',(id,));allowed(c,row,review=True)
            if row['status']!='pending' or row['revision']!=values['revision']:raise ApiError('Inventura se mezitím změnila. Obnovte seznam.',409)
            content=json.loads(row['content_json'])
            if action=='approve':
                saved=one(c,'SELECT * FROM stock_documents WHERE user_id=%s',(owner_id(),))
                old=json.loads(saved['data_json']) if saved else {'stores':[],'products':[],'counts':[],'moves':[],'draft':None,'barInventories':[]}
                new=copy.deepcopy(old)
                count_ids={r['id'] for r in old['counts']};bar_ids={r['id'] for r in old.get('barInventories',[])}
                if any(r['id'] in count_ids for r in content['counts']) or any(r['id'] in bar_ids for r in content['bars']):raise ApiError('Inventura už je v uzavřených zásobách.',409)
                # Count time stays the measurement time, even if stock moved while waiting.
                new['counts'].extend({**r,'reviewId':id} for r in content['counts'])
                new.setdefault('barInventories',[]).extend({**r,'reviewId':id} for r in content['bars'])
                try:new=validate_stock(new)
                except ValueError:raise ApiError('Skladové položky se změnily. Vraťte inventuru k opravě.',409)
                revision=saved['revision'] if saved else 0
                if not saved:execute(c,'INSERT INTO stock_documents (user_id,revision,data_json,updated_at) VALUES (%s,0,%s,%s)',(owner_id(),json.dumps(old),time.time()))
                changed=execute(c,'UPDATE stock_documents SET data_json=%s,revision=revision+1,updated_at=%s WHERE user_id=%s AND revision=%s',(json.dumps(new,ensure_ascii=False),time.time(),owner_id(),revision)).rowcount
                if changed!=1:raise ApiError('Sklad se změnil. Zopakujte kontrolu.',409)
                write_stock_changes(c,owner_id(),old,new,revision+1)
            now=time.time();status='approved' if action=='approve' else 'returned';reason=reason or 'Schváleno po kontrole odchylek'
            changed=execute(c,'UPDATE inventory_submissions SET status=%s,revision=revision+1,reviewed_by=%s,reviewed_name=%s,reviewed_at=%s,updated_at=%s,decision_reason=%s WHERE id=%s AND revision=%s AND status=%s',(status,g.user['id'],actor_name(g.user),now,now,reason,id,row['revision'],'pending')).rowcount
            if changed!=1:raise ApiError('Rozhodnutí již uložil jiný uživatel.',409)
            event(c,row,status,reason,content)
        return jsonify(ok=True,status=status)

    @app.post('/api/inventory/submissions/<id>/resubmit')
    @authenticated(permission='inventory.run')
    def resubmit(id):
        values=body();reason=values.get('reason','')
        if not isinstance(reason,str) or not 5<=len(reason.strip())<=500:raise ApiError('U opravy uveďte důvod (5–500 znaků).')
        if type(values.get('revision')) is not int or not isinstance(values.get('quantities'),dict):raise ApiError('Neplatná oprava inventury.')
        with db() as c:
            row=one(c,'SELECT * FROM inventory_submissions WHERE id=%s',(id,));allowed(c,row)
            if row['submitted_by']!=g.user['id'] and g.user['role']!='admin':raise ApiError('Opravu provede autor inventury nebo majitel.',403)
            required='inventory.bar' if row['kind']=='bar' else 'inventory.warehouse'
            if not has_permission(g.user,required):raise ApiError('K tomuto typu inventury nemáte oprávnění.',403)
            if row['status']!='returned' or row['revision']!=values['revision']:raise ApiError('Opravovat lze pouze vrácenou inventuru v aktuální revizi.',409)
            content=json.loads(row['content_json']);items={r['id']:r for r in content['counts']}
            for bar in content['bars']:
                for i,item in enumerate(bar['items']):items[bar['id']+':'+str(i)]=item
            quantities=values['quantities']
            if set(quantities)!=set(items) or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1e12 for v in quantities.values()):raise ApiError('Zadejte nezáporná množství všech položek.')
            for key,item in items.items():item['qty']=quantities[key]
            # Weighted bar lines are represented once in each format; keep both consistent.
            for bar in content['bars']:
                for item in bar['items']:
                    matches=[r for r in content['counts'] if r.get('inventoryId')==bar['id'] and r['product']==item.get('product') and r['store']==item.get('store')]
                    if matches and abs(sum(r['qty'] for r in matches)-item['qty'])>1e-8:raise ApiError('Množství ve skladu a souhrnu baru se musí shodovat.')
            changed=execute(c,"UPDATE inventory_submissions SET content_json=%s,status='pending',revision=revision+1,updated_at=%s WHERE id=%s AND revision=%s AND status='returned'",(json.dumps(content,ensure_ascii=False),time.time(),id,row['revision'])).rowcount
            if changed!=1:raise ApiError('Inventura se mezitím změnila.',409)
            event(c,row,'resubmitted',reason.strip(),content);notify(c,row)
        return jsonify(ok=True)

    @app.get('/intelligence.js')
    def intelligence_script():return send_from_directory(WEB,'intelligence.js')
