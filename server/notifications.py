"""Opt-in Web Push. Preferences are account/scoped; venue changes use a durable outbox."""
import base64
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from flask import g,request,jsonify,send_from_directory

DEFAULTS={'inventory':True,'low_stock':True,'stock_movements':False}
OUTBOX_SQL="""CREATE TABLE IF NOT EXISTS notification_outbox (id TEXT PRIMARY KEY,kind TEXT NOT NULL,payload_json TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,sent_at DOUBLE PRECISION)"""
TABLES=[
"CREATE TABLE IF NOT EXISTS notification_keys (id TEXT PRIMARY KEY,private_key TEXT NOT NULL,public_key TEXT NOT NULL)",
"CREATE TABLE IF NOT EXISTS notification_profiles (user_id TEXT NOT NULL,scope TEXT NOT NULL,preferences_json TEXT NOT NULL,PRIMARY KEY(user_id,scope))",
"CREATE TABLE IF NOT EXISTS notification_subscriptions (id TEXT PRIMARY KEY,user_id TEXT NOT NULL,scope TEXT NOT NULL,endpoint TEXT NOT NULL,subscription_json TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL,UNIQUE(user_id,scope,endpoint))",
'CREATE INDEX IF NOT EXISTS notification_subscriber_scope ON notification_subscriptions(scope,user_id)']
POOL=ThreadPoolExecutor(max_workers=1,thread_name_prefix='noira-push')
LOCK=threading.Lock()
RUNNING=False
LAST_RUN={}


def subscription_valid(value):
    if not isinstance(value,dict):return False
    endpoint=value.get('endpoint','');keys=value.get('keys')
    if not isinstance(endpoint,str) or len(endpoint)>2048 or not isinstance(keys,dict):return False
    try:
        url=urlparse(endpoint);port=url.port
    except ValueError:return False
    host=url.hostname or ''
    allowed=host in ('fcm.googleapis.com','updates.push.services.mozilla.com','web.push.apple.com') or host.endswith('.notify.windows.com')
    if url.scheme!='https' or not allowed or url.username or url.password or port not in (None,443):return False
    for key,size in [('auth',16),('p256dh',65)]:
        raw=keys.get(key)
        if not isinstance(raw,str) or len(raw)>200:return False
        try:decoded=base64.urlsafe_b64decode(raw+'='*(-len(raw)%4))
        except (ValueError,TypeError):return False
        if len(decoded)!=size:return False
        if key=='p256dh' and decoded[0]!=4:return False
    return True


def record_changes(c,before,after):
    from server.app import execute,uid
    from server.stock import current_quantity
    venue=getattr(g,'venue',None)
    if not venue:return
    def add(kind,title,body,stores):
        payload={'title':title,'body':body,'url':'/v/'+venue['id']+'/#overview','stores':list(stores)}
        execute(c,'INSERT INTO notification_outbox (id,kind,payload_json,created_at) VALUES (%s,%s,%s,%s)',(uid(),kind,json.dumps(payload,ensure_ascii=False),time.time()))
        g.notification_changes=True
    old_counts={r['id'] for r in before.get('counts',[])}
    old_bars={r['id'] for r in before.get('barInventories',[])}
    counts=[r for r in after.get('counts',[]) if r['id'] not in old_counts]
    bars=[r for r in after.get('barInventories',[]) if r['id'] not in old_bars]
    if counts or bars:add('inventory',venue['name']+' · inventura','Byla uložena nová inventura nebo měření.',{r['store'] for r in counts}|({s['id'] for s in after['stores']} if bars else set()))
    old_moves={r['id'] for r in before.get('moves',[])}
    moves=[r for r in after.get('moves',[]) if r['id'] not in old_moves]
    if moves:add('stock_movements',venue['name']+' · pohyb zásob','Byl uložen příjem, výdej nebo přesun zboží.',{r['store'] for r in moves})
    old_products={p['id']:p for p in before.get('products',[])}
    low=[];low_stores=set()
    from server.work import local_products
    for store in after['stores']:
        if store.get('archivedAt'):continue
        for product in local_products(after,store['id']):
            qty=current_quantity(after,product['id'],store['id'])
            previous=current_quantity(before,product['id'],store['id']) if product['id'] in old_products else None
            if qty is not None and qty<product.get('min',0) and (previous is None or previous>=old_products.get(product['id'],{}).get('min',0)):
                low.append(product['name']);low_stores.add(store['id'])
    if low:add('low_stock',venue['name']+' · nízká zásoba',str(len(low))+' položek je pod nastaveným minimem.',low_stores)


def deliver(subscription,payload,private_key):
    from pywebpush import webpush
    return webpush(subscription_info=subscription,data=json.dumps(payload,ensure_ascii=False),vapid_private_key=private_key,
        vapid_claims={'sub':'mailto:allinbarometr@seznam.cz'},ttl=3600,timeout=10)


def dispatch(app,venue):
    global RUNNING
    from server.app import db,one,allrows,execute
    from server.work import store_scope
    from server.permissions import has_permission
    try:
        with app.test_request_context():
            g.venue=venue
            with db() as c:
                pending=allrows(c,'SELECT * FROM notification_outbox WHERE sent_at IS NULL AND attempts<3 AND created_at>%s ORDER BY created_at LIMIT 20',(time.time()-86400,))
                users=allrows(c,"SELECT * FROM users WHERE status='active'")
                access={u['id']:store_scope(c,u) for u in users if has_permission(u,'stock.view')}
            if not pending:return
            with db(central=True) as c:
                keys=one(c,"SELECT * FROM notification_keys WHERE id='vapid'")
                owner=one(c,"SELECT id FROM users WHERE id=%s AND status='active'",(venue['owner_id'],))
                subscriptions=allrows(c,'SELECT s.*,p.preferences_json FROM notification_subscriptions s JOIN notification_profiles p ON p.user_id=s.user_id AND p.scope=s.scope WHERE s.scope=%s OR (s.scope=%s AND s.user_id=%s)',(venue['id'],'owner',venue['owner_id']))
            if not keys:return
            for event in pending:
                payload=json.loads(event['payload_json']);stores=set(payload.pop('stores',[]));payload['tag']='noira-'+event['id']
                sent=set();failed=False
                for row in subscriptions:
                    if row['scope']=='owner':
                        if not owner:continue
                    else:
                        if row['user_id'] not in access:continue
                        scope=access[row['user_id']]
                        if scope is not None and not stores.issubset(scope):continue
                    if not json.loads(row['preferences_json']).get(event['kind'],False) or row['endpoint'] in sent:continue
                    try:deliver(json.loads(row['subscription_json']),payload,keys['private_key']);sent.add(row['endpoint'])
                    except Exception as error:
                        status=getattr(getattr(error,'response',None),'status_code',None)
                        if status in (404,410):
                            with db(central=True) as c:execute(c,'DELETE FROM notification_subscriptions WHERE id=%s',(row['id'],))
                        else:failed=True
                with db() as c:
                    execute(c,'UPDATE notification_outbox SET attempts=attempts+1,sent_at=%s WHERE id=%s',(None if failed else time.time(),event['id']))
                    execute(c,'DELETE FROM notification_outbox WHERE created_at<%s',(time.time()-7*86400,))
    except Exception as error:app.logger.warning('Notification delivery deferred: %s',type(error).__name__)
    finally:
        with LOCK:RUNNING=False


def register(app):
    from server.app import authenticated,db,execute,one,allrows,body,ApiError,uid,TEST_DB,SUPABASE_DATABASE_URL,WEB,rate_limit
    with db(central=True) as c:
        for sql in TABLES:execute(c,sql)
        if not TEST_DB:
            for table in ('notification_keys','notification_profiles','notification_subscriptions'):
                execute(c,'ALTER TABLE '+table+' ENABLE ROW LEVEL SECURITY')
                execute(c,'REVOKE ALL ON '+table+' FROM PUBLIC')
                if SUPABASE_DATABASE_URL:execute(c,'REVOKE ALL ON '+table+' FROM anon,authenticated')

    # Existing venues predate the outbox; provision the additive table before serving them.
    with db(central=True) as c:existing=allrows(c,'SELECT * FROM allin_venues')
    from server.allin import venue_context
    for venue in existing:
        with app.app_context(),venue_context(venue),db() as c:
            execute(c,OUTBOX_SQL)
            if not TEST_DB:
                execute(c,'ALTER TABLE notification_outbox ENABLE ROW LEVEL SECURITY')
                execute(c,'REVOKE ALL ON notification_outbox FROM PUBLIC')
                if SUPABASE_DATABASE_URL:execute(c,'REVOKE ALL ON notification_outbox FROM anon,authenticated')

    def scope():return g.venue['id'] if getattr(g,'venue',None) else 'owner'
    def profile(c):
        row=one(c,'SELECT preferences_json FROM notification_profiles WHERE user_id=%s AND scope=%s',(g.user['id'],scope()))
        return json.loads(row['preferences_json']) if row else dict(DEFAULTS)
    def save_profile(c,preferences):
        execute(c,'INSERT INTO notification_profiles (user_id,scope,preferences_json) VALUES (%s,%s,%s) ON CONFLICT(user_id,scope) DO UPDATE SET preferences_json=excluded.preferences_json',(g.user['id'],scope(),json.dumps(preferences)))
    def keypair(c):
        row=one(c,"SELECT * FROM notification_keys WHERE id='vapid'")
        if not row:
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import serialization
            key=ec.generate_private_key(ec.SECP256R1())
            private=base64.urlsafe_b64encode(key.private_numbers().private_value.to_bytes(32,'big')).decode().rstrip('=')
            public=base64.urlsafe_b64encode(key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)).decode().rstrip('=')
            execute(c,"INSERT INTO notification_keys (id,private_key,public_key) VALUES ('vapid',%s,%s) ON CONFLICT(id) DO NOTHING",(private,public))
            row=one(c,"SELECT * FROM notification_keys WHERE id='vapid'")
        return row

    @app.route('/api/notifications',methods=['GET','PUT'])
    @authenticated()
    def notification_settings():
        with db(central=True) as c:
            if request.method=='PUT':
                prefs=body().get('preferences')
                if not isinstance(prefs,dict) or set(prefs)!=set(DEFAULTS) or any(type(v) is not bool for v in prefs.values()):raise ApiError('Neplatné nastavení oznámení.')
                save_profile(c,prefs)
            key=keypair(c)
            count=one(c,'SELECT COUNT(*) AS n FROM notification_subscriptions WHERE user_id=%s AND scope=%s',(g.user['id'],scope()))['n']
            return jsonify(preferences=profile(c),publicKey=key['public_key'],devices=count,scope=scope())

    @app.route('/api/notifications/subscription',methods=['POST','DELETE'])
    @authenticated()
    def subscribe():
        data=body()
        with db(central=True) as c:
            if request.method=='DELETE':
                endpoint=data.get('endpoint')
                if not isinstance(endpoint,str):raise ApiError('Neplatné zařízení.')
                execute(c,'DELETE FROM notification_subscriptions WHERE user_id=%s AND scope=%s AND endpoint=%s',(g.user['id'],scope(),endpoint))
            else:
                sub=data.get('subscription')
                if not subscription_valid(sub):raise ApiError('Prohlížeč neposkytl platné push připojení.')
                save_profile(c,profile(c));clean={'endpoint':sub['endpoint'],'keys':{k:sub['keys'][k] for k in ('auth','p256dh')}}
                execute(c,'INSERT INTO notification_subscriptions (id,user_id,scope,endpoint,subscription_json,created_at) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(user_id,scope,endpoint) DO UPDATE SET subscription_json=excluded.subscription_json',(uid(),g.user['id'],scope(),sub['endpoint'],json.dumps(clean),time.time()))
        return jsonify(ok=True)

    @app.get('/api/notifications/device')
    @authenticated()
    def notification_device():
        with db(central=True) as c:
            row=one(c,'SELECT id FROM notification_subscriptions WHERE user_id=%s AND scope=%s AND endpoint=%s',(g.user['id'],scope(),request.args.get('endpoint','')))
        return jsonify(subscribed=bool(row))

    @app.post('/api/notifications/test')
    @authenticated()
    def test_push():
        rate_limit(['push-test:'+g.user['id']],5,60)
        endpoint=body().get('endpoint')
        with db(central=True) as c:
            sub=one(c,'SELECT subscription_json FROM notification_subscriptions WHERE user_id=%s AND scope=%s AND endpoint=%s',(g.user['id'],scope(),endpoint))
            if not sub:raise ApiError('Nejdříve zapněte oznámení na tomto zařízení.')
            key=keypair(c)
        try:deliver(json.loads(sub['subscription_json']),{'title':'NOIRA · oznámení fungují','body':'Toto zařízení je připravené na vaše skladová upozornění.','url':request.script_root+'/#settings','tag':'noira-test'},key['private_key'])
        except Exception as error:
            if getattr(getattr(error,'response',None),'status_code',None) in (404,410):
                with db(central=True) as c:execute(c,'DELETE FROM notification_subscriptions WHERE user_id=%s AND scope=%s AND endpoint=%s',(g.user['id'],scope(),endpoint))
            raise ApiError('Oznámení se nepodařilo doručit. Zkuste vypnout a znovu zapnout toto zařízení.',502)
        return jsonify(ok=True)

    @app.get('/notifications.js')
    def notification_script():return send_from_directory(WEB,'notifications.js')

    @app.after_request
    def queue_delivery(response):
        global RUNNING
        venue=getattr(g,'venue',None)
        if venue and not TEST_DB and response.status_code<400:
            now=time.time()
            with LOCK:
                if not RUNNING and (getattr(g,'notification_changes',False) or now-LAST_RUN.get(venue['id'],0)>30):
                    RUNNING=True;LAST_RUN[venue['id']]=now;POOL.submit(dispatch,app,dict(venue))
        return response
