"""Owner-controlled opening hours and explainable stock attention cases."""
from server.coowners import owner_scope
import hashlib
import json
import math
import re
import time
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from urllib.parse import quote
from flask import g,request,jsonify,send_from_directory
from server.analytics import observations,timestamp

DEFAULTS={'lossPercent':20,'movementLimits':{'ks':50,'l':10,'kg':10,'balení':5},'repeatedCount':3,'transferMinutes':15,'outsideHours':True}
TABLES=[
 """CREATE TABLE IF NOT EXISTS stock_attention_cases (venue_id TEXT NOT NULL REFERENCES allin_venues(id) ON DELETE CASCADE,alert_key TEXT NOT NULL,resolved INTEGER NOT NULL,note TEXT NOT NULL,actor_name TEXT NOT NULL,updated_at DOUBLE PRECISION NOT NULL,snapshot_json TEXT NOT NULL,PRIMARY KEY(venue_id,alert_key))""",
 """CREATE TABLE IF NOT EXISTS stock_attention_events (id TEXT PRIMARY KEY,venue_id TEXT NOT NULL REFERENCES allin_venues(id) ON DELETE CASCADE,alert_key TEXT NOT NULL,resolved INTEGER NOT NULL,note TEXT NOT NULL,actor_id TEXT NOT NULL,actor_name TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL)""",
 'CREATE INDEX IF NOT EXISTS stock_attention_history ON stock_attention_events(venue_id,alert_key,created_at)']

def validate_hours(value):
    if not isinstance(value,dict):raise ValueError('Neplatná otevírací doba.')
    if not value:return {}
    if set(value)-{'timezone','days'}:raise ValueError('Neplatné údaje otevírací doby.')
    zone=value.get('timezone','Europe/Prague')
    if not isinstance(zone,str) or len(zone)>100:raise ValueError('Neplatné časové pásmo.')
    try:ZoneInfo(zone)
    except (ZoneInfoNotFoundError,ValueError):raise ValueError('Neplatné časové pásmo.')
    days=value.get('days')
    if not isinstance(days,dict) or set(days)!={str(i) for i in range(7)}:raise ValueError('Vyplňte všech sedm dnů v týdnu.')
    clean={}
    for day,row in days.items():
        if not isinstance(row,dict) or type(row.get('closed')) is not bool:raise ValueError('Označte zavřené dny.')
        if row['closed']:clean[day]={'closed':True};continue
        if any(not isinstance(row.get(k),str) or not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]',row[k]) for k in ('open','close')):raise ValueError('Vyplňte platný čas otevření a zavření.')
        clean[day]={'closed':False,'open':row['open'],'close':row['close']}
    return {'timezone':zone,'days':clean}

def validate_limits(value):
    if not isinstance(value,dict) or set(value)-set(DEFAULTS):raise ValueError('Neplatné limity upozornění.')
    result={**DEFAULTS,**value,'movementLimits':{**DEFAULTS['movementLimits'],**value.get('movementLimits',{})}} if isinstance(value.get('movementLimits',{}),dict) else None
    if result is None or set(result['movementLimits'])!=set(DEFAULTS['movementLimits']):raise ValueError('Neplatné limity množství.')
    def number(v,lo,hi):return type(v) in (int,float) and math.isfinite(v) and lo<=v<=hi
    if not number(result['lossPercent'],1,1000) or any(not number(v,.001,1e12) for v in result['movementLimits'].values()):raise ValueError('Zadejte kladné limity upozornění.')
    if type(result['repeatedCount']) is not int or not 2<=result['repeatedCount']<=50 or not number(result['transferMinutes'],1,1440) or type(result['outsideHours']) is not bool:raise ValueError('Neplatné nastavení opakování nebo času.')
    return result

def within_hours(stamp,hours):
    if not hours:return None
    local=datetime.fromtimestamp(stamp,ZoneInfo(hours['timezone']));minute=local.strftime('%H:%M')
    row=hours['days'][str(local.weekday())];previous=hours['days'][str((local.weekday()-1)%7)]
    if not row['closed']:
        start,end=row['open'],row['close']
        if start==end or (start<end and start<=minute<end) or (start>end and minute>=start):return True
    return not previous['closed'] and previous['open']>previous['close'] and minute<previous['close']

def detect(document,hours=None,limits=None,now=None,corrections=()):
    limits=validate_limits(limits or {});now=time.time() if now is None else now;cutoff=now-30*86400
    products={p['id']:p for p in document.get('products',[])};stores={s['id']:s for s in document.get('stores',[])}
    result=[]
    def add(kind,row,explanation,evidence=None):
        sid=row.get('storeId',row.get('store',''));pid=row.get('productId',row.get('product',''))
        product=products.get(pid,{});at=row.get('recordedAt') or (timestamp(row['at']) if row.get('at') else row.get('created_at',0))
        if not cutoff<=at<=now+60:return
        evidence=evidence or [row['id']]
        key=hashlib.sha256(json.dumps([kind,evidence,row.get('qty'),row.get('expected')],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        result.append({'id':key,'type':kind,'explanation':explanation,'evidenceIds':evidence,'at':at,'occurredAt':row.get('at'),
          'actorName':row.get('actorName') or row.get('actor_name') or 'Autor u staršího záznamu není evidován',
          'storeId':sid,'storeName':stores.get(sid,{}).get('name',row.get('storeName','')),'productId':pid,'productName':product.get('name',row.get('productName','')),
          'quantity':row.get('qty'),'unit':row.get('unit') or product.get('unit',''),'sourceId':row.get('inventoryId') or row['id'],
          'sourceRoute':('#movements/'+quote(row['id'],safe='')) if row.get('reason') else ('#audit/'+quote(row['inventoryId'],safe='')) if row.get('inventoryId') else ('#product/'+quote(pid,safe='')+'/'+quote(sid,safe='')) if pid and sid else '#changes'})
    movements=sorted(document.get('moves',[]),key=lambda r:r.get('recordedAt') or timestamp(r['at']))
    recent=[r for r in movements if cutoff<=(r.get('recordedAt') or timestamp(r['at']))<=now+60]
    waste=defaultdict(list)
    for row in recent:
        product=products.get(row['product'],{});unit=product.get('unit','ks');limit=limits['movementLimits'].get(unit,50)
        if abs(row['qty'])>=limit:add('large_writeoff' if row['reason']=='Odpis' else 'large_movement',row,f"{row['reason']}: {abs(row['qty']):g} {unit}; nastavený limit je {limit:g} {unit}.")
        if limits['outsideHours'] and within_hours(row.get('recordedAt') or timestamp(row['at']),hours) is False:add('outside_hours',row,'Pohyb byl zaznamenán mimo nastavenou otevírací dobu provozu.')
        if row['reason']=='Odpis':waste[(row['store'],row['product'])].append(row)
    for rows in waste.values():
        last=rows[-1];at=last.get('recordedAt') or timestamp(last['at']);same=[r for r in rows if (r.get('recordedAt') or timestamp(r['at']))>=at-7*86400]
        if len(same)>=limits['repeatedCount']:add('repeated_writeoff',last,f"{len(same)} odpisů stejného produktu ve skladu během sedmi dnů.",[r['id'] for r in same])
    losses=defaultdict(list)
    source_rows={r['id']:r for r in document.get('counts',[])+document.get('barInventories',[])}
    for row in observations(document):
        source=source_rows.get(row['id'],source_rows.get(row['id'].split(':')[0],{}))
        if source.get('recordedAt'):row['recordedAt']=source['recordedAt']
        at=row.get('recordedAt') or timestamp(row['at'])
        if cutoff<=at<=now+60 and limits['outsideHours'] and within_hours(at,hours) is False:add('inventory_outside_hours',row,'Inventura byla zaznamenána mimo nastavenou otevírací dobu provozu.')
        if cutoff<=at<=now+60 and row['difference'] is not None and row['difference']<0:losses[(row['storeId'],row['productId'],row['unit'])].append(row)
        if row['difference'] is not None and row['expected'] is not None:
            difference=abs(row['difference']);limit=limits['movementLimits'].get(row['unit'],50)
            rate=difference/abs(row['expected'])*100 if row['expected'] else None
            if difference>1e-8 and ((rate is not None and rate>=limits['lossPercent']) or difference>=limit):
                add('inventory_difference',row,f"{'Manko' if row['difference']<0 else 'Přebytek'} {difference:g} {row['unit']}"+(f" ({rate:.1f} %; limit {limits['lossPercent']:g} %)." if rate is not None else '; výchozí stav byl nulový.'))
    for rows in losses.values():
        if len(rows)>=limits['repeatedCount']:add('repeated_shortage',rows[-1],f"Manko u stejného produktu ve skladu se opakuje v {len(rows)} inventurách za posledních 30 dní.",[r['id'] for r in rows])
    transfers=defaultdict(list)
    for row in recent:
        if row['reason']=='Přesun' and row.get('transferId'):transfers[row['transferId']].append(row)
    pairs=[]
    for key,rows in transfers.items():
        outgoing=next((r for r in rows if r['qty']<0),None);incoming=next((r for r in rows if r['qty']>0),None)
        if outgoing and incoming:pairs.append((outgoing.get('recordedAt') or timestamp(outgoing['at']),outgoing,incoming))
    previous={}
    for at,outgoing,incoming in sorted(pairs,key=lambda p:p[0]):
        reverse=previous.get((outgoing['product'],incoming['store'],outgoing['store']))
        if reverse and at-reverse[0]<=limits['transferMinutes']*60 and abs(outgoing['qty']-reverse[1]['qty'])<1e-8:
            add('round_trip_transfer',outgoing,'Stejné množství bylo krátce po přesunu vráceno mezi stejnými sklady.',[reverse[1]['id'],outgoing['id']])
        previous[(outgoing['product'],outgoing['store'],incoming['store'])]=(at,outgoing)
    edits=[r for r in corrections if r.get('created_at',0)>=cutoff]
    if len(edits)>=limits['repeatedCount']:
        last=edits[-1];add('repeated_correction',last,f"{len(edits)} oprav schválených inventur za posledních 30 dnů.",[r['id'] for r in edits])
    return sorted(result,key=lambda r:(r['at'],r['id']),reverse=True)

def register(app):
    from server.app import authenticated,db,execute,one,allrows,body,ApiError,uid,TEST_DB,SUPABASE_DATABASE_URL,audit,WEB
    from server.allin import venue_context
    with db(central=True) as c:
        columns={r['name'] for r in allrows(c,'PRAGMA table_info(allin_venues)')} if TEST_DB else {r['column_name'] for r in allrows(c,"SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='allin_venues'")}
        for field in ('opening_hours_json','attention_limits_json'):
            if field not in columns:execute(c,"ALTER TABLE allin_venues ADD COLUMN "+field+" TEXT NOT NULL DEFAULT '{}'")
        for sql in TABLES:execute(c,sql)
        if not TEST_DB:
            for table in ('stock_attention_cases','stock_attention_events'):
                execute(c,'ALTER TABLE '+table+' ENABLE ROW LEVEL SECURITY');execute(c,'REVOKE ALL ON '+table+' FROM PUBLIC')
                if SUPABASE_DATABASE_URL:execute(c,'REVOKE ALL ON '+table+' FROM anon,authenticated')
    def owned(c,id):
        venue=one(c,'SELECT * FROM allin_venues WHERE id=%s AND owner_id=%s',(id,owner_scope()))
        if not venue:raise ApiError('Provoz neexistuje nebo k němu nemáte přístup.',404)
        return venue
    def evaluate(venue):
        with venue_context(venue),db() as c:
            row=one(c,'SELECT data_json FROM stock_documents WHERE user_id=%s',(venue['owner_id'],));document=json.loads(row['data_json']) if row else {}
            edits=allrows(c,"SELECT id,actor_name,created_at FROM inventory_review_events WHERE action='corrected' AND created_at>=%s ORDER BY created_at,id",(time.time()-30*86400,))
        return detect(document,json.loads(venue['opening_hours_json']),json.loads(venue['attention_limits_json']),corrections=edits)
    @app.route('/api/owner/venues/<venue_id>/controls',methods=['GET','PUT'])
    @authenticated(admin=True)
    def settings(venue_id):
        with db(central=True) as c:
            venue=owned(c,venue_id)
            if request.method=='PUT':
                values=body()
                try:
                    hours=validate_hours(values.get('openingHours',json.loads(venue['opening_hours_json'])))
                    limits=validate_limits(values.get('limits',json.loads(venue['attention_limits_json'])))
                except (ValueError,TypeError) as error:raise ApiError(str(error))
                execute(c,'UPDATE allin_venues SET opening_hours_json=%s,attention_limits_json=%s WHERE id=%s AND owner_id=%s',(json.dumps(hours),json.dumps(limits),venue_id,owner_scope()))
                audit(c,g.user['id'],'venue_controls_changed','Nastavení provozní doby a limitů: '+venue['name'])
            else:hours=json.loads(venue['opening_hours_json']);limits=validate_limits(json.loads(venue['attention_limits_json']))
        return jsonify(openingHours=hours,limits=limits)
    @app.get('/api/owner/attention')
    @authenticated(admin=True)
    def attention():
        with db(central=True) as c:venues=allrows(c,'SELECT * FROM allin_venues WHERE owner_id=%s ORDER BY name,id',(owner_scope(),))
        rows=[]
        for venue in venues:
            if request.args.get('venue') and request.args['venue']!=venue['id']:continue
            with db(central=True) as c:
                saved={r['alert_key']:r for r in allrows(c,'SELECT * FROM stock_attention_cases WHERE venue_id=%s',(venue['id'],))}
                history=allrows(c,'SELECT * FROM stock_attention_events WHERE venue_id=%s ORDER BY created_at,id',(venue['id'],))
            for alert in evaluate(venue):
                case=saved.get(alert['id'],{});rows.append({**alert,'venueId':venue['id'],'venueName':venue['name'],'resolved':bool(case.get('resolved')),'note':case.get('note',''),'resolvedBy':case.get('actor_name',''),'resolvedAt':case.get('updated_at'),'history':[r for r in history if r['alert_key']==alert['id']]})
        return jsonify(alerts=sorted(rows,key=lambda r:r['at'],reverse=True),days=30)
    @app.post('/api/owner/venues/<venue_id>/attention/<key>')
    @authenticated(admin=True)
    def resolve(venue_id,key):
        values=body();note=values.get('note');resolved=values.get('resolved')
        if type(resolved) is not bool or not isinstance(note,str) or not 5<=len(note.strip())<=500 or any(ord(c)<32 and c not in '\n\r\t' for c in note):raise ApiError('Uveďte vysvětlení nebo důvod znovuotevření (5–500 znaků).')
        with db(central=True) as c:venue=owned(c,venue_id)
        alert=next((r for r in evaluate(venue) if r['id']==key),None)
        if not alert:raise ApiError('Upozornění již není v aktuálním třicetidenním přehledu.',404)
        name=(g.user['first_name']+' '+g.user['last_name']).strip() or g.user['username'];now=time.time()
        with db(central=True) as c:
            owned(c,venue_id)
            execute(c,'INSERT INTO stock_attention_cases (venue_id,alert_key,resolved,note,actor_name,updated_at,snapshot_json) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(venue_id,alert_key) DO UPDATE SET resolved=excluded.resolved,note=excluded.note,actor_name=excluded.actor_name,updated_at=excluded.updated_at,snapshot_json=excluded.snapshot_json',(venue_id,key,int(resolved),note.strip(),name,now,json.dumps(alert,ensure_ascii=False)))
            execute(c,'INSERT INTO stock_attention_events (id,venue_id,alert_key,resolved,note,actor_id,actor_name,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',(uid(),venue_id,key,int(resolved),note.strip(),g.user['id'],name,now))
            audit(c,g.user['id'],'stock_attention_resolved' if resolved else 'stock_attention_reopened','Prověření skladové odchylky: '+key)
        return jsonify(ok=True)
    @app.get('/controls.js')
    def script():return send_from_directory(WEB,'controls.js')
    @app.get('/controls.css')
    def style():return send_from_directory(WEB,'controls.css')
