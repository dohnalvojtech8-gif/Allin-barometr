"""BAROMETR accounts API. PostgreSQL in production; explicit SQLite only for tests."""
import os, json, time, secrets, hashlib, hmac, re, uuid, sqlite3, unicodedata, logging
from pathlib import Path
from contextlib import contextmanager
from functools import wraps
from flask import Flask, request, jsonify, g, send_from_directory, make_response, has_request_context

ROOT=Path(__file__).resolve().parent.parent
WEB=Path(__file__).resolve().parent/'web'
SOURCE_DATABASE_URL=os.environ.get('DATABASE_URL')
SUPABASE_DATABASE_URL=os.environ.get('SUPABASE_DATABASE_URL') or os.environ.get('SUPABASE_DB_URL')
logging.warning('BAROMETR database configuration keys: %s', ','.join(sorted(k for k in os.environ if re.fullmatch(r'[A-Z_][A-Z0-9_]*',k) and ('SUPABASE' in k or 'DATABASE' in k or k.startswith('BAROMETR_DB')))))
DATABASE_URL=SUPABASE_DATABASE_URL or SOURCE_DATABASE_URL
TEST_DB=os.environ.get('BAROMETR_TEST_DB')
DATABASE_SCHEMA=os.environ.get('BAROMETR_DB_SCHEMA','allin_barometr')
if DATABASE_SCHEMA and not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}',DATABASE_SCHEMA):
    raise RuntimeError('BAROMETR_DB_SCHEMA must be a lowercase PostgreSQL schema name')
if not DATABASE_URL and not TEST_DB: raise RuntimeError('DATABASE_URL is required')
FREE_UNLOCKS=os.environ.get('BAROMETR_FREE_UNLOCKS','1')=='1'
SESSION_DAYS=7
COOKIE='barometr_session'
SECURE=os.environ.get('BAROMETR_TEST_HTTP')!='1'
app=Flask(__name__,static_folder=None)
app.config.update(MAX_CONTENT_LENGTH=4*1024*1024,JSON_SORT_KEYS=False)

def connect(central=False):
    venue=getattr(g,'venue',None) if has_request_context() and not central else None
    schema=('venue_'+venue['id'].replace('-','')) if venue else DATABASE_SCHEMA
    test_path=str(Path(TEST_DB).parent/('venue_'+venue['id']+'.sqlite3')) if TEST_DB and venue else TEST_DB
    if TEST_DB:
        c=sqlite3.connect(test_path,timeout=15);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
    import psycopg
    from psycopg.rows import dict_row
    c=psycopg.connect(DATABASE_URL,row_factory=dict_row,connect_timeout=10,prepare_threshold=None)
    c.execute('SET search_path TO '+schema)
    return c
def execute(c,sql,args=()): return c.execute(sql.replace('%s','?') if TEST_DB else sql,args)
@contextmanager
def db(central=False):
    c=connect(central=central)
    try:
        if TEST_DB:c.execute('BEGIN IMMEDIATE')
        yield c;c.commit()
    except: c.rollback();raise
    finally:c.close()
def one(c,sql,args=()):
    r=execute(c,sql,args).fetchone();return dict(r) if r else None
def allrows(c,sql,args=()):return [dict(r) for r in execute(c,sql,args).fetchall()]
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def uid():return str(uuid.uuid4())
def password_hash(value):
    salt=secrets.token_hex(16);key=hashlib.scrypt(value.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex();return 'scrypt$'+salt+'$'+key
def password_ok(value,hashed):
    try:
        _,salt,key=hashed.split('$');got=hashlib.scrypt(value.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex();return hmac.compare_digest(got,key)
    except (ValueError,TypeError):return False
DUMMY=password_hash(secrets.token_urlsafe(24))
SCHEMA=[
'''CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT NOT NULL, username_key TEXT UNIQUE NOT NULL, first_name TEXT NOT NULL, last_name TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','user')), status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','suspended')), created_at DOUBLE PRECISION NOT NULL, last_login DOUBLE PRECISION, last_seen DOUBLE PRECISION, login_count INTEGER NOT NULL DEFAULT 0, state_json TEXT NOT NULL DEFAULT '{}', permissions_json TEXT NOT NULL DEFAULT '{}',stock_owner_id TEXT REFERENCES users(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED)''',
'''CREATE TABLE IF NOT EXISTS stock_documents (user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,revision INTEGER NOT NULL DEFAULT 0,data_json TEXT NOT NULL,updated_at DOUBLE PRECISION NOT NULL)''',
'''CREATE TABLE IF NOT EXISTS stock_change_log (id TEXT PRIMARY KEY,owner_id TEXT REFERENCES users(id) ON DELETE SET NULL,actor_id TEXT REFERENCES users(id) ON DELETE SET NULL,actor_name TEXT NOT NULL,store_id TEXT NOT NULL,store_name TEXT NOT NULL,entity_id TEXT NOT NULL,kind TEXT NOT NULL,label TEXT NOT NULL,field TEXT NOT NULL,before_json TEXT NOT NULL,after_json TEXT NOT NULL,revision INTEGER NOT NULL,created_at DOUBLE PRECISION NOT NULL)''',
'CREATE INDEX IF NOT EXISTS stock_changes_time ON stock_change_log(created_at)',
'''CREATE TABLE IF NOT EXISTS shop_bundles (id TEXT PRIMARY KEY,kind TEXT NOT NULL,template_json TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL)''',
'''CREATE TABLE IF NOT EXISTS bottle_calibrations (user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,product_id TEXT NOT NULL,capacity INTEGER NOT NULL,points_json TEXT NOT NULL,updated_at DOUBLE PRECISION NOT NULL,PRIMARY KEY(user_id,product_id,capacity))''',
'''CREATE TABLE IF NOT EXISTS scan_photos (id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,jpeg TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL)''',
'''CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,csrf TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL,expires_at DOUBLE PRECISION NOT NULL)''',
'''CREATE TABLE IF NOT EXISTS invitations (id TEXT PRIMARY KEY,code_hash TEXT UNIQUE NOT NULL,label TEXT NOT NULL,created_by TEXT REFERENCES users(id) ON DELETE SET NULL,created_at DOUBLE PRECISION NOT NULL,expires_at DOUBLE PRECISION NOT NULL,max_uses INTEGER NOT NULL,used_count INTEGER NOT NULL DEFAULT 0,revoked INTEGER NOT NULL DEFAULT 0)''',
'''CREATE TABLE IF NOT EXISTS invitation_uses (id TEXT PRIMARY KEY,invite_id TEXT REFERENCES invitations(id) ON DELETE CASCADE,user_id TEXT REFERENCES users(id) ON DELETE CASCADE,used_at DOUBLE PRECISION NOT NULL)''',
'''CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id) ON DELETE CASCADE,action TEXT NOT NULL,detail TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL)''',
'''CREATE TABLE IF NOT EXISTS unlocks (user_id TEXT REFERENCES users(id) ON DELETE CASCADE,product_id TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL,PRIMARY KEY(user_id,product_id))''',
'''CREATE TABLE IF NOT EXISTS rate_buckets (bucket TEXT PRIMARY KEY,started_at DOUBLE PRECISION NOT NULL,attempts INTEGER NOT NULL)''',
'CREATE INDEX IF NOT EXISTS events_user_time ON events(user_id,created_at)',
'CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id)',
'CREATE INDEX IF NOT EXISTS users_last_seen ON users(last_seen)']
def audit(c,user_id,action,detail=''):
    execute(c,'INSERT INTO events (id,user_id,action,detail,created_at) VALUES (%s,%s,%s,%s,%s)',(uid(),user_id,action,detail[:240],time.time()))
from server.work import TABLES as WORK_TABLES,store_scope,scoped_stock,merge_scoped_stock
SCHEMA.extend(WORK_TABLES)
from server.staff import POSITION_SQL
SCHEMA.append(POSITION_SQL)
from server.reviews import TABLES as REVIEW_TABLES
SCHEMA.extend(REVIEW_TABLES)
from server.notifications import OUTBOX_SQL
SCHEMA.append(OUTBOX_SQL)

def upgrade_contact_columns(connection):
    """Add optional contact fields to central and existing venue databases."""
    columns = ({r['name'] for r in allrows(connection, 'PRAGMA table_info(users)')} if TEST_DB else
               {r['column_name'] for r in allrows(connection, "SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='users'")})
    for field in ('phone', 'email'):
        if field not in columns:
            execute(connection, "ALTER TABLE users ADD COLUMN " + field + " TEXT NOT NULL DEFAULT ''")


def init_db(seed_admins=True):
    with db() as c:
        for sql in SCHEMA:execute(c,sql)
        columns={r['name'] for r in allrows(c,'PRAGMA table_info(users)')} if TEST_DB else {r['column_name'] for r in allrows(c,"SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='users'")}
        upgrade_contact_columns(c)
        if 'position_id' not in columns:execute(c,'ALTER TABLE users ADD COLUMN position_id TEXT')
        if 'permission_overrides_json' not in columns:execute(c,"ALTER TABLE users ADD COLUMN permission_overrides_json TEXT NOT NULL DEFAULT '{}'")
        if 'permissions_json' not in columns:execute(c,"ALTER TABLE users ADD COLUMN permissions_json TEXT NOT NULL DEFAULT '{}'")
        if 'stock_owner_id' not in columns:execute(c,'ALTER TABLE users ADD COLUMN stock_owner_id TEXT REFERENCES users(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED')
        execute(c,'CREATE INDEX IF NOT EXISTS users_stock_owner ON users(stock_owner_id)')
        if not TEST_DB:
            for table in allrows(c,"SELECT tablename FROM pg_tables WHERE schemaname=current_schema()"):
                name=table['tablename']
                execute(c,'ALTER TABLE '+name+' ENABLE ROW LEVEL SECURITY')
                execute(c,'REVOKE ALL ON '+name+' FROM PUBLIC')
                if SUPABASE_DATABASE_URL:execute(c,'REVOKE ALL ON '+name+' FROM anon,authenticated')
        for number in ((1,2) if seed_admins else ()):
            name=os.environ.get(f'ADMIN{number}_USERNAME');password=os.environ.get(f'ADMIN{number}_PASSWORD')
            if name and password:
                execute(c,"INSERT INTO users (id,username,username_key,first_name,last_name,password_hash,role,created_at) VALUES (%s,%s,%s,%s,%s,%s,'admin',%s) ON CONFLICT (username_key) DO NOTHING",(uid(),name,name.casefold(),name,'',password_hash(password),time.time()))
        execute(c,'DELETE FROM sessions WHERE expires_at < %s',(time.time(),))
        execute(c,'DELETE FROM rate_buckets WHERE started_at < %s',(time.time()-86400,))
if not TEST_DB:
    with db(central=True) as c:
        execute(c,'CREATE SCHEMA IF NOT EXISTS '+DATABASE_SCHEMA)
        execute(c,'REVOKE ALL ON SCHEMA '+DATABASE_SCHEMA+' FROM PUBLIC')
init_db()
raw=(ROOT/'aplikace/catalog-data.js').read_text()
CATALOG=json.loads(raw.split(' = ',1)[1].rstrip(';\n'))
PRODUCTS={p['id']:p for p in CATALOG['products']}

from server.shop import build_templates,choose_day as choose_week,quote

def seed_shop():
    templates=build_templates(CATALOG['products'])
    with db() as c:
        # Batch inserts avoid one database round trip for each template.
        for offset in range(0,len(templates),200):
            batch=templates[offset:offset+200];args=[]
            for t in batch:args.extend((t['id'],t['kind'],json.dumps(t,ensure_ascii=False),time.time()))
            execute(c,'INSERT INTO shop_bundles (id,kind,template_json,created_at) VALUES '+','.join(['(%s,%s,%s,%s)']*len(batch))+' ON CONFLICT (id) DO UPDATE SET kind=excluded.kind,template_json=excluded.template_json',tuple(args))
        return [json.loads(r['template_json']) for r in allrows(c,'SELECT template_json FROM shop_bundles ORDER BY id')]
SHOP_TEMPLATES=seed_shop()

class ApiError(Exception):
    def __init__(self,message,status=400):self.message=message;self.status=status
@app.errorhandler(ApiError)
def api_error(e):return jsonify(error=e.message),e.status
@app.errorhandler(413)
def too_large(e):return jsonify(error='Požadavek je příliš velký.'),413
@app.errorhandler(Exception)
def unexpected(e):
    from werkzeug.exceptions import HTTPException
    if isinstance(e,HTTPException):return jsonify(error='Požadavek nelze zpracovat.'),e.code
    app.logger.error('Unhandled request failure: %s',type(e).__name__)
    return jsonify(error='Dočasná chyba serveru. Zkuste to znovu.'),500
from server.allin import install_context
install_context(app)
_last_cleanup={}
@app.before_request
def cleanup_expired():
    now=time.time();key=getattr(g,'venue',None)
    key=key['id'] if key else 'owner'
    if now-_last_cleanup.get(key,0)>3600:
        with db() as c:
            execute(c,'DELETE FROM events WHERE created_at < %s',(now-90*86400,))
            execute(c,'DELETE FROM sessions WHERE expires_at < %s',(now,))
            execute(c,'DELETE FROM work_sessions WHERE last_activity < %s',(now-300,))
            execute(c,'DELETE FROM rate_buckets WHERE started_at < %s',(now-86400,))
        _last_cleanup[key]=now

@app.before_request
def protect_origin():
    if request.path.startswith('/api/') and request.method in ('POST','PUT','PATCH','DELETE'):
        if request.headers.get('Origin') and request.headers['Origin'].rstrip('/')!=request.host_url.rstrip('/'):
            # Render TLS terminates at the proxy, so compare host and require HTTPS in production.
            from urllib.parse import urlparse
            origin=urlparse(request.headers['Origin'])
            if origin.netloc!=request.host or (SECURE and origin.scheme!='https'):raise ApiError('Nepovolený původ požadavku.',403)
        if request.mimetype!='application/json':raise ApiError('Očekáván JSON požadavek.',415)
@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options']='nosniff';response.headers['X-Frame-Options']='DENY';response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self' blob:; style-src 'self' 'unsafe-inline'; img-src 'self' https: data:; connect-src 'self'; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.path.startswith('/api/') or request.path=='/':response.headers['Cache-Control']='no-store'
    return response

def body():
    value=request.get_json(silent=True)
    if not isinstance(value,dict):raise ApiError('Neplatný požadavek.')
    return value
def textfield(data,key,minimum=1,maximum=64):
    v=data.get(key)
    if not isinstance(v,str):raise ApiError('Vyplňte všechna povinná pole.')
    v=unicodedata.normalize('NFKC',v).strip()
    if len(v)<minimum or len(v)>maximum or any(ord(x)<32 for x in v):raise ApiError('Zkontrolujte délku a obsah polí.')
    return v
from server.permissions import has_permission, effective_permissions, PERMISSIONS

from server.coowners import owner_scope, valid_owner

def workspace_id():
    return owner_scope() if getattr(g,'venue',None) and g.user['role']=='admin' else g.user['id']

def cookie_name():
    venue=getattr(g,'venue',None)
    return COOKIE+'_'+venue['id'] if venue else COOKIE

def authenticated(admin=False,bottles=False,permission=None):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args,**kwargs):
            token=request.cookies.get(cookie_name(),'')
            with db() as c:
                row=one(c,"SELECT u.*,p.name AS position_name,s.csrf,s.token_hash FROM sessions s JOIN users u ON u.id=s.user_id LEFT JOIN staff_positions p ON p.id=u.position_id WHERE s.token_hash=%s AND s.expires_at>%s AND u.status='active'",(digest(token),time.time()))
                if not row:raise ApiError('Přihlaste se prosím.',401)
                if getattr(g,'venue',None) and row['role']=='admin':
                    # Owner entry is tied to a live central session on this browser.
                    with db(central=True) as owner_db:
                        owner_session=one(owner_db,"SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=%s AND s.expires_at>%s AND u.status='active' AND u.role='admin'",(digest(request.cookies.get(COOKIE,'')),time.time()))
                    if not owner_session or owner_session['id']!=row['id'] or not valid_owner(owner_session,g.venue):raise ApiError('Přihlaste se do centrálního panelu majitele.',401)
                if row['role']=='admin' and not getattr(g,'venue',None) and not valid_owner(row):raise ApiError('Přístup majitele byl pozastaven.',401)
                if row['role']=='admin' and row.get('stock_owner_id') and getattr(g,'venue',None):
                    shared=one(c,'SELECT state_json FROM users WHERE id=%s',(row['stock_owner_id'],))
                    row['state_json']=shared['state_json']
                if permission and not has_permission(row,permission):raise ApiError('K této akci nemáte oprávnění.',403)
                if admin and row['role']!='admin':raise ApiError('Tato akce je dostupná pouze administrátorům.',403)
                if bottles and permission!='catalog.unlock' and not (has_permission(row,'inventory.run') and has_permission(row,'inventory.bar')):raise ApiError('Nemáte oprávnění provádět inventury baru.',403)
                if bottles and not (FREE_UNLOCKS or row['role']=='admin'):raise ApiError('Odemykání a práce s lahvemi je pro běžné účty zatím vypnutá.',403)
                if request.method in ('POST','PUT','PATCH','DELETE') and not hmac.compare_digest(request.headers.get('X-CSRF-Token',''),row['csrf']):raise ApiError('Obnovte stránku a zkuste to znovu.',403)
                if not row['last_seen'] or time.time()-row['last_seen']>45:execute(c,'UPDATE users SET last_seen=%s WHERE id=%s',(time.time(),row['id']))
                g.user=row
            return fn(*args,**kwargs)
        return wrapped
    return decorator

def public_user(u):return {**{k:u[k] for k in ('id','username','first_name','last_name','role','status','created_at','last_login','last_seen','login_count')},'permissions':effective_permissions(u),'stockOwnerId':u.get('stock_owner_id'),'positionId':u.get('position_id'),'positionName':u.get('position_name'),'phone':u.get('phone',''),'email':u.get('email','')}
def rate_limit(keys,max_attempts=8,window=900):
    now=time.time()
    with db() as c:
        for key in keys:
            key=digest(key)
            execute(c,'INSERT INTO rate_buckets (bucket,started_at,attempts) VALUES (%s,%s,1) ON CONFLICT (bucket) DO UPDATE SET attempts=CASE WHEN rate_buckets.started_at<%s THEN 1 ELSE rate_buckets.attempts+1 END,started_at=CASE WHEN rate_buckets.started_at<%s THEN %s ELSE rate_buckets.started_at END',(key,now,now-window,now-window,now))
            if one(c,'SELECT attempts FROM rate_buckets WHERE bucket=%s',(key,))['attempts']>max_attempts:raise ApiError('Příliš mnoho pokusů. Zkuste to za 15 minut.',429)
def client_ip():return request.headers.get('X-Forwarded-For',request.remote_addr or 'unknown').split(',')[-1].strip()
def session_response(c,u):
    token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24);now=time.time()
    execute(c,'INSERT INTO sessions (token_hash,user_id,csrf,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)',(digest(token),u['id'],csrf,now,now+SESSION_DAYS*86400))
    execute(c,'UPDATE users SET last_login=%s,last_seen=%s,login_count=login_count+1 WHERE id=%s',(now,now,u['id']))
    audit(c,u['id'],'login','Úspěšné přihlášení')
    response=jsonify(ok=True);response.set_cookie(cookie_name(),token,max_age=SESSION_DAYS*86400,httponly=True,secure=SECURE,samesite='Lax',path=request.script_root or '/');return response
@app.post('/api/login')
def login():
    data=body();username=textfield(data,'username',1,64);password=data.get('password','')
    if not isinstance(password,str) or len(password)>128:raise ApiError('Nesprávné přihlašovací údaje.',401)
    rate_limit(['login-name:'+username.casefold()],5);rate_limit(['login-ip:'+client_ip()],40)
    with db() as c:
        u=one(c,'SELECT * FROM users WHERE username_key=%s',(username.casefold(),))
        valid=password_ok(password,u['password_hash'] if u else DUMMY) and u is not None and u['status']=='active'
        if valid:
            execute(c,'DELETE FROM rate_buckets WHERE bucket=%s',(digest('login-name:'+username.casefold()),))
            return session_response(c,u)
        if u:audit(c,u['id'],'login_failed','Neúspěšný pokus o přihlášení')
    if not getattr(g,'venue',None):
        from server.staff import employee_login
        response=employee_login(data,username,password)
        if response is not None:
            with db(central=True) as c:execute(c,'DELETE FROM rate_buckets WHERE bucket=%s',(digest('login-name:'+username.casefold()),))
            return response
    return jsonify(error='Nesprávné přihlašovací údaje nebo zablokovaný účet.'),401
@app.post('/api/register')
def register():
    data=body();first=textfield(data,'firstName');last=textfield(data,'lastName');username=textfield(data,'username',3,32);password=data.get('password','');code=textfield(data,'inviteCode',8,100).upper().replace(' ','')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{3,32}',username):raise ApiError('Uživatelské jméno: 3–32 písmen bez diakritiky, číslic nebo znaků . _ -')
    if not isinstance(password,str) or not 8<=len(password)<=128:raise ApiError('Heslo musí mít 8–128 znaků.')
    rate_limit(['register:'+client_ip()],15)
    with db() as c:
        if one(c,'SELECT id FROM users WHERE username_key=%s',(username.casefold(),)):raise ApiError('Toto uživatelské jméno je již obsazené.',409)
        invite=one(c,'SELECT * FROM invitations WHERE code_hash=%s',(digest(code),))
        if not invite:raise ApiError('Pozvánka je neplatná, použitá nebo vypršela.')
        count=execute(c,'UPDATE invitations SET used_count=used_count+1 WHERE id=%s AND revoked=0 AND expires_at>%s AND used_count<max_uses',(invite['id'],time.time())).rowcount
        if count!=1:raise ApiError('Pozvánka je neplatná, použitá nebo vypršela.')
        id=uid();execute(c,"INSERT INTO users (id,username,username_key,first_name,last_name,password_hash,role,created_at) VALUES (%s,%s,%s,%s,%s,%s,'user',%s)",(id,username,username.casefold(),first,last,password_hash(password),time.time()))
        if getattr(g,'venue',None):
            execute(c,'UPDATE users SET stock_owner_id=%s WHERE id=%s',(g.venue['owner_id'],id))
            from server.staff import index_employee
            index_employee(c,{'id':id,'username_key':username.casefold()})
        execute(c,'INSERT INTO invitation_uses (id,invite_id,user_id,used_at) VALUES (%s,%s,%s,%s)',(uid(),invite['id'],id,time.time()))
        audit(c,id,'registered','Registrace pomocí pozvánky')
        return session_response(c,one(c,'SELECT * FROM users WHERE id=%s',(id,)))
@app.get('/api/me')
@authenticated()
def me():
    with db() as c:
        unlocked=allrows(c,'SELECT product_id,created_at FROM unlocks WHERE user_id=%s',(workspace_id(),))
        state=json.loads(g.user['state_json']);state.update(unlocks={r['product_id']:{'reason':'free','paid':0,'at':r['created_at']*1000} for r in unlocked},ownerPreview=g.user['role']=='admin')
        return jsonify(user=public_user(g.user),csrf=g.user['csrf'],state=state,freeUnlocks=FREE_UNLOCKS)
@app.post('/api/logout')
@authenticated()
def logout():
    with db() as c:execute(c,'DELETE FROM sessions WHERE token_hash=%s',(g.user['token_hash'],));audit(c,g.user['id'],'logout','Odhlášení')
    r=jsonify(ok=True);r.delete_cookie(cookie_name(),path=request.script_root or '/');return r
@app.get('/api/catalog')
@authenticated()
def catalog():
    if not (has_permission(g.user,'catalog.view') or (has_permission(g.user,'inventory.run') and has_permission(g.user,'inventory.bar'))):raise ApiError('Nemáte oprávnění otevřít katalog.',403)
    return jsonify(CATALOG)
@app.get('/api/shop')
@authenticated(permission='catalog.view')
def shop_offers():
    current=choose_week(SHOP_TEMPLATES)
    with db() as c:owned={r['product_id'] for r in allrows(c,'SELECT product_id FROM unlocks WHERE user_id=%s',(workspace_id(),))}
    current['offers']=[quote(t,PRODUCTS,owned) for t in current['offers']]
    return jsonify(**current,templateCount=len(SHOP_TEMPLATES),paymentsEnabled=False,freeUnlocks=FREE_UNLOCKS,adminFree=g.user['role']=='admin')
@app.post('/api/shop/bundles/<bundle_id>/unlock')
@authenticated(bottles=True,permission='catalog.unlock')
def unlock_bundle(bundle_id):
    if not has_permission(g.user,'catalog.unlock'):raise ApiError('Nemáte oprávnění odemykat nápoje.',403)
    data=body();current=choose_week(SHOP_TEMPLATES)
    if data.get('weekKey')!=current['weekKey']:raise ApiError('Nabídka se změnila. Načtěte aktuální balíčky.',409)
    template=next((t for t in current['offers'] if t['id']==bundle_id),None)
    if not template:raise ApiError('Tento balíček už není v aktuální nabídce.',409)
    added=0
    with db() as c:
        for product_id in template['productIds']:
            added+=execute(c,'INSERT INTO unlocks (user_id,product_id,created_at) VALUES (%s,%s,%s) ON CONFLICT (user_id,product_id) DO NOTHING',(workspace_id(),product_id,time.time())).rowcount
        if added:audit(c,g.user['id'],'bundle_unlocked',template['title'])
    return jsonify(ok=True,productIds=template['productIds'],addedCount=added,paidCents=0,currency='EUR')
@app.post('/api/unlocks')
@authenticated(bottles=True,permission='catalog.unlock')
def unlock():
    if not has_permission(g.user,'catalog.unlock'):raise ApiError('Nemáte oprávnění odemykat nápoje.',403)
    id=body().get('productId')
    if id not in PRODUCTS:raise ApiError('Produkt neexistuje.',404)
    with db() as c:
        n=execute(c,'INSERT INTO unlocks (user_id,product_id,created_at) VALUES (%s,%s,%s) ON CONFLICT (user_id,product_id) DO NOTHING',(workspace_id(),id,time.time())).rowcount
        if n:audit(c,g.user['id'],'product_unlocked',PRODUCTS[id]['name'])
    return jsonify(ok=True)
@app.get('/api/products/<id>')
@authenticated()
def product(id):
    if not (has_permission(g.user,'catalog.view') or (has_permission(g.user,'inventory.run') and has_permission(g.user,'inventory.bar'))):raise ApiError('Nemáte oprávnění otevřít produkt.',403)
    if id not in PRODUCTS:raise ApiError('Produkt neexistuje.',404)
    with db() as c:
        if not (FREE_UNLOCKS or g.user['role']=='admin') or not one(c,'SELECT product_id FROM unlocks WHERE user_id=%s AND product_id=%s',(workspace_id(),id)):raise ApiError('Nejdříve odemkněte produkt.',403)
        audit(c,g.user['id'],'product_opened',PRODUCTS[id]['name'])
    return jsonify(PRODUCTS[id])
@app.get('/api/barcode/<code>')
@authenticated()
def barcode_lookup(code):
    if not (has_permission(g.user,'stock.edit') or (has_permission(g.user,'inventory.run') and has_permission(g.user,'inventory.bar'))):raise ApiError('Nemáte oprávnění vyhledávat produkty.',403)
    if not re.fullmatch(r'(?:[0-9]{8}|[0-9]{12,14})',code):raise ApiError('Neplatný čárový kód.')
    digits=[int(x) for x in code]
    if (sum(digits[-2::-2])*3+sum(digits[-3::-2])+digits[-1])%10:raise ApiError('Nesouhlasí kontrolní číslice kódu.')
    rate_limit(['barcode:'+g.user['id']],40,60)
    from urllib.request import Request,urlopen
    from urllib.error import URLError
    url='https://world.openfoodfacts.org/api/v2/product/'+code+'.json?fields=product_name,brands,quantity,product_quantity,product_quantity_unit'
    try:
        with urlopen(Request(url,headers={'User-Agent':'Barometr/0.5 (bottle inventory; https://github.com/dohnalvojtech8-gif/Barometr)'}),timeout=7) as response:
            data=json.loads(response.read(65536))
    except (URLError,TimeoutError,ValueError,OSError):raise ApiError('Online databáze není dostupná. Ověřte etiketu a objem ručně.',503)
    if not isinstance(data,dict):raise ApiError('Online databáze vrátila neplatnou odpověď.',503)
    p=data.get('product',{})
    if data.get('status')!=1 or not isinstance(p,dict) or not p.get('product_name'):return jsonify(found=False,code=code)
    return jsonify(found=True,code=code,name=str(p.get('product_name',''))[:200],brands=str(p.get('brands',''))[:200],quantity=str(p.get('quantity',''))[:80],source='Open Food Facts',url='https://world.openfoodfacts.org/product/'+code)

def read_calibration(c,user_id,product_id,capacity):
    row=one(c,'SELECT points_json,updated_at FROM bottle_calibrations WHERE user_id=%s AND product_id=%s AND capacity=%s',(user_id,product_id,capacity))
    return {'productId':product_id,'capacity':capacity,'points':json.loads(row['points_json']),'updatedAt':row['updated_at'],'accuracyVerified':False} if row else None
@app.route('/api/calibrations/<product_id>/<int:capacity>',methods=['GET','PUT'])
@authenticated(bottles=True)
def calibration_profile(product_id,capacity):
    from server.calibration import validate_points,CalibrationError
    if product_id not in PRODUCTS or capacity not in [v['ml'] for v in PRODUCTS[product_id]['variants']]:raise ApiError('Neplatná varianta lahve.')
    with db() as c:
        if not one(c,'SELECT product_id FROM unlocks WHERE user_id=%s AND product_id=%s',(workspace_id(),product_id)):raise ApiError('Nejdříve odemkněte produkt.',403)
        if request.method=='PUT':
            data=body()
            if data.get('measured') is not True:raise ApiError('Potvrďte vlastní měření referenčních bodů.')
            try:points=validate_points(data.get('points'),capacity)
            except CalibrationError as error:raise ApiError(str(error))
            execute(c,'INSERT INTO bottle_calibrations (user_id,product_id,capacity,points_json,updated_at) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (user_id,product_id,capacity) DO UPDATE SET points_json=excluded.points_json,updated_at=excluded.updated_at',(workspace_id(),product_id,capacity,json.dumps(points),time.time()))
            audit(c,g.user['id'],'calibration_saved',PRODUCTS[product_id]['name']+' · '+str(capacity)+' ml')
        profile=read_calibration(c,workspace_id(),product_id,capacity)
    return jsonify(profile=profile)
@app.get('/api/vision/status')
@authenticated(admin=True)
def vision_status():
    from server.vision import configuration
    return jsonify(configuration())
@app.post('/api/vision/analyze')
@authenticated(admin=True)
def vision_analyze():
    from server.vision import analyze,VisionError,configuration
    data=body();product_id=data.get('productId');capacity=data.get('capacity')
    if not isinstance(product_id,str) or product_id not in PRODUCTS or capacity not in [v['ml'] for v in PRODUCTS[product_id]['variants']]:raise ApiError('Neplatný produkt nebo objem.')
    with db() as c:
        unlocked=one(c,'SELECT product_id FROM unlocks WHERE user_id=%s AND product_id=%s',(workspace_id(),product_id))
        profile=read_calibration(c,workspace_id(),product_id,capacity)
    if not unlocked:raise ApiError('Nejdřív odemkněte produkt.',403)
    if not configuration()['enabled']:raise ApiError('Automatický skener není připojený. Administrátor musí nastavit a povolit analýzu obrazu.',503)
    rate_limit(['vision:'+g.user['id']],60,3600)
    try:result=analyze(data.get('images'),PRODUCTS[product_id],capacity,profile)
    except VisionError as error:raise ApiError(str(error),error.status)
    return jsonify(result)

@app.put('/api/scan-photos/<photo_id>')
@authenticated(bottles=True)
def put_scan_photo(photo_id):
    import base64,binascii
    if not re.fullmatch(r'[a-zA-Z0-9-]{1,100}',photo_id):raise ApiError('Neplatné ID snímku.')
    data=body();image=data.get('image','')
    if not isinstance(image,str) or not image.startswith('data:image/jpeg;base64,') or len(image)>300000:raise ApiError('Neplatný nebo příliš velký snímek.')
    try:raw=base64.b64decode(image.split(',',1)[1],validate=True)
    except (ValueError,binascii.Error):raise ApiError('Neplatný snímek.')
    if not raw.startswith(b'\xff\xd8') or not raw.endswith(b'\xff\xd9'):raise ApiError('Snímek musí být JPEG.')
    with db() as c:
        existing=one(c,'SELECT user_id FROM scan_photos WHERE id=%s',(photo_id,))
        if existing and existing['user_id']!=workspace_id():raise ApiError('Snímek není dostupný.',404)
        execute(c,'INSERT INTO scan_photos (id,user_id,jpeg,created_at) VALUES (%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET jpeg=excluded.jpeg WHERE scan_photos.user_id=excluded.user_id',(photo_id,workspace_id(),image,time.time()))
    return jsonify(id=photo_id)
@app.get('/api/scan-photos/<photo_id>')
@authenticated()
def get_scan_photo(photo_id):
    import base64
    if not (has_permission(g.user,'inventory.history') or (has_permission(g.user,'inventory.run') and has_permission(g.user,'inventory.bar'))):raise ApiError('Nemáte oprávnění prohlížet snímky inventur.',403)
    with db() as c:photo=one(c,'SELECT jpeg FROM scan_photos WHERE id=%s AND user_id=%s',(photo_id,workspace_id()))
    if not photo:raise ApiError('Snímek nebyl nalezen.',404)
    response=make_response(base64.b64decode(photo['jpeg'].split(',',1)[1]));response.headers['Content-Type']='image/jpeg';response.headers['Cache-Control']='private, no-store';return response

@app.put('/api/state')
@authenticated()
def put_state():
    data=body();clean={}
    old_state=json.loads(g.user['state_json'])
    clean.update({k:old_state[k] for k in ('cycle','closing') if k in old_state})
    if not (has_permission(g.user,'inventory.run') and has_permission(g.user,'inventory.bar')) and any(data.get(k,old_state.get(k))!=old_state.get(k) for k in ('rows','records','inventoryPlan')):raise ApiError('Nemáte oprávnění provádět inventury.',403)
    for key in ('cycle','closing'):
        if key in data:clean[key]=data[key]
    if clean.get('cycle','Měsíční') not in ('Denní','Týdenní','Měsíční'):raise ApiError('Neplatný cyklus.')
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',str(clean.get('closing','04:00'))):raise ApiError('Neplatný čas.')
    old=json.loads(g.user['state_json'])
    plan=data.get('inventoryPlan',old.get('inventoryPlan',{'entries':[]}))
    if not isinstance(plan,dict) or not isinstance(plan.get('entries'),list) or len(plan['entries'])>500:raise ApiError('Neplatný plán inventury.')
    if plan.get('runId') is not None and (not isinstance(plan['runId'],str) or not re.fullmatch(r'[a-zA-Z0-9-]{1,48}',plan['runId'])):raise ApiError('Neplatné kolo inventury.')
    if not (FREE_UNLOCKS or g.user['role']=='admin') and plan['entries']:raise ApiError('Inventura zatím není pro uživatele povolená.',403)
    if not (FREE_UNLOCKS or g.user['role']=='admin') and (data.get('rows') or data.get('records')):raise ApiError('Evidence lahví zatím není pro uživatele povolená.',403)
    if FREE_UNLOCKS or g.user['role']=='admin':
        rows=data.get('rows',old.get('rows',[]));records=data.get('records',old.get('records',[]))
        if not isinstance(rows,list) or len(rows)>500 or not isinstance(records,list) or len(records)>3000:raise ApiError('Příliš mnoho záznamů.')
        with db() as c:ids={r['product_id'] for r in allrows(c,'SELECT product_id FROM unlocks WHERE user_id=%s',(workspace_id(),))}
        seen=set()
        for row in rows:
            if not isinstance(row,dict) or row.get('productId') not in ids or row.get('id') in seen:raise ApiError('Neplatná nebo neodemčená lahev.')
            seen.add(row.get('id'));p=PRODUCTS[row['productId']]
            if row.get('capacity') not in [v['ml'] for v in p['variants']]:raise ApiError('Neplatný objem lahve.')
            for k in ('ml','start','sold40','sold20','otherMl'):
                if type(row.get(k)) not in (int,float) or not 0<=row[k]<=100000:raise ApiError('Neplatné množství.')
            if row['ml']>row['capacity'] or row['start']>row['capacity']:raise ApiError('Objem překračuje kapacitu lahve.')
            if not isinstance(row.get('label'),str) or len(row['label'])>80:raise ApiError('Neplatné označení lahve.')
        for r in records:
            if not isinstance(r,dict) or r.get('productId') not in ids or type(r.get('ml')) not in (int,float):raise ApiError('Neplatná historie.')
        managed={'actorId','actorName','actorUsername','recordedAt','at'}
        previous=old.get('records',[])
        if g.user['role']!='admin':
            if len(records)<len(previous) or any({k:v for k,v in r.items() if k not in managed}!={k:v for k,v in records[i].items() if k not in managed} for i,r in enumerate(previous)):
                raise ApiError('Historii může upravovat nebo mazat pouze majitel.',403)
        for i,record in enumerate(records):
            if i<len(previous):
                for key in managed:
                    if key in previous[i]:record[key]=previous[i][key]
                    else:record.pop(key,None)
            else:
                record.update(actorId=g.user['id'],actorName=(g.user['first_name']+' '+g.user['last_name']).strip() or g.user['username'],actorUsername=g.user['username'],recordedAt=time.time())
                if g.user['role']!='admin':record['at']=int(time.time()*1000)
        entry_ids=set()
        for entry in plan['entries']:
            if not isinstance(entry,dict) or not isinstance(entry.get('id'),str) or not re.fullmatch(r'[a-zA-Z0-9-]{1,48}',entry['id']) or entry['id'] in entry_ids:raise ApiError('Neplatná položka plánu.')
            entry_ids.add(entry['id'])
            if entry.get('productId') not in ids or entry.get('capacity') not in [v['ml'] for v in PRODUCTS[entry['productId']]['variants']]:raise ApiError('Neplatný produkt nebo objem v plánu.')
            if not isinstance(entry.get('label',''),str) or len(entry.get('label',''))>80:raise ApiError('Neplatný název v plánu.')
            if entry.get('status','pending') not in ('pending','done','skipped'):raise ApiError('Neplatný stav plánu.')
            if type(entry.get('purchasePrice',0)) not in (int,float) or not 0<=entry.get('purchasePrice',0)<=1000000:raise ApiError('Neplatná nákupní cena lahve.')
            if entry.get('rowId') and entry['rowId'] not in seen:raise ApiError('Lahev plánu není v inventuře.')
        clean.update(rows=rows,records=records)
    else:clean.update(rows=[],records=[])
    clean['inventoryPlan']=plan
    with db() as c:
        changed=execute(c,'UPDATE users SET state_json=%s WHERE id=%s AND state_json=%s',(json.dumps(clean,ensure_ascii=False),workspace_id(),g.user['state_json'])).rowcount
        if changed!=1:raise ApiError('Inventura byla mezitím změněna. Obnovte stránku a změnu zopakujte.',409)
        if clean.get('rows')!=old.get('rows') or clean.get('records')!=old.get('records'):audit(c,g.user['id'],'inventory_saved','Uložení inventury')
        elif clean.get('inventoryPlan')!=old.get('inventoryPlan'):audit(c,g.user['id'],'inventory_plan_changed','Změna pořadí nebo průběhu inventury')
        elif clean.get('cycle')!=old.get('cycle') or clean.get('closing')!=old.get('closing'):audit(c,g.user['id'],'settings_changed','Změna nastavení')
    return jsonify(ok=True)
@app.post('/api/activity')
@authenticated()
def activity():
    data=body();action=data.get('action');labels={'catalog':'Otevření katalogu','library':'Moje lahve','overview':'Přehled inventury','history':'Historie měření','settings':'Nastavení','users':'Správa uživatelů','search':'Hledání v katalogu','heartbeat':'Aktivní aplikace'}
    if action not in labels:raise ApiError('Neplatná událost.')
    if action=='users' and g.user['role']!='admin':raise ApiError('Zakázáno.',403)
    with db() as c:
        if action!='heartbeat':
            last=one(c,'SELECT created_at FROM events WHERE user_id=%s AND action=%s ORDER BY created_at DESC LIMIT 1',(g.user['id'],'view_'+action))
            if not last or time.time()-last['created_at']>20:audit(c,g.user['id'],'view_'+action,labels[action])
    return jsonify(ok=True)
@app.post('/api/admin/users')
@authenticated(admin=True)
def employee_create():
    from server.employees import create_employee
    rate_limit(['employee-create:'+g.user['id']],30)
    values=body()
    owner_id=g.venue['owner_id'] if getattr(g,'venue',None) else g.user['id']
    with db() as c:user=create_employee(c,values,owner_id,g.user['id'])
    return jsonify(user=user,hasPin=True,venueUrl=(request.script_root or '')+'/'),201

@app.get('/api/admin/users')
@authenticated(permission='users.manage')
def users_list():
    with db() as c:
        users=allrows(c,'SELECT u.id,u.username,u.first_name,u.last_name,u.phone,u.email,u.role,u.status,u.created_at,u.last_login,u.last_seen,u.login_count,u.permissions_json,u.stock_owner_id,u.position_id,p.name AS position_name FROM users u LEFT JOIN staff_positions p ON p.id=u.position_id ORDER BY u.created_at DESC')
        counts={r['user_id']:r['n'] for r in allrows(c,'SELECT user_id,COUNT(*) AS n FROM events WHERE created_at>%s GROUP BY user_id',(time.time()-7*86400,))}
        for u in users:
            u['activity7d']=counts.get(u['id'],0);u['permissions']=effective_permissions(u);u['stockOwnerId']=u.pop('stock_owner_id',None);u.pop('permissions_json',None)
    return jsonify(users=users)
@app.get('/api/admin/users/<id>')
@authenticated(permission='users.manage')
def user_detail(id):
    limit=min(max(request.args.get('limit',100,type=int),1),200);offset=max(request.args.get('offset',0,type=int),0)
    with db() as c:
        u=one(c,'SELECT u.*,p.name AS position_name FROM users u LEFT JOIN staff_positions p ON p.id=u.position_id WHERE u.id=%s',(id,))
        if not u:raise ApiError('Účet neexistuje.',404)
        total=one(c,'SELECT COUNT(*) AS n FROM events WHERE user_id=%s',(id,))['n']
        events=allrows(c,'SELECT id,action,detail,created_at FROM events WHERE user_id=%s ORDER BY created_at DESC LIMIT %s OFFSET %s',(id,limit,offset))
        sessions=one(c,'SELECT COUNT(*) AS n FROM sessions WHERE user_id=%s AND expires_at>%s',(id,time.time()))['n']
    return jsonify(user=public_user(u),events=events,total=total,activeSessions=sessions)
@app.post('/api/admin/invites')
@authenticated(permission='users.manage')
def invite_create():
    data=body();label=str(data.get('label','Pozvánka'))[:80].strip() or 'Pozvánka';days=data.get('days',7);uses=data.get('maxUses',1)
    if type(days) is not int or not 1<=days<=30 or type(uses) is not int or not 1<=uses<=50:raise ApiError('Platnost 1–30 dní, počet použití 1–50.')
    code='BM-'+secrets.token_hex(12).upper();id=uid();now=time.time()
    with db() as c:
        execute(c,'INSERT INTO invitations (id,code_hash,label,created_by,created_at,expires_at,max_uses) VALUES (%s,%s,%s,%s,%s,%s,%s)',(id,digest(code),label,g.user['id'],now,now+days*86400,uses));audit(c,g.user['id'],'invite_created','Vygenerování registrační pozvánky')
    return jsonify(id=id,code=code,expiresAt=now+days*86400,maxUses=uses)
@app.get('/api/admin/invites')
@authenticated(permission='users.manage')
def invite_list():
    with db() as c:return jsonify(invites=allrows(c,'SELECT i.id,i.label,i.created_at,i.expires_at,i.max_uses,i.used_count,i.revoked,u.username AS creator FROM invitations i LEFT JOIN users u ON i.created_by=u.id ORDER BY i.created_at DESC LIMIT 100'))
@app.post('/api/admin/invites/<id>/revoke')
@authenticated(permission='users.manage')
def invite_revoke(id):
    with db() as c:execute(c,'UPDATE invitations SET revoked=1 WHERE id=%s',(id,));audit(c,g.user['id'],'invite_revoked','Zrušení pozvánky')
    return jsonify(ok=True)
@app.post('/api/admin/users/<id>/status')
@authenticated(permission='users.manage')
def user_status(id):
    status=body().get('status')
    if status not in ('active','suspended'):raise ApiError('Neplatný stav.')
    with db() as c:
        target=one(c,'SELECT * FROM users WHERE id=%s',(id,))
        if not target:raise ApiError('Účet neexistuje.',404)
        if target['role']=='admin':raise ApiError('Administrátory zde nelze blokovat.',403)
        execute(c,'UPDATE users SET status=%s WHERE id=%s',(status,id));execute(c,'DELETE FROM sessions WHERE user_id=%s',(id,));audit(c,g.user['id'],'user_status_changed',('Zablokování' if status=='suspended' else 'Obnovení')+' účtu '+target['username'])
    return jsonify(ok=True)
@app.delete('/api/admin/users/<id>')
@authenticated(admin=True)
def user_delete(id):
    confirmation=body().get('confirmation')
    with db() as c:
        target=one(c,'SELECT * FROM users WHERE id=%s',(id,))
        if not target:raise ApiError('Účet neexistuje.',404)
        if target['role']=='admin':raise ApiError('Administrátory zde nelze smazat.',403)
        if confirmation!=target['username']:raise ApiError('Pro potvrzení zadejte přesné uživatelské jméno.')
        if getattr(g,'venue',None):
            from server.staff import directory_table
            execute(c,'DELETE FROM '+directory_table(c)+' WHERE venue_id=%s AND user_id=%s',(g.venue['id'],id))
        execute(c,'DELETE FROM users WHERE id=%s',(id,));audit(c,g.user['id'],'user_deleted','Odstranění testovacího účtu a jeho záznamů')
    return jsonify(ok=True)
@app.post('/api/password')
@authenticated()
def change_password():
    data=body();old=data.get('oldPassword','');new=data.get('newPassword','')
    minimum=4 if g.user['role']=='admin' else 8
    if not isinstance(old,str) or not isinstance(new,str) or not minimum<=len(new)<=128:raise ApiError(f'Nové heslo musí mít {minimum}–128 znaků.')
    rate_limit(['password:'+g.user['id']],5)
    central_owner=bool(getattr(g,'venue',None) and g.user['role']=='admin')
    with db(central=central_owner) as c:
        account=one(c,'SELECT * FROM users WHERE id=%s',(g.user['id'],))
        if not account or not password_ok(old,account['password_hash']):raise ApiError('Současné heslo není správné.',403)
        execute(c,'UPDATE users SET password_hash=%s WHERE id=%s',(password_hash(new),account['id']))
        token=digest(request.cookies.get(COOKIE,'')) if central_owner else g.user['token_hash']
        execute(c,'DELETE FROM sessions WHERE user_id=%s AND token_hash<>%s',(account['id'],token))
        audit(c,account['id'],'password_changed','Změna hesla')
    return jsonify(ok=True)
def write_stock_changes(c,owner,before,after,revision):
    from server.notifications import record_changes
    record_changes(c,before,after)
    from server.stock import change_rows
    stores={r['id']:r['name'] for r in before.get('stores',[])+after['stores']}
    for r in change_rows(before,after):
        execute(c,'INSERT INTO stock_change_log (id,owner_id,actor_id,actor_name,store_id,store_name,entity_id,kind,label,field,before_json,after_json,revision,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(uid(),owner,g.user['id'],g.user['username'],r['store'],stores.get(r['store'],''),r['entity'],r['kind'],r['label'],r['field'],json.dumps(r['before'],ensure_ascii=False),json.dumps(r['after'],ensure_ascii=False),revision,time.time()))

def stock_latest_changes(c,owner,data):
    # Resolve the current profile name; historical usernames are only a fallback.
    rows=allrows(c,"SELECT l.*,u.first_name,u.last_name FROM stock_change_log l LEFT JOIN users u ON u.id=l.actor_id WHERE l.owner_id=%s AND l.field='qty' AND l.kind IN ('inventura','pohyb') ORDER BY l.created_at DESC,l.id DESC",(owner,))
    entities={r['id']:r for r in data.get('counts',[])+data.get('moves',[])}
    latest={}
    for r in rows:
        entity=entities.get(r['entity_id'])
        if not entity:continue
        key=entity['store']+'|'+entity['product']
        if key in latest:continue
        latest[key]={'before':json.loads(r['before_json']),'after':json.loads(r['after_json']),'at':r['created_at'],'name':(' '.join(filter(None,[r['first_name'],r['last_name']])).strip() or r['actor_name'])}
    return latest

@app.route('/api/stock',methods=['GET','PUT'])
@authenticated(permission='stock.view')
def stock_document():
    from server.stock import validate_stock, StockValidationError, required_permissions, prepare_counts, validate_active_changes,attribute_records
    owner_id=g.user.get('stock_owner_id') or g.user['id']
    if request.method=='GET':
        with db() as c:
            row=one(c,'SELECT data_json,revision FROM stock_documents WHERE user_id=%s',(owner_id,))
            document=json.loads(row['data_json']) if row else {'stores':[{'id':'main','name':'Hlavní sklad'}],'products':[],'counts':[],'moves':[],'draft':None,'barInventories':[]}
            document=scoped_stock(document,store_scope(c,g.user))
            latest=stock_latest_changes(c,owner_id,document)
        return jsonify(data=document,revision=row['revision'] if row else 0,latestChanges=latest)
    data=body()
    if type(data.get('revision')) is not int or data['revision']<0:raise ApiError('Neplatná verze skladu.')
    try:clean=validate_stock(data.get('data'))
    except (StockValidationError,TypeError,KeyError) as e:raise ApiError(str(e) if isinstance(e,StockValidationError) else 'Neplatná skladová data.')
    revision=data['revision']
    with db() as c:
        empty={'stores':[],'products':[],'counts':[],'moves':[],'draft':None,'barInventories':[]}
        execute(c,'INSERT INTO stock_documents (user_id,revision,data_json,updated_at) VALUES (%s,0,%s,%s) ON CONFLICT (user_id) DO NOTHING',(owner_id,json.dumps(empty),time.time()))
        row=one(c,'SELECT data_json,revision FROM stock_documents WHERE user_id=%s',(owner_id,))
        if row['revision']!=revision:raise ApiError('Sklad byl změněn na jiném zařízení. Načtěte aktuální stav a změnu zopakujte.',409)
        old=json.loads(row['data_json'])
        clean=merge_scoped_stock(old,clean,store_scope(c,g.user))
        try:clean=validate_stock(clean)
        except StockValidationError as e:raise ApiError(str(e))
        for permission in required_permissions(old,clean):
            if not has_permission(g.user,permission):raise ApiError('K této změně nemáte oprávnění: '+PERMISSIONS[permission][0]+'.',403)
        try:validate_active_changes(old,clean)
        except StockValidationError as e:raise ApiError(str(e))
        clean=prepare_counts(old,attribute_records(old,clean,g.user))
        from server.reviews import stage,protect_closed,event as review_event
        corrected=protect_closed(old,clean,data.get('correctionReason'))
        clean=stage(c,old,clean,owner_id)
        changed=execute(c,'UPDATE stock_documents SET data_json=%s,revision=revision+1,updated_at=%s WHERE user_id=%s AND revision=%s',(json.dumps(clean,ensure_ascii=False),time.time(),owner_id,revision)).rowcount
        if changed!=1:raise ApiError('Sklad byl změněn na jiném zařízení. Obnovte stránku.',409)
        write_stock_changes(c,owner_id,old,clean,revision+1)
        if corrected:
            for key in ('counts','barInventories'):
                current={r['id']:r for r in clean.get(key,[])}
                for row in old.get(key,[]):
                    if row.get('reviewId') and current.get(row['id'])!=row:review_event(c,{'id':row['reviewId']},'corrected',data['correctionReason'].strip(),{'before':row,'after':current.get(row['id'])})
        audit(c,g.user['id'],'stock_saved','Uložení skladů a inventur')
        visible=scoped_stock(clean,store_scope(c,g.user))
        latest=stock_latest_changes(c,owner_id,visible)
    return jsonify(ok=True,revision=revision+1,data=visible,latestChanges=latest,pendingInventoryIds=getattr(g,'pending_inventory_ids',[]))

@app.get('/api/admin/stock-changes')
@authenticated(permission='stock.audit')
def stock_changes():
    limit=100;offset=max(0,request.args.get('offset',0,type=int));conditions=[];args=[]
    if g.user['role']!='admin':conditions.append('owner_id=%s');args.append(g.user.get('stock_owner_id') or g.user['id'])
    for param,column in [('store','store_id'),('owner','owner_id'),('kind','kind')]:
        value=request.args.get(param,'')
        if value:conditions.append(column+'=%s');args.append(value)
    for param,operator in [('from','>='),('to','<=')]:
        value=request.args.get(param,'')
        if value:
            try:
                from datetime import datetime,timezone
                stamp=datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()+(86399.999 if param=='to' else 0)
            except ValueError:raise ApiError('Neplatné datum.')
            conditions.append('created_at'+operator+'%s');args.append(stamp)
    query=request.args.get('q','').strip()
    if query:conditions.append('(LOWER(label) LIKE %s OR LOWER(actor_name) LIKE %s)');args.extend(['%'+query.lower()+'%']*2)
    with db() as c:
        scope=store_scope(c,g.user)
    if scope is not None:
        if not scope:return jsonify(changes=[],total=0,offset=offset,limit=limit,stores=[])
        conditions.append('store_id IN ('+','.join(['%s']*len(scope))+')');args.extend(scope)
    where=' WHERE '+' AND '.join(conditions) if conditions else ''
    with db() as c:
        total=one(c,'SELECT count(*) AS n FROM stock_change_log'+where,tuple(args))['n']
        rows=allrows(c,'SELECT * FROM stock_change_log'+where+' ORDER BY created_at DESC,id DESC LIMIT %s OFFSET %s',tuple(args+[limit,offset]))
        stores=allrows(c,'SELECT DISTINCT store_id,store_name FROM stock_change_log'+where+' ORDER BY store_name',tuple(args))
    for row in rows:row['before']=json.loads(row.pop('before_json'));row['after']=json.loads(row.pop('after_json'))
    return jsonify(changes=rows,total=total,offset=offset,limit=limit,stores=stores)

@app.post('/api/admin/users/<id>/permissions')
@authenticated(admin=True)
def user_permissions(id):
    input_data=body();permissions=input_data.get('permissions')
    if not isinstance(permissions,dict) or set(permissions)-set(PERMISSIONS) or any(type(v) is not bool for v in permissions.values()):raise ApiError('Neplatná oprávnění.')
    with db() as c:
        target=one(c,'SELECT * FROM users WHERE id=%s',(id,))
        if not target:raise ApiError('Účet neexistuje.',404)
        if target['role']=='admin':raise ApiError('Oprávnění majitele nelze omezit.',403)
        from server.staff import set_access,UNCHANGED
        permissions=set_access(c,target,permissions,input_data.get('positionId',UNCHANGED))
        previous=effective_permissions(target)
        owner_id=input_data.get('stockOwnerId',target.get('stock_owner_id')) or None
        if owner_id is not None:
            owner=one(c,"SELECT * FROM users WHERE id=%s AND role='admin'",(owner_id,))
            if not owner:raise ApiError('Pracovní prostor musí patřit existujícímu majiteli.')
            owner_id=owner_scope(owner)
        execute(c,'UPDATE users SET permissions_json=%s,stock_owner_id=%s WHERE id=%s',(json.dumps(permissions),owner_id,id))
        execute(c,'INSERT INTO stock_change_log (id,owner_id,actor_id,actor_name,store_id,store_name,entity_id,kind,label,field,before_json,after_json,revision,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s)',(uid(),id,g.user['id'],g.user['username'],'','',id,'oprávnění',target['username'],'permissions',json.dumps(previous),json.dumps(permissions),time.time()))
        if owner_id!=target.get('stock_owner_id'):audit(c,g.user['id'],'workspace_changed','Změna přístupu ke skladům účtu '+target['username'])
        audit(c,g.user['id'],'permissions_changed','Změna oprávnění účtu '+target['username'])
    return jsonify(ok=True)

@app.get('/ocr/<path:name>')
def ocr_asset(name):return send_from_directory(WEB/'ocr',name)

@app.get('/scale.js')
def scale_script():return send_from_directory(WEB,'scale.js')

@app.get('/reference.js')
def reference_script():return send_from_directory(WEB,'reference.js')

@app.get('/stock.js')
def stock_script():return send_from_directory(WEB,'stock.js')

@app.get('/healthz')
def health():
    with db() as c:execute(c,'SELECT 1')
    from server.vision import configuration
    return jsonify(status='ok',version='1.4.0',application='NOIRA',database='supabase' if SUPABASE_DATABASE_URL else 'postgres',freeUnlocks=FREE_UNLOCKS,automaticLevelEnabled=configuration()['enabled'],shopBundleTemplates=len(SHOP_TEMPLATES))
@app.get('/')
def index():return send_from_directory(WEB,'index.html' if getattr(g,'venue',None) else 'owner.html')
@app.get('/designs.js')
def design_script():return send_from_directory(WEB,'designs.js')
@app.get('/designs')
def design_gallery():return send_from_directory(WEB,'designs.html')
@app.get('/app.js')
def javascript():return send_from_directory(WEB,'app.js')
@app.get('/shop.js')
def shop_script():return send_from_directory(WEB,'shop.js')
@app.get('/calibration.js')
def calibration_script():return send_from_directory(WEB,'calibration.js')
@app.get('/inventory.js')
def inventory_script():return send_from_directory(WEB,'inventory.js')
@app.get('/scanner.js')
def scanner_script():return send_from_directory(WEB,'scanner.js')
@app.get('/auth.js')
def auth_script():return send_from_directory(WEB,'auth.js')
@app.get('/style.css')
def css():return send_from_directory(WEB,'style.css')
@app.get('/assets/<path:name>')
def assets(name):return send_from_directory(ROOT/'aplikace/assets',name)
@app.get('/manifest.webmanifest')
def pwa_manifest():
    manifest=json.loads((WEB/'manifest.webmanifest').read_text())
    venue=getattr(g,'venue',None)
    if venue:
        prefix='/v/'+venue['id']+'/'
        manifest.update(id=prefix,name=venue['name']+' · NOIRA',short_name=venue['name'][:24],start_url=prefix,scope=prefix)
    else:manifest.update(name='NOIRA',short_name='NOIRA',description='Centrální panel majitele provozů')
    response=jsonify(manifest);response.mimetype='application/manifest+json'
    return response
@app.get('/sw.js')
def pwa_worker():
    response=send_from_directory(WEB,'sw.js',mimetype='application/javascript')
    response.headers['Cache-Control']='no-cache'
    return response
@app.get('/pwa.js')
def pwa_script():return send_from_directory(WEB,'pwa.js')
@app.get('/pwa.css')
def pwa_style():return send_from_directory(WEB,'pwa.css')
@app.get('/icons/<path:name>')
def pwa_icon(name):return send_from_directory(WEB/'icons',name)
@app.get('/favicon.ico')
def favicon():return send_from_directory(WEB/'icons','noira-logo.png',mimetype='image/png')
from server.work import register as register_work
register_work(app)




@app.get('/premium/')
def premium_preview():
    return send_from_directory(WEB/'premium','index.html')

@app.get('/premium/<path:name>')
def premium_preview_asset(name):
    return send_from_directory(WEB/'premium',name)

@app.get('/premium-theme.css')
def premium_theme():
    return send_from_directory(WEB,'premium-theme.css')

from server.allin import register as register_allin
register_allin(app)
from server.coowners import register as register_coowners
register_coowners(app)
from server.notifications import register as register_notifications
register_notifications(app)
from server.pos import register as register_pos
register_pos(app)
from server.staff import register as register_staff
register_staff(app)
from server.reviews import register as register_reviews
register_reviews(app)
from server.operations import register as register_operations
register_operations(app)
from server.controls import register as register_controls
register_controls(app)

@app.get('/noira.css')
def noira_theme():return send_from_directory(WEB,'noira.css')


@app.get('/i18n.js')
def i18n_script():return send_from_directory(WEB,'i18n.js')



@app.get('/motion.js')
def motion_script():return send_from_directory(WEB,'motion.js')

@app.get('/motion.css')
def motion_styles():return send_from_directory(WEB,'motion.css')


@app.get('/team.js')
def team_script():return send_from_directory(WEB,'team.js')

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.environ.get('PORT','10000')))

