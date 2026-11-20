"""Owner hub and independent venue databases. Never accept a client supplied SQL schema."""
from server.coowners import owner_scope
import json
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path
from flask import g, request, jsonify, send_from_directory

VENUES="""CREATE TABLE IF NOT EXISTS allin_venues (
 id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 name TEXT NOT NULL, address TEXT NOT NULL DEFAULT '', manager_first_name TEXT NOT NULL DEFAULT '', manager_last_name TEXT NOT NULL DEFAULT '', created_at DOUBLE PRECISION NOT NULL)"""

class VenueMount:
    def __init__(self, application):self.application=application
    def __call__(self, environ, start_response):
        path=environ.get('PATH_INFO','')
        match=re.match(r'^/v/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})(/|$)',path)
        if match:
            prefix='/v/'+match[1]
            environ['allin.venue_id']=match[1]
            environ['SCRIPT_NAME']=environ.get('SCRIPT_NAME','')+prefix
            environ['PATH_INFO']=path[len(prefix):] or '/'
        return self.application(environ,start_response)

@contextmanager
def venue_context(venue, provision=True):
    previous=getattr(g,'venue',None)
    g.venue=venue
    try:
        if provision and venue:
            from server.coowners import provision_owner
            provision_owner(venue)
        yield
    finally:g.venue=previous

def install_context(app):
    from server.app import db,execute,one,allrows,ApiError,TEST_DB,SUPABASE_DATABASE_URL
    with db(central=True) as c:
        execute(c,VENUES)
        columns={r['name'] for r in allrows(c,'PRAGMA table_info(allin_venues)')} if TEST_DB else {r['column_name'] for r in allrows(c,"SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='allin_venues'")}
        for field in ('manager_first_name','manager_last_name'):
            if field not in columns:execute(c,"ALTER TABLE allin_venues ADD COLUMN "+field+" TEXT NOT NULL DEFAULT ''")
        for field,sql in [('archived_at','DOUBLE PRECISION'),('card_style_json',"TEXT NOT NULL DEFAULT '{}'")]:
            if field not in columns:execute(c,'ALTER TABLE allin_venues ADD COLUMN '+field+' '+sql)
        execute(c,'CREATE INDEX IF NOT EXISTS allin_venues_owner ON allin_venues(owner_id,created_at)')
        if not TEST_DB:
            execute(c,'ALTER TABLE allin_venues ENABLE ROW LEVEL SECURITY')
            execute(c,'REVOKE ALL ON allin_venues FROM PUBLIC')
            if SUPABASE_DATABASE_URL:execute(c,'REVOKE ALL ON allin_venues FROM anon,authenticated')
    app.wsgi_app=VenueMount(app.wsgi_app)

    @app.before_request
    def resolve_venue():
        venue_id=request.environ.get('allin.venue_id')
        g.venue=None
        if venue_id:
            with db(central=True) as c:venue=one(c,'SELECT * FROM allin_venues WHERE id=%s',(venue_id,))
            if not venue:raise ApiError('Provoz neexistuje.',404)
            if venue.get('archived_at') is not None:
                if not request.path.startswith('/api/'):
                    from server.app import WEB
                    return send_from_directory(WEB,'archived.html'),410
                raise ApiError('Tento provoz je vypnutý a archivovaný. Obraťte se na majitele.',410)
            g.venue=venue
            if request.path.startswith('/api/owner/') or request.path=='/api/owner':raise ApiError('Centrální panel otevřete mimo provoz.',403)
        elif request.path.startswith('/api/') and not (TEST_DB and os.environ.get('ALLIN_LEGACY_TEST_API')=='1'):
            if request.path not in ('/api/login','/api/logout','/api/me','/api/password') and not request.path.startswith(('/api/owner/','/api/notifications')):
                raise ApiError('Nejdříve vyberte provoz v centrálním panelu.',403)

    @app.after_request
    def private_venue_response(response):
        if getattr(g,'venue',None):response.headers['Cache-Control']='no-store'
        return response


def register(app):
    from server.app import (authenticated,db,execute,one,allrows,ApiError,body,textfield,uid,
        init_db,seed_shop,public_user,session_response,WEB,TEST_DB,COOKIE,SECURE,audit)
    from server.permissions import PERMISSIONS
    from server.stock import current_quantity,at_minimum,low_stock

    def owned(venue_id):
        with db(central=True) as c:venue=one(c,'SELECT * FROM allin_venues WHERE id=%s AND owner_id=%s',(venue_id,owner_scope()))
        if not venue:raise ApiError('Provoz neexistuje nebo k němu nemáte přístup.',404)
        if venue.get('archived_at') is not None:raise ApiError('Provoz je archivovaný. Nejprve jej obnovte.',409)
        return venue

    def manager_values(values):
        first=textfield({'managerFirstName':values.get('managerFirstName','')},'managerFirstName',0,64)
        last=textfield({'managerLastName':values.get('managerLastName','')},'managerLastName',0,64)
        if bool(first)!=bool(last):raise ApiError('Vyplňte jméno i příjmení manažera, nebo ponechte obě pole prázdná.')
        return first,last

    def summary(venue):
        from server.controls import opening_status
        venue={**venue,'openingStatus':opening_status(json.loads(venue.get('opening_hours_json') or '{}'))}
        with venue_context(venue),db() as c:
            row=one(c,'SELECT data_json FROM stock_documents WHERE user_id=%s',(venue['owner_id'],))
            data=json.loads(row['data_json']) if row else {'stores':[],'products':[],'counts':[],'moves':[],'barInventories':[]}
            stores=[s for s in data['stores'] if not s.get('archivedAt')]
            quantities={};low=0;known=0;unmeasured=0
            for store in stores:
                from server.work import local_products
                for product in local_products(data,store['id']):
                    qty=current_quantity(data,product['id'],store['id'])
                    if qty is None:unmeasured+=1;continue
                    known+=1;unit=product['unit'];quantities[unit]=quantities.get(unit,0)+qty
                    if at_minimum(product,qty):low+=1
            inventory_ids={r.get('inventoryId') or r['store']+'|'+r['at'] for r in data['counts'] if not r.get('opening')}
            inventory_ids.update(r['id'] for r in data.get('barInventories',[]))
            runs={r['id']:{'at':r['at'],'items':r['items']} for r in data.get('barInventories',[])}
            for count in data['counts']:
                if count.get('opening'):continue
                key=count.get('inventoryId') or count['store']+'|'+count['at']
                if key in {r['id'] for r in data.get('barInventories',[])}:continue
                run=runs.setdefault(key,{'at':count['at'],'items':[]})
                run['items'].append(count)
            latest=max(runs.values(),key=lambda r:r['at'],default=None)
            shortage=None
            if latest:
                comparable=[i for i in latest['items'] if i.get('expected') is not None]
                if comparable:
                    short=[i for i in comparable if i['qty']<i['expected']]
                    shortage={}
                    for item in short:
                        unit=item['unit'];shortage[unit]=shortage.get(unit,0)+item['expected']-item['qty']
                    shortage={unit:round(qty,3) for unit,qty in shortage.items()}
            last=one(c,'SELECT created_at FROM events ORDER BY created_at DESC LIMIT 1')
            team=one(c,"SELECT COUNT(*) AS n FROM users WHERE role='user'")['n']
            return {**venue,'cardStyle':json.loads(venue.get('card_style_json') or '{}'),'quantities':{unit:round(qty,3) for unit,qty in quantities.items()},'warehouses':len(stores),'products':len(data['products']),
                'inventories':len(inventory_ids),'belowMinimum':low,'lowStock':low_stock(data),'measuredPositions':known,'unmeasuredPositions':unmeasured,
                'latestShortage':shortage,'latestInventoryAt':latest['at'] if latest else None,'employees':team,'lastActivity':last['created_at'] if last else None}

    @app.get('/api/owner/venues')
    @authenticated(admin=True)
    def venues():
        with db(central=True) as c:rows=allrows(c,'SELECT * FROM allin_venues WHERE owner_id=%s AND archived_at IS '+('NOT NULL' if request.args.get('archived')=='1' else 'NULL')+' ORDER BY created_at,id',(owner_scope(),))
        return jsonify(venues=[summary(v) for v in rows])

    @app.post('/api/owner/venues')
    @authenticated(admin=True)
    def create():
        values=body();name=textfield(values,'name',1,100);address=textfield({'address':values.get('address','')},'address',0,200)
        first,last=manager_values(values)
        venue={'manager_first_name':first,'manager_last_name':last,'id':uid(),'owner_id':owner_scope(),'name':name,'address':address,'created_at':time.time()}
        # Provision first; publish the venue only after the private database is ready.
        schema='venue_'+venue['id'].replace('-','')
        if not TEST_DB:
            with db(central=True) as c:
                execute(c,'CREATE SCHEMA '+schema)
                execute(c,'REVOKE ALL ON SCHEMA '+schema+' FROM PUBLIC')
        try:
            with venue_context(venue, provision=False):
                init_db(seed_admins=False)
                from server.coowners import provision_owner
                provision_owner(venue, force=True)
                with db() as c:
                    actor=g.user
                    initial={'stores':[{'id':'main','name':'Hlavní sklad'}],'products':[],'counts':[],'moves':[],'draft':None,'barInventories':[],'barDraft':None}
                    execute(c,'INSERT INTO stock_documents (user_id,revision,data_json,updated_at) VALUES (%s,0,%s,%s)',(venue['owner_id'],json.dumps(initial),time.time()))
                    audit(c,actor['id'],'venue_created','Vytvoření provozu '+name)
                seed_shop()
            with db(central=True) as c:
                execute(c,'INSERT INTO allin_venues (id,owner_id,name,address,created_at,manager_first_name,manager_last_name) VALUES (%s,%s,%s,%s,%s,%s,%s)',tuple(venue[k] for k in ('id','owner_id','name','address','created_at','manager_first_name','manager_last_name')))
                audit(c,g.user['id'],'venue_created','Vytvoření provozu '+name)
        except Exception:
            if TEST_DB:
                Path(TEST_DB).with_name('venue_'+venue['id']+'.sqlite3').unlink(missing_ok=True)
            else:
                with db(central=True) as c:execute(c,'DROP SCHEMA '+schema+' CASCADE')
            raise
        return jsonify(venue=summary(venue)),201

    @app.put('/api/owner/venues/<venue_id>/manager')
    @authenticated(admin=True)
    def update_manager(venue_id):
        venue=owned(venue_id);first,last=manager_values(body())
        with db(central=True) as c:
            execute(c,'UPDATE allin_venues SET manager_first_name=%s,manager_last_name=%s WHERE id=%s AND owner_id=%s',(first,last,venue_id,owner_scope()))
            audit(c,g.user['id'],'venue_manager_changed','Změna odpovědného manažera provozu '+venue['name'])
        return jsonify(ok=True)

    @app.post('/api/owner/venues/<venue_id>/enter')
    @authenticated(admin=True)
    def enter(venue_id):
        venue=owned(venue_id)
        with venue_context(venue),db() as c:
            user=one(c,'SELECT * FROM users WHERE id=%s',(g.user['id'],))
            response=session_response(c,user)
        # Keep the central session and every other venue session untouched.
        cookies=response.headers.getlist('Set-Cookie')
        response.headers.remove('Set-Cookie')
        for value in cookies:response.headers.add('Set-Cookie',value.replace('Path=/',f'Path=/v/{venue_id}'))
        response.set_data(app.json.dumps({'url':f'/v/{venue_id}/','name':venue['name']}))
        return response

    @app.get('/api/owner/activity')
    @authenticated(admin=True)
    def owner_activity():
        with db(central=True) as c:rows=allrows(c,'SELECT * FROM allin_venues WHERE owner_id=%s AND archived_at IS NULL',(owner_scope(),))
        selected=request.args.get('venue','')
        if selected:rows=[owned(selected)]
        events=[]
        for venue in rows:
            with venue_context(venue),db() as c:
                for event in allrows(c,'SELECT e.*,u.first_name,u.last_name,u.username FROM events e LEFT JOIN users u ON u.id=e.user_id ORDER BY e.created_at DESC LIMIT 100'):
                    events.append({**event,'venueId':venue['id'],'venueName':venue['name']})
        return jsonify(events=sorted(events,key=lambda e:(e['created_at'],e['id']),reverse=True)[:200],retentionDays=90)

    @app.get('/api/owner/team')
    @authenticated(admin=True)
    def team():
        with db(central=True) as c:rows=allrows(c,'SELECT * FROM allin_venues WHERE owner_id=%s AND archived_at IS NULL ORDER BY created_at',(owner_scope(),))
        members=[]
        for venue in rows:
            with venue_context(venue),db() as c:
                for user in allrows(c,"SELECT u.*,p.name AS position_name FROM users u LEFT JOIN staff_positions p ON p.id=u.position_id WHERE u.role='user' ORDER BY u.created_at"):
                    members.append({**public_user(user),'venueId':venue['id'],'venueName':venue['name']})
        return jsonify(members=members,permissions={k:v[0] for k,v in PERMISSIONS.items()})

    @app.post('/api/owner/venues/<venue_id>/invites')
    @authenticated(admin=True)
    def invite(venue_id):
        venue=owned(venue_id)
        with venue_context(venue):
            from server.app import invite_create
            response=invite_create.__wrapped__()
            data=response.get_json();data['venueUrl']=f'/v/{venue_id}/'
            return jsonify(data)

    @app.post('/api/owner/venues/<venue_id>/members')
    @authenticated(admin=True)
    def create_member(venue_id):
        from server.app import rate_limit
        from server.employees import create_employee
        venue=owned(venue_id);values=body()
        rate_limit(['employee-create:'+g.user['id']],30)
        with venue_context(venue),db() as c:
            user=create_employee(c,values,venue['owner_id'],g.user['id'])
        return jsonify(user=user,hasPin=True,venueUrl=f'/v/{venue_id}/'),201

    @app.post('/api/owner/venues/<venue_id>/members/<member_id>')
    @authenticated(admin=True)
    def update_member(venue_id,member_id):
        venue=owned(venue_id);values=body();permissions=values.get('permissions');status=values.get('status')
        if permissions is not None and (not isinstance(permissions,dict) or set(permissions)-set(PERMISSIONS) or any(type(v) is not bool for v in permissions.values())):raise ApiError('Neplatná oprávnění.')
        if status is not None and status not in ('active','suspended'):raise ApiError('Neplatný stav.')
        with venue_context(venue),db() as c:
            user=one(c,"SELECT * FROM users WHERE id=%s AND role='user'",(member_id,))
            if not user:raise ApiError('Zaměstnanec neexistuje.',404)
            from server.staff import set_access,UNCHANGED
            if permissions is not None or 'positionId' in values:set_access(c,user,permissions,values.get('positionId',UNCHANGED))
            if status is not None:execute(c,'UPDATE users SET status=%s WHERE id=%s',(status,member_id))
            execute(c,'DELETE FROM sessions WHERE user_id=%s',(member_id,))
            execute(c,'DELETE FROM work_sessions WHERE user_id=%s',(member_id,))
            audit(c,g.user['id'],'permissions_changed','Změna přístupu zaměstnance '+user['username'])
        return jsonify(ok=True)

    @app.get('/api/venue')
    @authenticated()
    def venue_identity():return jsonify(venue={k:g.venue[k] for k in ('id','name','address')})

    @app.get('/owner.js')
    def owner_js():return send_from_directory(WEB,'owner.js')
    @app.get('/owner.css')
    def owner_css():return send_from_directory(WEB,'owner.css')
    @app.get('/venue-context.js')
    def venue_js():return send_from_directory(WEB,'venue-context.js')

