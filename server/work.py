"""Paired shared terminals, employee PIN sessions and warehouse scopes."""
import copy
import json
import math
import re
import secrets
import time
from datetime import datetime, timezone
from functools import wraps
from flask import request, jsonify, g, send_from_directory

TABLES=[
"CREATE TABLE IF NOT EXISTS work_access (user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,pin_hash TEXT,stores_json TEXT NOT NULL DEFAULT 'null')",
"CREATE TABLE IF NOT EXISTS work_devices (token_hash TEXT PRIMARY KEY,owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,csrf TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL)",
"CREATE TABLE IF NOT EXISTS work_sessions (token_hash TEXT PRIMARY KEY,device_hash TEXT NOT NULL REFERENCES work_devices(token_hash) ON DELETE CASCADE,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,csrf TEXT NOT NULL,last_activity DOUBLE PRECISION NOT NULL)",
"CREATE INDEX IF NOT EXISTS work_sessions_device ON work_sessions(device_hash)",
"CREATE INDEX IF NOT EXISTS work_access_owner ON work_access(owner_id)"
]
DEVICE='barometr_work_device'
SESSION='barometr_work_session'
IDLE=300

def store_scope(c,user):
    from server.app import one
    if user['role']=='admin':return None
    row=one(c,'SELECT owner_id,stores_json FROM work_access WHERE user_id=%s',(user['id'],))
    if not row:return None
    if row['owner_id']!=(user.get('stock_owner_id') or user['id']):return []
    return json.loads(row['stores_json'])

def local_products(data,sid):
    referenced={r['product'] for r in data['counts']+data['moves'] if r['store']==sid}
    used={r['product'] for r in data['counts']+data['moves']}
    return [p for p in data['products'] if p.get('store')==sid or p['id'] in referenced or (not p.get('store') and p['id'] not in used and sid==next(iter(data['stores']),{}).get('id'))]

def scoped_stock(data,scope):
    if scope is None:return copy.deepcopy(data)
    out=copy.deepcopy(data);allowed=set(scope)
    pids={p['id'] for sid in allowed for p in local_products(data,sid)}
    out['stores']=[s for s in out['stores'] if s['id'] in allowed]
    out['products']=[p for p in out['products'] if p['id'] in pids]
    for p in out['products']:
        if p.get('store') not in allowed:p.pop('store',None)
    for key in ('counts','moves'):out[key]=[r for r in out[key] if r['store'] in allowed]
    if out.get('draft',{} ) and out['draft']['store'] not in allowed:out['draft']=None
    out['barInventories']=[];out['barDraft']=None
    return out

def merge_scoped_stock(before,submitted,scope):
    from server.app import ApiError
    if scope is None:return submitted
    visible=scoped_stock(before,scope);allowed=set(scope)
    if any(s['id'] not in allowed for s in submitted['stores']):raise ApiError('Ke skladu nemáte přístup.',403)
    if {s['id'] for s in submitted['stores']}!={s['id'] for s in visible['stores']}:raise ApiError('S tímto přístupem nelze přidávat nebo odstraňovat sklady.',403)
    for key in ('counts','moves'):
        if any(r['store'] not in allowed for r in submitted[key]):raise ApiError('Ke skladu nemáte přístup.',403)
    if submitted.get('draft') and submitted['draft']['store'] not in allowed:raise ApiError('Ke skladu nemáte přístup.',403)
    if submitted.get('barInventories') or submitted.get('barDraft'):raise ApiError('Inventura baru vyžaduje přístup ke všem skladům.',403)
    hidden_pids={r['product'] for r in before['counts']+before['moves'] if r['store'] not in allowed}|{p['id'] for p in before['products'] if p.get('store') and p['store'] not in allowed}
    old_products={p['id']:p for p in visible['products']};new_products={p['id']:p for p in submitted['products']}
    for pid in set(old_products)|set(new_products):
        if old_products.get(pid)!=new_products.get(pid) and (pid in hidden_pids or (new_products.get(pid) and new_products[pid].get('store') not in allowed)):raise ApiError('Sdílený produkt může upravit pouze majitel.',403)
    out=copy.deepcopy(before)
    for key in ('stores','products','counts','moves'):
        visible_ids={r['id'] for r in visible[key]}
        additions=submitted[key]
        if key=='products':
            originals={p['id']:p for p in before['products']}
            additions=[originals[p['id']] if p==old_products.get(p['id']) else p for p in additions]
        replacements={r['id']:r for r in additions};original_ids={r['id'] for r in before[key]}
        out[key]=[replacements[r['id']] if r['id'] in replacements else r for r in before[key] if r['id'] not in visible_ids or r['id'] in replacements]+[r for r in additions if r['id'] not in original_ids]
    if not before.get('draft') or before['draft']['store'] in allowed:out['draft']=submitted.get('draft')
    return out

def register(app):
    from server.app import (db,one,allrows,execute,uid,digest,password_hash,password_ok,ApiError,body,authenticated,has_permission,effective_permissions,audit,SECURE,cookie_name,WEB,rate_limit,client_ip,write_stock_changes,stock_latest_changes)
    from server.stock import current_quantity,validate_stock,prepare_counts,StockValidationError

    def document(c,owner):
        row=one(c,'SELECT data_json,revision FROM stock_documents WHERE user_id=%s',(owner,))
        return (json.loads(row['data_json']),row['revision']) if row else ({'stores':[{'id':'main','name':'Hlavní sklad'}],'products':[],'counts':[],'moves':[],'draft':None,'barInventories':[],'barDraft':None},0)

    def device(c):
        value=one(c,"SELECT d.* FROM work_devices d JOIN users u ON u.id=d.owner_id WHERE d.token_hash=%s AND u.status='active' AND u.role='admin'",(digest(request.cookies.get(DEVICE,'')),))
        if not value:raise ApiError('Majitel musí na tomto zařízení nejprve zapnout pracovní režim.',401)
        return value

    def employee(c,d):
        s=one(c,"SELECT s.*,u.* FROM work_sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=%s AND s.device_hash=%s AND s.last_activity>%s AND u.status='active'",(digest(request.cookies.get(SESSION,'')),d['token_hash'],time.time()-IDLE))
        if not s:return None
        access=one(c,'SELECT * FROM work_access WHERE user_id=%s AND owner_id=%s',(s['user_id'],d['owner_id']))
        if not access or not access['pin_hash'] or (s.get('stock_owner_id') or s['id'])!=d['owner_id']:return None
        return s

    def worker(permission=None):
        def decorate(fn):
            @wraps(fn)
            def wrapped(*args,**kwargs):
                with db() as c:
                    d=device(c);u=employee(c,d)
                    if not u:raise ApiError('Pracovní přístup je zamčený. Zadejte PIN.',401)
                    if permission and not has_permission(u,permission):raise ApiError('K této akci nemáte oprávnění.',403)
                    if request.method!='GET' and not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),u['csrf']):raise ApiError('Obnovte přihlášení PINem.',403)
                    g.user=u;g.work_device=d
                return fn(*args,**kwargs)
            return wrapped
        return decorate

    def check_store(c,data,sid):
        scope=store_scope(c,g.user)
        s=next((s for s in data['stores'] if s['id']==sid and not s.get('archivedAt')),None)
        if not s or (scope is not None and sid not in scope):raise ApiError('Ke skladu nemáte přístup nebo je archivovaný.',403)
        return s

    def save(c,old,new,revision):
        try:
            from server.stock import attribute_records
            new=prepare_counts(old,attribute_records(old,validate_stock(new),g.user))
        except StockValidationError as e:raise ApiError(str(e))
        owner=g.work_device['owner_id']
        from server.reviews import stage
        new=stage(c,old,new,owner)
        execute(c,'INSERT INTO stock_documents (user_id,revision,data_json,updated_at) VALUES (%s,0,%s,%s) ON CONFLICT (user_id) DO NOTHING',(owner,json.dumps(old),time.time()))
        n=execute(c,'UPDATE stock_documents SET data_json=%s,revision=revision+1,updated_at=%s WHERE user_id=%s AND revision=%s',(json.dumps(new,ensure_ascii=False),time.time(),owner,revision)).rowcount
        if n!=1:raise ApiError('Stav skladu se změnil. Načtěte jej a zápis zopakujte.',409)
        write_stock_changes(c,owner,old,new,revision+1)
        execute(c,'UPDATE work_sessions SET last_activity=%s WHERE token_hash=%s',(time.time(),digest(request.cookies.get(SESSION,''))))
        return new

    @app.get('/work')
    def work_page():return send_from_directory(WEB,'work.html')
    @app.get('/work.js')
    def work_js():return send_from_directory(WEB,'work.js')
    @app.get('/work.css')
    def work_css():return send_from_directory(WEB,'work.css')

    @app.route('/api/admin/users/<id>/work-access',methods=['GET','PUT'])
    @authenticated(admin=True)
    def configure(id):
        if request.method=='PUT':rate_limit(['pin-config:'+g.user['id']],30)
        with db() as c:
            target=one(c,'SELECT * FROM users WHERE id=%s',(id,))
            if not target:raise ApiError('Účet neexistuje.',404)
            owner=target.get('stock_owner_id') or target['id'];data,_=document(c,owner)
            current=one(c,'SELECT * FROM work_access WHERE user_id=%s',(id,))
            if request.method=='GET':return jsonify(hasPin=bool(current and current['owner_id']==owner and current['pin_hash']),stores=data['stores'],allowedStores=store_scope(c,target),ownerId=owner)
            values=body();scope=values.get('allowedStores');pin=values.get('pin')
            valid={s['id'] for s in data['stores']}
            if scope is not None and (not isinstance(scope,list) or any(not isinstance(s,str) for s in scope) or len(scope)!=len(set(scope)) or not set(scope)<=valid):raise ApiError('Neplatný výběr skladů.')
            if target['role']=='admin' and scope is not None:raise ApiError('Majitel má přístup ke všem skladům.')
            if pin is not None and (not isinstance(pin,str) or not re.fullmatch(r'[0-9]{4}',pin)):raise ApiError('PIN musí obsahovat přesně čtyři číslice.')
            execute(c,'UPDATE users SET last_seen=last_seen WHERE id=%s',(owner,))
            if pin:
                peers=allrows(c,'SELECT pin_hash FROM work_access WHERE owner_id=%s AND user_id<>%s AND pin_hash IS NOT NULL',(owner,id))
                if any(password_ok(pin,p['pin_hash']) for p in peers):raise ApiError('Tento PIN už v pracovním prostoru používá jiný zaměstnanec.')
            hashed=password_hash(pin) if pin else current['pin_hash'] if current and current['owner_id']==owner else None
            if values.get('removePin') is True:hashed=None
            execute(c,'INSERT INTO work_access (user_id,owner_id,pin_hash,stores_json) VALUES (%s,%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET owner_id=excluded.owner_id,pin_hash=excluded.pin_hash,stores_json=excluded.stores_json',(id,owner,hashed,json.dumps(scope)))
            execute(c,'DELETE FROM work_sessions WHERE user_id=%s',(id,))
            audit(c,g.user['id'],'work_access_changed','Změna PINu nebo přístupu ke skladům: '+target['username'])
        return jsonify(ok=True)

    @app.post('/api/work/device')
    @authenticated(admin=True)
    def pair():
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
        with db() as c:
            access=one(c,'SELECT pin_hash FROM work_access WHERE user_id=%s AND owner_id=%s',(g.user['id'],g.user['id']))
            if not access or not access['pin_hash']:raise ApiError('Nejdříve si nastavte vlastní pracovní PIN v profilu nebo nastavení.',403)
            execute(c,'DELETE FROM work_devices WHERE token_hash=%s',(digest(request.cookies.get(DEVICE,'')),))
            execute(c,'INSERT INTO work_devices (token_hash,owner_id,csrf,created_at) VALUES (%s,%s,%s,%s)',(digest(token),g.user['id'],csrf,time.time()))
            execute(c,'DELETE FROM sessions WHERE token_hash=%s',(g.user['token_hash'],))
            audit(c,g.user['id'],'work_device_paired','Aktivace pracovního terminálu')
        r=jsonify(ok=True);r.set_cookie(DEVICE,token,max_age=180*86400,secure=SECURE,httponly=True,samesite='Strict',path=request.script_root or '/');r.delete_cookie(cookie_name(),path=request.script_root or '/');r.delete_cookie(SESSION,path=request.script_root or '/');return r

    @app.get('/api/work/session')
    def status():
        with db() as c:
            d=device(c);u=employee(c,d)
            if not u:return jsonify(locked=True,csrf=d['csrf'])
            return jsonify(locked=False,csrf=u['csrf'],name=(u['first_name']+' '+u['last_name']).strip(),permissions=effective_permissions(u),idleSeconds=IDLE,expiresAt=u['last_activity']+IDLE,isOwner=u['role']=='admin')

    @app.post('/api/work/login')
    def pin_login():
        rate_limit(['work-pin-device:'+digest(request.cookies.get(DEVICE,''))],8)
        rate_limit(['work-pin-ip:'+client_ip()],200)
        with db() as c:
            d=device(c)
            if not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),d['csrf']):raise ApiError('Obnovte pracovní bránu.',403)
            pin=body().get('pin','')
            if not isinstance(pin,str) or not re.fullmatch(r'[0-9]{4}',pin):raise ApiError('Nesprávný PIN.',401)
            candidates=allrows(c,"SELECT u.*,w.pin_hash FROM work_access w JOIN users u ON u.id=w.user_id WHERE w.owner_id=%s AND w.pin_hash IS NOT NULL AND u.status='active'",(d['owner_id'],))
            u=next((u for u in candidates if (u.get('stock_owner_id') or u['id'])==d['owner_id'] and password_ok(pin,u['pin_hash'])),None)
            if not u:raise ApiError('Nesprávný PIN.',401)
            if not has_permission(u,'stock.view'):raise ApiError('Nemáte povolený přístup ke skladům. Obraťte se na majitele.',403)
            token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
            execute(c,'DELETE FROM work_sessions WHERE device_hash=%s',(d['token_hash'],))
            execute(c,'INSERT INTO work_sessions (token_hash,device_hash,user_id,csrf,last_activity) VALUES (%s,%s,%s,%s,%s)',(digest(token),d['token_hash'],u['id'],csrf,time.time()))
            execute(c,'DELETE FROM rate_buckets WHERE bucket=%s',(digest('work-pin-device:'+d['token_hash']),))
            audit(c,u['id'],'work_login','Přihlášení PINem na pracovním terminálu')
        r=jsonify(ok=True);r.set_cookie(SESSION,token,max_age=86400,secure=SECURE,httponly=True,samesite='Strict',path=request.script_root or '/');return r

    @app.post('/api/work/lock')
    def lock():
        with db() as c:
            d=device(c);u=employee(c,d)
            if not any(secrets.compare_digest(request.headers.get('X-CSRF-Token',''),v) for v in [d['csrf']]+([u['csrf']] if u else [])):raise ApiError('Obnovte pracovní bránu.',403)
            execute(c,'DELETE FROM work_sessions WHERE device_hash=%s',(d['token_hash'],))
        r=jsonify(ok=True);r.delete_cookie(SESSION,path=request.script_root or '/');return r

    @app.post('/api/work/touch')
    @worker()
    def touch():
        with db() as c:execute(c,'UPDATE work_sessions SET last_activity=%s WHERE token_hash=%s',(time.time(),digest(request.cookies.get(SESSION,''))))
        return jsonify(ok=True,expiresAt=time.time()+IDLE)

    @app.post('/api/work/leave')
    @worker()
    def leave():
        if g.user['role']!='admin':raise ApiError('Pracovní režim může ukončit pouze majitel.',403)
        with db() as c:
            audit(c,g.user['id'],'work_device_unpaired','Ukončení pracovního režimu majitelem')
            execute(c,'DELETE FROM work_devices WHERE token_hash=%s',(g.work_device['token_hash'],))
        r=jsonify(ok=True);r.delete_cookie(DEVICE,path=request.script_root or '/');r.delete_cookie(SESSION,path=request.script_root or '/');return r

    @app.get('/api/work/stock')
    @worker('stock.view')
    def stock():
        with db() as c:
            data,revision=document(c,g.work_device['owner_id']);visible=scoped_stock(data,store_scope(c,g.user))
            rows=[]
            for s in visible['stores']:
                if s.get('archivedAt'):continue
                for p in local_products(data,s['id']):
                    qty=current_quantity(data,p['id'],s['id']);rows.append({'id':p['id'],'store':s['id'],'name':p['name'],'unit':p['unit'],'qty':qty,'min':p['min']})
        return jsonify(revision=revision,stores=[s for s in visible['stores'] if not s.get('archivedAt')],products=rows)

    @app.post('/api/work/move')
    @worker('stock.view')
    def move():
        v=body();reason=v.get('reason');permission={'Příjem':'stock.receive','Výdej':'stock.move'}.get(reason)
        if not permission or not has_permission(g.user,permission):raise ApiError('K této akci nemáte oprávnění.',403)
        qty=v.get('qty');operation=v.get('operationId')
        if type(qty) not in (int,float) or not math.isfinite(qty) or not 0<qty<=1e12 or not isinstance(operation,str) or not re.fullmatch(r'[a-zA-Z0-9-]{10,100}',operation):raise ApiError('Zadejte kladné množství.')
        with db() as c:
            data,revision=document(c,g.work_device['owner_id']);check_store(c,data,v.get('store'))
            p=next((p for p in local_products(data,v['store']) if p['id']==v.get('product')),None)
            if not p:raise ApiError('Položka do tohoto skladu nepatří.',403)
            signed=qty if reason=='Příjem' else -qty
            duplicate=next((m for m in data['moves'] if m['id']==operation),None)
            if duplicate:
                if any(duplicate[k]!=val for k,val in [('store',v['store']),('product',p['id']),('qty',signed),('reason',reason)]):raise ApiError('ID zápisu již bylo použito.',409)
                return jsonify(ok=True,duplicate=True)
            if type(v.get('revision')) is not int or revision!=v['revision']:raise ApiError('Stav skladu se změnil. Načtěte jej a zápis zopakujte.',409)
            current=current_quantity(data,p['id'],v['store'])
            if reason=='Výdej' and (current is None or qty>current):raise ApiError('Ve skladu není dostatečné množství.')
            new=copy.deepcopy(data);new['moves'].append({'id':operation,'product':p['id'],'store':v['store'],'qty':signed,'reason':reason,'at':datetime.now(timezone.utc).isoformat()})
            save(c,data,new,revision);audit(c,g.user['id'],'work_move',reason+' · '+p['name'])
        return jsonify(ok=True)

    @app.post('/api/work/inventory')
    @worker('inventory.run')
    def inventory():
        if not has_permission(g.user,'work.inventory') or not has_permission(g.user,'inventory.warehouse'):raise ApiError('Nemáte zvláštní oprávnění k inventuře v pracovním režimu.',403)
        v=body();values=v.get('values');operation=v.get('operationId')
        if not isinstance(values,dict) or not values or not isinstance(operation,str) or not re.fullmatch(r'[a-zA-Z0-9-]{10,100}',operation):raise ApiError('Vyplňte položky inventury.')
        if any(type(q) not in (int,float) or not math.isfinite(q) or not 0<=q<=1e12 for q in values.values()):raise ApiError('Inventurní množství musí být nezáporné číslo.')
        with db() as c:
            data,revision=document(c,g.work_device['owner_id']);check_store(c,data,v.get('store'));ps=local_products(data,v['store'])
            if set(values)!={p['id'] for p in ps}:raise ApiError('Seznam položek se změnil. Načtěte inventuru znovu.',409)
            submission=one(c,'SELECT * FROM inventory_submissions WHERE id=%s AND owner_id=%s',(operation,g.work_device['owner_id']))
            if submission:
                content=json.loads(submission['content_json'])
                if submission['submitted_by']!=g.user['id'] or {r['product']:r['qty'] for r in content['counts']}!=values or any(r['store']!=v['store'] for r in content['counts']):raise ApiError('ID inventury již bylo použito.',409)
                return jsonify(ok=True,duplicate=True,pendingInventoryIds=[operation])
            previous=[r for r in data['counts'] if r.get('inventoryId')==operation]
            if previous:
                if {r['product']:r['qty'] for r in previous}!=values or any(r['store']!=v['store'] for r in previous):raise ApiError('ID inventury již bylo použito.',409)
                return jsonify(ok=True,duplicate=True)
            if data.get('draft') and data['draft']['store']==v['store']:raise ApiError('V tomto skladu už je rozpracovaná inventura. Dokončete ji v hlavní aplikaci.',409)
            if type(v.get('revision')) is not int or revision!=v['revision']:raise ApiError('Stav skladu se změnil. Načtěte inventuru znovu.',409)
            new=copy.deepcopy(data);at=datetime.now(timezone.utc).isoformat()
            for pid,qty in values.items():new['counts'].append({'id':uid(),'inventoryId':operation,'kind':'warehouse','product':pid,'store':v['store'],'qty':qty,'at':at})
            try:save(c,data,new,revision)
            except StockValidationError as e:raise ApiError(str(e))
            audit(c,g.user['id'],'work_inventory','Uložení inventury skladu '+v['store'])
        return jsonify(ok=True,pendingInventoryIds=getattr(g,'pending_inventory_ids',[]))

    @app.get('/api/work/changes')
    @worker('stock.audit')
    def changes():
        with db() as c:
            scope=store_scope(c,g.user);clauses=['l.owner_id=%s'];args=[g.work_device['owner_id']]
            if scope is not None:
                if not scope:return jsonify(changes=[])
                clauses.append('l.store_id IN ('+','.join(['%s']*len(scope))+')');args+=scope
            rows=allrows(c,'SELECT l.store_name,l.label,l.kind,l.field,l.before_json,l.after_json,l.created_at,l.actor_name,u.first_name,u.last_name FROM stock_change_log l LEFT JOIN users u ON u.id=l.actor_id WHERE '+' AND '.join(clauses)+' ORDER BY l.created_at DESC,l.id DESC LIMIT 100',tuple(args))
            for r in rows:
                r['name']=(' '.join(filter(None,[r.pop('first_name'),r.pop('last_name')])) or r.pop('actor_name'))
                r['before']=json.loads(r.pop('before_json'));r['after']=json.loads(r.pop('after_json'))
        return jsonify(changes=rows)
