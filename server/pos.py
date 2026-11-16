"""Owner-only daily POS summaries. CSV ingestion is live; provider APIs need partner access."""
import csv
import io
import json
import re
import time
import unicodedata
from datetime import date,datetime
from zoneinfo import ZoneInfo
from decimal import Decimal,InvalidOperation
from flask import g,request,jsonify,send_from_directory,make_response

PROVIDERS=[
 {'id':'dotykacka','name':'Dotykačka','apiStatus':'requires_partner_access','docs':'https://docs.api.dotypos.com/getting-started/'},
 {'id':'storyous','name':'Storyous','apiStatus':'requires_partner_access','docs':'https://docs.api.storyous.com/'},
 {'id':'septim','name':'Septim','apiStatus':'requires_vendor_agreement','docs':'https://www.septim.cz/sluzby-servis/vyvoj-na-miru'},
 {'id':'csv','name':'Jiná pokladna / CSV','apiStatus':'csv_only','docs':None}]
TABLES=[
'''CREATE TABLE IF NOT EXISTS pos_connections (venue_id TEXT PRIMARY KEY REFERENCES allin_venues(id) ON DELETE CASCADE,provider TEXT NOT NULL,register_label TEXT NOT NULL DEFAULT '',updated_at DOUBLE PRECISION NOT NULL)''',
'''CREATE TABLE IF NOT EXISTS pos_days (id TEXT PRIMARY KEY,venue_id TEXT NOT NULL REFERENCES allin_venues(id) ON DELETE CASCADE,business_date TEXT NOT NULL,register_id TEXT NOT NULL,currency TEXT NOT NULL,provider TEXT NOT NULL,source_ref TEXT NOT NULL,revenue_net BIGINT NOT NULL,cogs BIGINT,operating_costs BIGINT,revision INTEGER NOT NULL DEFAULT 1,created_at DOUBLE PRECISION NOT NULL,updated_at DOUBLE PRECISION NOT NULL,UNIQUE(venue_id,business_date,register_id))''',
'CREATE INDEX IF NOT EXISTS pos_days_date ON pos_days(venue_id,business_date,id)',
'''CREATE TABLE IF NOT EXISTS pos_revisions (id TEXT PRIMARY KEY,day_id TEXT NOT NULL REFERENCES pos_days(id) ON DELETE CASCADE,revision INTEGER NOT NULL,data_json TEXT NOT NULL,actor_id TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL,UNIQUE(day_id,revision))''',
'''CREATE TABLE IF NOT EXISTS pos_imports (id TEXT PRIMARY KEY,venue_id TEXT NOT NULL REFERENCES allin_venues(id) ON DELETE CASCADE,provider TEXT NOT NULL,inserted INTEGER NOT NULL,updated INTEGER NOT NULL,unchanged INTEGER NOT NULL,actor_id TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL)''']
FIELDS=('business_date','register_id','currency','provider','source_ref','revenue_net','cogs','operating_costs')


def normalize_header(value):return ''.join(c for c in unicodedata.normalize('NFD',value.strip().lower()) if not unicodedata.combining(c)).replace(' ','_')


def parse_money(value,optional=False):
    value=str(value or '').strip().replace('\xa0','').replace(' ','')
    if not value and optional:return None
    if not value or not re.fullmatch(r'-?\d+(?:[.,]\d{1,2})?',value):raise ValueError('Částka musí být číslo s nejvýše dvěma desetinnými místy.')
    try:amount=Decimal(value.replace(',','.'))
    except InvalidOperation:raise ValueError('Neplatná částka.')
    if abs(amount)>Decimal('1000000000'):raise ValueError('Částka je příliš vysoká.')
    if optional and amount<0:raise ValueError('Náklady nemohou být záporné.')
    return int(amount*100)


def parse_csv(text,provider,default_register='hlavni'):
    if not isinstance(text,str) or not text.strip() or len(text)>2_000_000:raise ValueError('Vyberte neprázdné CSV nejvýše 2 MB.')
    text=text.lstrip('\ufeff')
    try:dialect=csv.Sniffer().sniff(text[:8192],delimiters=';,\t')
    except csv.Error:dialect=None
    reader=csv.DictReader(io.StringIO(text),dialect=dialect) if dialect else csv.DictReader(io.StringIO(text),delimiter=';')
    names=[normalize_header(h) for h in reader.fieldnames or []]
    if len(names)!=len(set(names)) or not {'datum','trzby_bez_dph'}.issubset(names):raise ValueError('CSV musí mít unikátní sloupce datum a trzby_bez_dph. Použijte vzor NOIRA.')
    reader.fieldnames=names;rows=[];seen=set()
    for line,raw in enumerate(reader,2):
        if len(rows)>=5000:raise ValueError('Jeden import může obsahovat nejvýše 5 000 řádků.')
        if None in raw:raise ValueError(f'Řádek {line}: jiný počet sloupců než v záhlaví.')
        if not any(v and v.strip() for v in raw.values()):continue
        try:
            day=str(raw.get('datum') or '').strip()
            try:day=date.fromisoformat(day).isoformat()
            except ValueError:day=datetime.strptime(day,'%d.%m.%Y').date().isoformat()
            if day>datetime.now(ZoneInfo('Europe/Prague')).date().isoformat():raise ValueError('Datum nesmí být v budoucnosti.')
            register=str(raw.get('kasa') or default_register).strip();currency=str(raw.get('mena') or 'CZK').strip().upper();ref=str(raw.get('uzaverka_id') or '').strip()
            if not register or len(register)>100 or any(ord(c)<32 for c in register) or len(ref)>150:raise ValueError('Neplatné označení pokladny nebo uzávěrky.')
            if not re.fullmatch('[A-Z]{3}',currency):raise ValueError('Měna musí mít třípísmenný kód, např. CZK nebo EUR.')
            key=(day,register)
            if key in seen:raise ValueError('Každá pokladna smí mít pro jeden den pouze jeden denní souhrn.')
            seen.add(key)
            rows.append({'business_date':day,'register_id':register,'currency':currency,'provider':provider,'source_ref':ref,
                         'revenue_net':parse_money(raw.get('trzby_bez_dph')),'cogs':parse_money(raw.get('naklady_zbozi'),True),
                         'operating_costs':parse_money(raw.get('provozni_naklady'),True)})
        except (ValueError,TypeError) as error:raise ValueError(f'Řádek {line}: {error}')
    if not rows:raise ValueError('CSV neobsahuje žádné denní souhrny.')
    return rows


def public_day(row):
    result=dict(row)
    complete=result['cogs'] is not None and result['operating_costs'] is not None
    result['profit']=result['revenue_net']-result['cogs']-result['operating_costs'] if complete else None
    result['profitStatus']='estimate' if complete else 'missing_costs'
    return result


def register(app):
    from server.app import authenticated,db,execute,one,allrows,ApiError,body,uid,TEST_DB,SUPABASE_DATABASE_URL,WEB,audit
    with db(central=True) as c:
        for sql in TABLES:execute(c,sql)
        execute(c,'CREATE INDEX IF NOT EXISTS pos_imports_latest ON pos_imports(venue_id,created_at)')
        if not TEST_DB:
            for name in ('pos_connections','pos_days','pos_revisions','pos_imports'):
                execute(c,'ALTER TABLE '+name+' ENABLE ROW LEVEL SECURITY');execute(c,'REVOKE ALL ON '+name+' FROM PUBLIC')
                if SUPABASE_DATABASE_URL:execute(c,'REVOKE ALL ON '+name+' FROM anon,authenticated')

    def own(c,venue_id):
        row=one(c,'SELECT * FROM allin_venues WHERE id=%s AND owner_id=%s',(venue_id,g.user['id']))
        if not row:raise ApiError('Provoz neexistuje nebo k němu nemáte přístup.',404)
        return row
    def filters():
        conditions=['v.owner_id=%s'];args=[g.user['id']]
        venue=request.args.get('venue','')
        if venue:
            with db(central=True) as c:own(c,venue)
            conditions.append('d.venue_id=%s');args.append(venue)
        for key,operator in [('from','>='),('to','<=')]:
            value=request.args.get(key,'')
            if value:
                try:value=date.fromisoformat(value).isoformat()
                except ValueError:raise ApiError('Neplatné datum filtru.')
                conditions.append('d.business_date'+operator+'%s');args.append(value)
        if request.args.get('from','') and request.args.get('to','') and request.args['from']>request.args['to']:raise ApiError('Začátek období musí předcházet konci.')
        for param,column in [('currency','currency'),('register','register_id')]:
            value=request.args.get(param,'')
            if value:conditions.append('d.'+column+'=%s');args.append(value)
        status=request.args.get('status','')
        if status=='missing_costs':conditions.append('(d.cogs IS NULL OR d.operating_costs IS NULL)')
        elif status=='estimate':conditions.append('(d.cogs IS NOT NULL AND d.operating_costs IS NOT NULL)')
        elif status:raise ApiError('Neplatný stav výsledku.')
        return ' WHERE '+' AND '.join(conditions),tuple(args)

    @app.get('/api/owner/pos')
    @authenticated(admin=True)
    def pos_status():
        with db(central=True) as c:
            venues=allrows(c,'SELECT v.*,p.provider,p.register_label,p.updated_at AS configured_at FROM allin_venues v LEFT JOIN pos_connections p ON p.venue_id=v.id WHERE v.owner_id=%s ORDER BY v.created_at,v.id',(g.user['id'],))
            for v in venues:
                v['latestResults']=allrows(c,"SELECT business_date,currency,SUM(revenue_net) AS revenue_net,SUM(CASE WHEN cogs IS NULL OR operating_costs IS NULL THEN 1 ELSE 0 END) AS missing,SUM(CASE WHEN cogs IS NOT NULL AND operating_costs IS NOT NULL THEN revenue_net-cogs-operating_costs ELSE 0 END) AS profit,COUNT(*) AS registers FROM pos_days WHERE venue_id=%s AND business_date=(SELECT MAX(business_date) FROM pos_days WHERE venue_id=%s) GROUP BY business_date,currency ORDER BY currency",(v['id'],v['id']))
                for day in v['latestResults']:
                    for key in ('revenue_net','missing','profit','registers'):day[key]=int(day[key])
                    if day['missing']:day['profit']=None
                v['latest']=v['latestResults'][0] if v['latestResults'] else None
                v['lastImport']=one(c,'SELECT * FROM pos_imports WHERE venue_id=%s ORDER BY created_at DESC LIMIT 1',(v['id'],))
                v['mode']='csv';v['automaticSync']=False
        return jsonify(providers=PROVIDERS,venues=venues)

    @app.put('/api/owner/pos/<venue_id>')
    @authenticated(admin=True)
    def pos_configure(venue_id):
        data=body();provider=data.get('provider');label=data.get('registerLabel','')
        if not isinstance(provider,str) or provider not in {p['id'] for p in PROVIDERS} or not isinstance(label,str) or len(label)>100 or any(ord(c)<32 for c in label):raise ApiError('Neplatná pokladna.')
        with db(central=True) as c:
            own(c,venue_id);execute(c,'INSERT INTO pos_connections (venue_id,provider,register_label,updated_at) VALUES (%s,%s,%s,%s) ON CONFLICT(venue_id) DO UPDATE SET provider=excluded.provider,register_label=excluded.register_label,updated_at=excluded.updated_at',(venue_id,provider,label.strip(),time.time()))
            audit(c,g.user['id'],'pos_configured','Nastavení importu denních uzávěrek')
        return jsonify(ok=True,mode='csv',automaticSync=False)

    @app.post('/api/owner/pos/<venue_id>/import')
    @authenticated(admin=True)
    def pos_import(venue_id):
        data=body()
        with db(central=True) as c:
            own(c,venue_id)
            connection=one(c,'SELECT * FROM pos_connections WHERE venue_id=%s',(venue_id,))
            provider=connection['provider'] if connection else 'csv'
        try:rows=parse_csv(data.get('csv'),provider,connection['register_label'] if connection and connection['register_label'] else 'hlavni')
        except (ValueError,csv.Error) as error:raise ApiError(str(error))
        inserted=updated=unchanged=0
        with db(central=True) as c:
            own(c,venue_id)
            # Serialize imports for the same venue in PostgreSQL. SQLite's db() already locks writes.
            execute(c,'UPDATE allin_venues SET name=name WHERE id=%s',(venue_id,))
            for row in rows:
                old=one(c,'SELECT * FROM pos_days WHERE venue_id=%s AND business_date=%s AND register_id=%s',(venue_id,row['business_date'],row['register_id']))
                if old and old['currency']!=row['currency']:raise ApiError('Měnu existujícího denního souhrnu nelze přepsat. Zkontrolujte soubor.',409)
                if old and all(old[k]==row[k] for k in FIELDS):unchanged+=1;continue
                now=time.time();id=old['id'] if old else uid();revision=old['revision']+1 if old else 1
                if old:
                    count=execute(c,'UPDATE pos_days SET provider=%s,source_ref=%s,revenue_net=%s,cogs=%s,operating_costs=%s,revision=%s,updated_at=%s WHERE id=%s AND revision=%s',(row['provider'],row['source_ref'],row['revenue_net'],row['cogs'],row['operating_costs'],revision,now,id,old['revision'])).rowcount
                    if count!=1:raise ApiError('Uzávěrka se mezitím změnila. Zopakujte import.',409)
                    updated+=1
                else:
                    execute(c,'INSERT INTO pos_days (id,venue_id,business_date,register_id,currency,provider,source_ref,revenue_net,cogs,operating_costs,revision,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(id,venue_id,*[row[k] for k in FIELDS[:3]],row['provider'],row['source_ref'],row['revenue_net'],row['cogs'],row['operating_costs'],revision,now,now));inserted+=1
                snapshot={**row,'id':id,'venue_id':venue_id,'revision':revision}
                execute(c,'INSERT INTO pos_revisions (id,day_id,revision,data_json,actor_id,created_at) VALUES (%s,%s,%s,%s,%s,%s)',(uid(),id,revision,json.dumps(snapshot,ensure_ascii=False),g.user['id'],now))
            execute(c,'INSERT INTO pos_imports (id,venue_id,provider,inserted,updated,unchanged,actor_id,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',(uid(),venue_id,provider,inserted,updated,unchanged,g.user['id'],time.time()))
            audit(c,g.user['id'],'pos_imported',f'Import denních souhrnů: {inserted} nových, {updated} oprav')
        return jsonify(inserted=inserted,updated=updated,unchanged=unchanged)

    @app.get('/api/owner/pos/days')
    @authenticated(admin=True)
    def pos_days():
        where,args=filters();limit=50;offset=max(0,request.args.get('offset',0,type=int))
        base=' FROM pos_days d JOIN allin_venues v ON v.id=d.venue_id'
        with db(central=True) as c:
            count=one(c,'SELECT COUNT(*) AS n'+base+where,args)['n']
            rows=allrows(c,'SELECT d.*,v.name AS venue_name'+base+where+' ORDER BY d.business_date DESC,v.name,d.register_id,d.id LIMIT %s OFFSET %s',args+(limit,offset))
            aggregates=allrows(c,'SELECT d.business_date,d.currency,SUM(d.revenue_net) AS revenue_net,SUM(CASE WHEN d.cogs IS NOT NULL AND d.operating_costs IS NOT NULL THEN d.revenue_net-d.cogs-d.operating_costs ELSE 0 END) AS known_profit,SUM(CASE WHEN d.cogs IS NULL OR d.operating_costs IS NULL THEN 1 ELSE 0 END) AS missing,COUNT(*) AS registers'+base+where+' GROUP BY d.business_date,d.currency ORDER BY d.business_date DESC',args)
        totals={}
        for row in aggregates:
            for key in ('revenue_net','known_profit','missing','registers'):row[key]=int(row[key])
            total=totals.setdefault(row['currency'],{'currency':row['currency'],'revenue_net':0,'known_profit':0,'missing':0,'registers':0})
            for key in ('revenue_net','known_profit','missing','registers'):total[key]+=row[key]
        return jsonify(days=[public_day(r) for r in rows],daily=aggregates,total=count,offset=offset,limit=limit,totals=list(totals.values()))

    @app.get('/api/owner/pos/days/<day_id>')
    @authenticated(admin=True)
    def pos_day_detail(day_id):
        with db(central=True) as c:
            day=one(c,'SELECT d.*,v.name AS venue_name FROM pos_days d JOIN allin_venues v ON v.id=d.venue_id WHERE d.id=%s AND v.owner_id=%s',(day_id,g.user['id']))
            if not day:raise ApiError('Denní souhrn neexistuje.',404)
            revisions=allrows(c,'SELECT revision,data_json,created_at FROM pos_revisions WHERE day_id=%s ORDER BY revision DESC',(day_id,))
        return jsonify(day=public_day(day),revisions=[{'revision':r['revision'],'data':json.loads(r['data_json']),'created_at':r['created_at']} for r in revisions])

    @app.get('/api/owner/pos/export')
    @authenticated(admin=True)
    def pos_export():
        where,args=filters()
        with db(central=True) as c:rows=allrows(c,'SELECT d.*,v.name AS venue_name FROM pos_days d JOIN allin_venues v ON v.id=d.venue_id'+where+' ORDER BY d.business_date DESC,d.id',args)
        out=io.StringIO();writer=csv.writer(out,delimiter=';');writer.writerow(['provoz','datum','kasa','mena','trzby_bez_dph','naklady_zbozi','provozni_naklady','odhad_zisku','revize'])
        def cell(value):
            value=str(value)
            return "'"+value if value.startswith(('=','+','-','@','\t','\r')) else value
        def money(value):return '' if value is None else format(Decimal(value)/100,'.2f')
        for row in rows:
            day=public_day(row);writer.writerow([cell(day['venue_name']),day['business_date'],cell(day['register_id']),day['currency'],money(day['revenue_net']),money(day['cogs']),money(day['operating_costs']),money(day['profit']),day['revision']])
        result=make_response('\ufeff'+out.getvalue());result.headers['Content-Type']='text/csv; charset=utf-8';result.headers['Content-Disposition']='attachment; filename=noira-denni-prehled.csv';result.headers['Cache-Control']='no-store';return result

    @app.get('/api/owner/pos/template')
    @authenticated(admin=True)
    def pos_template():
        result=make_response('\ufeffdatum;kasa;mena;trzby_bez_dph;naklady_zbozi;provozni_naklady;uzaverka_id\n2026-01-01;hlavni;CZK;10000,00;3000,00;2000,00;UZ-001\n');result.headers['Content-Type']='text/csv; charset=utf-8';result.headers['Content-Disposition']='attachment; filename=noira-vzor-uzaverek.csv';result.headers['Cache-Control']='no-store';return result

    @app.get('/pos.js')
    def pos_script():return send_from_directory(WEB,'pos.js')
