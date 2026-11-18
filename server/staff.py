"""Venue job presets and an indexed, private employee login directory."""
from server.coowners import owner_scope
import json
import re
from flask import g, request, jsonify, has_request_context
from server.allin import venue_context

POSITION_SQL="""CREATE TABLE IF NOT EXISTS staff_positions (id TEXT PRIMARY KEY,name TEXT NOT NULL,permissions_json TEXT NOT NULL)"""
DIRECTORY_SQL="""CREATE TABLE IF NOT EXISTS staff_login_directory (venue_id TEXT NOT NULL REFERENCES allin_venues(id) ON DELETE CASCADE,user_id TEXT NOT NULL,username_key TEXT NOT NULL,PRIMARY KEY(venue_id,user_id))"""


def staff_defaults():
    from server.permissions import PERMISSIONS
    return {k:default for k,(_,default) in PERMISSIONS.items() if k!='inventory.adjust'}


def validate_permissions(values):
    from server.app import ApiError
    from server.permissions import PERMISSIONS
    if not isinstance(values,dict) or set(values)-set(PERMISSIONS) or any(type(v) is not bool for v in values.values()):
        raise ApiError('Neplatná oprávnění.')
    # Historical edits are an owner capability, regardless of a supplied preset.
    return {**staff_defaults(),**values,'inventory.adjust':False}


def seed_positions(c):
    from server.app import execute
    for key,name in [('zamestnanec','Zaměstnanec'),('kuchar','Kuchař'),('cisnik','Číšník'),('manager','Manager')]:
        execute(c,'INSERT INTO staff_positions (id,name,permissions_json) VALUES (%s,%s,%s) ON CONFLICT (id) DO NOTHING',(key,name,json.dumps(staff_defaults())))


def assigned_position(c,position_id):
    from server.app import one,ApiError
    seed_positions(c)
    if not isinstance(position_id,str):raise ApiError('Neplatná pozice.')
    row=one(c,'SELECT * FROM staff_positions WHERE id=%s',(position_id,))
    if not row:raise ApiError('Pozice neexistuje.',404)
    return row


UNCHANGED=object()

def set_access(c,user,permissions=None,position_id=UNCHANGED):
    from server.app import execute
    selected=user.get('position_id') if position_id is UNCHANGED else position_id or 'zamestnanec'
    position=assigned_position(c,selected) if selected else None
    preset=validate_permissions(json.loads(position['permissions_json'])) if position else validate_permissions({})
    effective=validate_permissions(permissions) if permissions is not None else preset
    overrides={k:v for k,v in effective.items() if v!=preset.get(k)}
    execute(c,'UPDATE users SET position_id=%s,permissions_json=%s,permission_overrides_json=%s WHERE id=%s',
            (selected,json.dumps(effective),json.dumps(overrides),user['id']))
    return effective


def directory_table(c):
    from server.app import TEST_DB,DATABASE_SCHEMA,execute
    venue=getattr(g,'venue',None) if has_request_context() else None
    if TEST_DB:
        if not venue:return 'staff_login_directory'
        if not any(r[1]=='login_hub' for r in c.execute('PRAGMA database_list')):
            execute(c,'ATTACH DATABASE %s AS login_hub',(TEST_DB,))
        return 'login_hub.staff_login_directory'
    return DATABASE_SCHEMA+'.staff_login_directory'


def index_employee(c,user):
    from server.app import execute
    venue=getattr(g,'venue',None) if has_request_context() else None
    if not venue:return
    table=directory_table(c)
    execute(c,'INSERT INTO '+table+' (venue_id,user_id,username_key) VALUES (%s,%s,%s) ON CONFLICT (venue_id,user_id) DO UPDATE SET username_key=excluded.username_key',
            (venue['id'],user['id'],user['username_key']))


def employee_login(values,username,password):
    """Return a venue session only after checking credentials in that venue."""
    from server.app import db,one,allrows,password_ok,ApiError,session_response,app
    where='v.archived_at IS NULL AND d.username_key=%s';args=(username.casefold(),)
    if values.get('venueId'):
        if not isinstance(values['venueId'],str):raise ApiError('Neplatný provoz.')
        where+=' AND v.id=%s';args+=(values['venueId'],)
    with db(central=True) as c:
        candidates=allrows(c,'SELECT v.*,d.user_id FROM staff_login_directory d JOIN allin_venues v ON v.id=d.venue_id WHERE '+where+' ORDER BY v.id LIMIT 51',args)
    if len(candidates)>50:
        raise ApiError('Toto přihlašovací jméno používá více provozů. Otevřete adresu svého provozu.',409)
    matches=[]
    for venue in candidates:
        with venue_context(venue),db() as c:
            user=one(c,"SELECT * FROM users WHERE id=%s AND username_key=%s AND role='user'",(venue['user_id'],username.casefold()))
            if user and password_ok(password,user['password_hash']) and user['status']=='active':matches.append(venue)
    if not matches:return None
    if len(matches)>1:
        return jsonify(error='Vyberte svůj provoz.',venues=[{'id':v['id'],'name':v['name']} for v in matches]),409
    venue=matches[0]
    with venue_context(venue),db() as c:
        user=one(c,"SELECT * FROM users WHERE id=%s AND username_key=%s AND status='active' AND role='user'",(venue['user_id'],username.casefold()))
        if not user or not password_ok(password,user['password_hash']):return None
        response=session_response(c,user)
        cookies=response.headers.getlist('Set-Cookie');response.headers.remove('Set-Cookie')
        for cookie in cookies:response.headers.add('Set-Cookie',cookie.replace('Path=/',f'Path=/v/{venue["id"]}'))
        response.set_data(app.json.dumps({'ok':True,'url':f'/v/{venue["id"]}/'}))
    return response


def register(app):
    from server.app import db,execute,allrows,one,TEST_DB,SUPABASE_DATABASE_URL,authenticated,body,textfield,ApiError,uid,audit
    from server.permissions import PERMISSIONS
    with db(central=True) as c:
        execute(c,DIRECTORY_SQL);execute(c,'CREATE INDEX IF NOT EXISTS staff_login_username ON staff_login_directory(username_key)')
        if not TEST_DB:
            execute(c,'ALTER TABLE staff_login_directory ENABLE ROW LEVEL SECURITY');execute(c,'REVOKE ALL ON staff_login_directory FROM PUBLIC')
            if SUPABASE_DATABASE_URL:execute(c,'REVOKE ALL ON staff_login_directory FROM anon,authenticated')
        venues=allrows(c,'SELECT * FROM allin_venues')
    # Upgrade existing venues and backfill existing employee accounts without
    # changing their passwords, PINs, permissions, or sessions.
    for venue in venues:
        with app.test_request_context(),venue_context(venue),db() as c:
            execute(c,POSITION_SQL)
            columns={r['name'] for r in allrows(c,'PRAGMA table_info(users)')} if TEST_DB else {r['column_name'] for r in allrows(c,"SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='users'")}
            if 'position_id' not in columns:execute(c,'ALTER TABLE users ADD COLUMN position_id TEXT')
            if 'permission_overrides_json' not in columns:execute(c,"ALTER TABLE users ADD COLUMN permission_overrides_json TEXT NOT NULL DEFAULT '{}'")
            from server.app import upgrade_contact_columns
            upgrade_contact_columns(c)
            seed_positions(c)
            if not TEST_DB:
                execute(c,'ALTER TABLE staff_positions ENABLE ROW LEVEL SECURITY');execute(c,'REVOKE ALL ON staff_positions FROM PUBLIC')
                if SUPABASE_DATABASE_URL:execute(c,'REVOKE ALL ON staff_positions FROM anon,authenticated')
            for user in allrows(c,"SELECT id,username_key FROM users WHERE role='user'"):index_employee(c,user)

    def positions(venue_id=None,position_id=None):
        if venue_id:
            with db(central=True) as c:venue=one(c,'SELECT * FROM allin_venues WHERE id=%s AND owner_id=%s',(venue_id,owner_scope()))
            if not venue:raise ApiError('Provoz neexistuje nebo k němu nemáte přístup.',404)
        else:venue=getattr(g,'venue',None)
        if venue and venue.get('archived_at') is not None:raise ApiError('Provoz je archivovaný.',409)
        with venue_context(venue),db() as c:
            execute(c,'UPDATE users SET last_seen=last_seen WHERE id=%s',(g.user['id'],))
            seed_positions(c)
            if request.method in ('POST','PUT'):
                values=body();name=textfield(values,'name',1,80);permissions=validate_permissions(values.get('permissions',{}));position_id=position_id or uid()
                if request.method=='PUT' and not one(c,'SELECT id FROM staff_positions WHERE id=%s',(position_id,)):raise ApiError('Pozice neexistuje.',404)
                execute(c,'INSERT INTO staff_positions (id,name,permissions_json) VALUES (%s,%s,%s) ON CONFLICT (id) DO UPDATE SET name=excluded.name,permissions_json=excluded.permissions_json',(position_id,name,json.dumps(permissions)))
                for user in allrows(c,"SELECT * FROM users WHERE position_id=%s AND role='user'",(position_id,)):
                    effective=validate_permissions({**permissions,**json.loads(user.get('permission_overrides_json') or '{}')})
                    if effective!=json.loads(user['permissions_json']):
                        execute(c,'UPDATE users SET permissions_json=%s WHERE id=%s',(json.dumps(effective),user['id']))
                        execute(c,'DELETE FROM sessions WHERE user_id=%s',(user['id'],));execute(c,'DELETE FROM work_sessions WHERE user_id=%s',(user['id'],))
                audit(c,g.user['id'],'position_changed','Nastavení pozice: '+name)
            rows=allrows(c,'SELECT * FROM staff_positions ORDER BY name,id')
        return jsonify(positions=[{'id':r['id'],'name':r['name'],'permissions':validate_permissions(json.loads(r['permissions_json']))} for r in rows],permissions={k:v[0] for k,v in PERMISSIONS.items() if k!='inventory.adjust'},defaults=staff_defaults())

    for route in ['/api/admin/positions','/api/owner/venues/<venue_id>/positions']:
        app.add_url_rule(route,endpoint='positions_'+str(len(app.view_functions)),view_func=authenticated(admin=True)(positions),methods=['GET','POST'])
        app.add_url_rule(route+'/<position_id>',endpoint='position_'+str(len(app.view_functions)),view_func=authenticated(admin=True)(positions),methods=['PUT'])

