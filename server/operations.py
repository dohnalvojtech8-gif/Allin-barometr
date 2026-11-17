"""Owner operational analytics with explicit POS coverage and versioned recipes."""
import csv
import io
import json
import math
import time
from collections import defaultdict
from datetime import date,datetime,time as daytime,timedelta,timezone
from flask import g,request,jsonify,make_response
from server.analytics import PRAGUE,analyze,margins,timestamp,business_date,canonical

TABLES=[
"""CREATE TABLE IF NOT EXISTS pos_item_sales (venue_id TEXT NOT NULL REFERENCES allin_venues(id) ON DELETE CASCADE,register_id TEXT NOT NULL,source_id TEXT NOT NULL,sold_at TEXT NOT NULL,business_date TEXT NOT NULL,sales_code TEXT NOT NULL,quantity DOUBLE PRECISION NOT NULL,import_id TEXT NOT NULL,PRIMARY KEY(venue_id,register_id,source_id))""",
'CREATE INDEX IF NOT EXISTS pos_item_sales_period ON pos_item_sales(venue_id,business_date,sold_at)',
"""CREATE TABLE IF NOT EXISTS pos_item_coverage (venue_id TEXT NOT NULL REFERENCES allin_venues(id) ON DELETE CASCADE,register_id TEXT NOT NULL,business_date TEXT NOT NULL,import_id TEXT NOT NULL,PRIMARY KEY(venue_id,register_id,business_date))""",
"""CREATE TABLE IF NOT EXISTS pos_item_imports (id TEXT PRIMARY KEY,venue_id TEXT NOT NULL REFERENCES allin_venues(id) ON DELETE CASCADE,register_id TEXT NOT NULL,from_date TEXT NOT NULL,to_date TEXT NOT NULL,row_count INTEGER NOT NULL,actor_id TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL,snapshot_json TEXT NOT NULL)""",
"""CREATE TABLE IF NOT EXISTS pos_recipes (id TEXT PRIMARY KEY,venue_id TEXT NOT NULL REFERENCES allin_venues(id) ON DELETE CASCADE,sales_code TEXT NOT NULL,effective_at TEXT NOT NULL,ingredients_json TEXT NOT NULL,actor_id TEXT NOT NULL,reason TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL)""",
'CREATE INDEX IF NOT EXISTS pos_recipe_effective ON pos_recipes(venue_id,sales_code,effective_at,created_at)']

def day_range(start,end):
    cursor=date.fromisoformat(start);last=date.fromisoformat(end)
    while cursor<=last:
        yield cursor.isoformat();cursor+=timedelta(days=1)

def parse_sales(text,first,last):
    if not isinstance(text,str) or len(text)>2_000_000:raise ValueError('Vyberte CSV nejvýše 2 MB.')
    text=text.lstrip('\ufeff')
    try:dialect=csv.Sniffer().sniff(text[:8192],delimiters=';,\t')
    except csv.Error:dialect=None
    reader=csv.DictReader(io.StringIO(text),dialect=dialect) if dialect else csv.DictReader(io.StringIO(text),delimiter=';')
    if reader.fieldnames!=['prodej_id','datum_cas','produkt_pokladny','pocet']:raise ValueError('Použijte sloupce prodej_id;datum_cas;produkt_pokladny;pocet.')
    rows=[];seen=set()
    for number,row in enumerate(reader,2):
        if not any(v for v in row.values()):continue
        if len(rows)>=5000:raise ValueError('Jeden import smí mít nejvýše 5 000 položek.')
        if None in row:raise ValueError(f'Řádek {number}: neplatný počet sloupců.')
        id=row.get('prodej_id','').strip();code=row.get('produkt_pokladny','').strip()
        if not id or len(id)>150 or not code or len(code)>150 or any(ord(c)<32 for c in id+code) or id in seen:raise ValueError(f'Řádek {number}: neplatné nebo opakované ID či kód produktu.')
        try:
            at=datetime.fromisoformat(row['datum_cas'].strip().replace('Z','+00:00'))
            qty=float(row['pocet'].strip().replace(',','.'))
        except (ValueError,TypeError,KeyError):raise ValueError(f'Řádek {number}: neplatný čas nebo množství.')
        if at.tzinfo is None or at.timestamp()>time.time()+60 or not math.isfinite(qty) or abs(qty)>1e9:raise ValueError(f'Řádek {number}: čas musí mít časové pásmo a množství musí být konečné.')
        day=at.astimezone(PRAGUE).date().isoformat()
        if not first<=day<=last:raise ValueError(f'Řádek {number}: prodej leží mimo deklarované období.')
        seen.add(id);rows.append({'source_id':id,'sold_at':at.astimezone(timezone.utc).isoformat(),'business_date':day,'sales_code':code,'quantity':qty})
    return rows

def reconcile(observations,sales,recipes,coverage,pos_days,products):
    catalog={p['id']:p for p in products};definitions=defaultdict(list)
    for recipe in recipes:definitions[recipe['sales_code']].append(recipe)
    for values in definitions.values():values.sort(key=lambda r:(timestamp(r['effective_at']),r['created_at'],r['id']))
    covered={(r['business_date'],r['register_id']) for r in coverage}
    registers=defaultdict(set)
    for row in pos_days:registers[row['business_date']].add(row['register_id'])
    results=[]
    for observation in observations:
        row={k:observation[k] for k in ('id','productId','productName','storeId','storeName','unit','date','startAt','at','consumption')}
        row.update(theoreticalConsumption=None,excessConsumption=None,status='missing_baseline',missingSalesCodes=[])
        if observation['startAt'] is None or observation['consumption'] is None:results.append(row);continue
        start=timestamp(observation['startAt']);end=timestamp(observation['at'])
        days=list(day_range(business_date(observation['startAt']),business_date(observation['at'])))
        complete=all(registers[day] and all((day,register) in covered for register in registers[day]) for day in days)
        total=0;missing=set();invalid=False
        for sale in sales:
            moment=timestamp(sale['sold_at'])
            if not start<moment<=end:continue
            choices=[r for r in definitions[sale['sales_code']] if timestamp(r['effective_at'])<=moment]
            if not choices:missing.add(sale['sales_code']);continue
            recipe=choices[-1]
            for ingredient in json.loads(recipe['ingredients_json']):
                product=catalog.get(ingredient['productId'])
                if not product or ingredient['storeId']!=product.get('store',ingredient['storeId']):invalid=True;continue
                unit,qty=canonical(ingredient['unit'],ingredient['quantity'])
                if unit!=product['unit']:invalid=True;continue
                if ingredient['storeId']==observation['storeId'] and ingredient['productId']==observation['productId']:
                    total+=qty*sale['quantity']
        row['missingSalesCodes']=sorted(missing);row['theoreticalConsumption']=total
        row['status']='incomplete_sales' if not complete else 'missing_recipe' if missing else 'invalid_recipe' if invalid else 'complete'
        if row['status']=='complete':
            row['excessConsumption']=observation['consumption']-total
            tolerance=max(1e-6,.05*max(abs(total),abs(observation['consumption'])))
            row['alert']=row['excessConsumption']>tolerance
            row['tolerance']=tolerance
        results.append(row)
    return results

def register(app):
    from server.app import authenticated,db,one,allrows,execute,body,ApiError,uid,TEST_DB,SUPABASE_DATABASE_URL,audit,scoped_stock
    from server.allin import venue_context
    from server.work import store_scope
    from server.permissions import has_permission
    with db(central=True) as c:
        for sql in TABLES:execute(c,sql)
        if not TEST_DB:
            for table in ('pos_item_sales','pos_item_coverage','pos_item_imports','pos_recipes'):
                execute(c,'ALTER TABLE '+table+' ENABLE ROW LEVEL SECURITY');execute(c,'REVOKE ALL ON '+table+' FROM PUBLIC')
                if SUPABASE_DATABASE_URL:execute(c,'REVOKE ALL ON '+table+' FROM anon,authenticated')
    def owned(c,id):
        venue=one(c,'SELECT * FROM allin_venues WHERE id=%s AND owner_id=%s',(id,g.user['id']))
        if not venue:raise ApiError('Provoz neexistuje nebo k němu nemáte přístup.',404)
        return venue
    def period(values):
        today=datetime.now(PRAGUE).date();first=values.get('from') or (today-timedelta(days=30)).isoformat();last=values.get('to') or today.isoformat()
        try:
            first=date.fromisoformat(first).isoformat();last=date.fromisoformat(last).isoformat()
            if first>last or (date.fromisoformat(last)-date.fromisoformat(first)).days>3660:raise ValueError()
        except (ValueError,TypeError):raise ApiError('Vyberte platné období nejvýše deseti let.')
        return first,last
    def document(c,id):
        row=one(c,'SELECT data_json FROM stock_documents WHERE user_id=%s',(id,))
        return json.loads(row['data_json']) if row else {'stores':[],'products':[],'counts':[],'moves':[],'barInventories':[]}
    @app.get('/api/inventory/analytics')
    @authenticated(permission='reports.view')
    def venue_analytics():
        if not has_permission(g.user,'stock.view'):raise ApiError('Nemáte oprávnění prohlížet zásoby.',403)
        first,last=period(request.args)
        with db() as c:data=scoped_stock(document(c,g.user.get('stock_owner_id') or g.user['id']),store_scope(c,g.user))
        return jsonify(**analyze(data,first,last,request.args.get('store',''),request.args.get('product','')))

    @app.get('/api/owner/analytics')
    @authenticated(admin=True)
    def owner_analytics():
        first,last=period(request.args);selected=request.args.get('venue','')
        span=(date.fromisoformat(last)-date.fromisoformat(first)).days+1
        previous_last=(date.fromisoformat(first)-timedelta(days=1)).isoformat();previous_first=(date.fromisoformat(first)-timedelta(days=span)).isoformat()
        with db(central=True) as c:
            if selected:owned(c,selected)
            venues=allrows(c,'SELECT * FROM allin_venues WHERE owner_id=%s ORDER BY created_at,id',(g.user['id'],))
        results=[]
        for venue in venues:
            if selected and venue['id']!=selected:continue
            with venue_context(venue),db() as c:data=document(c,venue['owner_id'])
            analytics=analyze(data,first,last,request.args.get('store',''),request.args.get('product',''))
            start_dates=[business_date(r['startAt']) for r in analytics['observations'] if r['startAt']]
            coverage_from=min([first]+start_dates)
            with db(central=True) as c:
                days=allrows(c,'SELECT * FROM pos_days WHERE venue_id=%s AND business_date>=%s AND business_date<=%s',(venue['id'],coverage_from,last))
                previous=allrows(c,'SELECT * FROM pos_days WHERE venue_id=%s AND business_date>=%s AND business_date<=%s',(venue['id'],previous_first,previous_last))
                sales=allrows(c,'SELECT * FROM pos_item_sales WHERE venue_id=%s AND business_date>=%s AND business_date<=%s',(venue['id'],coverage_from,last))
                coverage=allrows(c,'SELECT * FROM pos_item_coverage WHERE venue_id=%s AND business_date>=%s AND business_date<=%s',(venue['id'],coverage_from,last))
                recipes=allrows(c,'SELECT * FROM pos_recipes WHERE venue_id=%s ORDER BY effective_at,created_at,id',(venue['id'],))
            financial=margins([d for d in days if first<=d['business_date']<=last]);prior={r['currency']:r for r in margins(previous)}
            for row in financial:
                old=prior.get(row['currency']);current=row['grossMarginPercent'];baseline=old.get('grossMarginPercent') if old else None
                row['previousGrossMarginPercent']=baseline;row['marginChangePoints']=current-baseline if current is not None and baseline is not None else None
                row['marginAlert']=row['marginChangePoints'] is not None and row['marginChangePoints']<=-5
                row['missingClosureDays']=sum(not any(d['business_date']==day and d['currency']==row['currency'] for d in days) for day in day_range(first,last))
            results.append({'id':venue['id'],'name':venue['name'],'analytics':analytics,'financial':financial,
                'consumption':reconcile(analytics['observations'],sales,recipes,coverage,days,data['products']),
                'catalog':{'stores':data['stores'],'products':[{'id':p['id'],'name':p['name'],'unit':p['unit'],'store':p.get('store')} for p in data['products']]},
                'recipes':[{'id':r['id'],'salesCode':r['sales_code'],'effectiveAt':r['effective_at'],'ingredients':json.loads(r['ingredients_json']),'reason':r['reason']} for r in recipes]})
        return jsonify(fromDate=first,toDate=last,previousFrom=previous_first,previousTo=previous_last,venues=results)

    @app.post('/api/owner/analytics/<venue_id>/sales-import')
    @authenticated(admin=True)
    def sales_import(venue_id):
        values=body();first,last=period(values);register=values.get('register','hlavni')
        if last>datetime.now(PRAGUE).date().isoformat():raise ApiError('Položkové prodeje nelze potvrdit pro budoucí období.')
        if not isinstance(register,str) or not register.strip() or len(register)>100 or any(ord(c)<32 for c in register):raise ApiError('Neplatné označení pokladny.')
        register=register.strip()
        if values.get('complete') is not True:raise ApiError('Potvrďte úplný export pro vybranou pokladnu a období.')
        try:rows=parse_sales(values.get('csv'),first,last)
        except (ValueError,csv.Error) as error:raise ApiError(str(error))
        with db(central=True) as c:
            owned(c,venue_id);execute(c,'UPDATE allin_venues SET name=name WHERE id=%s',(venue_id,))
            old=allrows(c,'SELECT * FROM pos_item_sales WHERE venue_id=%s AND register_id=%s AND business_date>=%s AND business_date<=%s',(venue_id,register,first,last))
            import_id=uid()
            # Source IDs reused outside the declared window indicate a bad export.
            for row in rows:
                collision=one(c,'SELECT business_date FROM pos_item_sales WHERE venue_id=%s AND register_id=%s AND source_id=%s',(venue_id,register,row['source_id']))
                if collision and not first<=collision['business_date']<=last:raise ApiError('ID prodeje již existuje mimo vybrané období.',409)
            execute(c,'DELETE FROM pos_item_sales WHERE venue_id=%s AND register_id=%s AND business_date>=%s AND business_date<=%s',(venue_id,register,first,last))
            for row in rows:
                execute(c,'INSERT INTO pos_item_sales (venue_id,register_id,source_id,sold_at,business_date,sales_code,quantity,import_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',(venue_id,register,row['source_id'],row['sold_at'],row['business_date'],row['sales_code'],row['quantity'],import_id))
            for day in day_range(first,last):
                execute(c,'INSERT INTO pos_item_coverage (venue_id,register_id,business_date,import_id) VALUES (%s,%s,%s,%s) ON CONFLICT(venue_id,register_id,business_date) DO UPDATE SET import_id=excluded.import_id',(venue_id,register,day,import_id))
            execute(c,'INSERT INTO pos_item_imports (id,venue_id,register_id,from_date,to_date,row_count,actor_id,created_at,snapshot_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',(import_id,venue_id,register,first,last,len(rows),g.user['id'],time.time(),json.dumps({'before':old,'after':rows},ensure_ascii=False)))
            audit(c,g.user['id'],'pos_items_imported','Položkové prodeje: '+str(len(rows)))
        return jsonify(ok=True,rows=len(rows))

    @app.post('/api/owner/analytics/<venue_id>/recipes')
    @authenticated(admin=True)
    def recipe_save(venue_id):
        values=body();code=values.get('salesCode');ingredients=values.get('ingredients');reason=values.get('reason','')
        if not isinstance(code,str) or not code.strip() or len(code)>150 or any(ord(c)<32 for c in code) or not isinstance(ingredients,list) or not 1<=len(ingredients)<=100:raise ApiError('Zadejte kód produktu pokladny a 1–100 surovin.')
        if not isinstance(reason,str) or not 5<=len(reason.strip())<=500:raise ApiError('Uveďte důvod nastavení receptury (5–500 znaků).')
        try:effective=datetime.combine(date.fromisoformat(values.get('from','')),daytime.min,PRAGUE).astimezone(timezone.utc).isoformat()
        except (ValueError,TypeError):raise ApiError('Zadejte datum platnosti receptury.')
        with db(central=True) as c:venue=owned(c,venue_id)
        with venue_context(venue),db() as c:catalog=document(c,venue['owner_id'])
        products={p['id']:p for p in catalog['products']};stores={s['id'] for s in catalog['stores']};seen=set();clean=[]
        for row in ingredients:
            if not isinstance(row,dict):raise ApiError('Neplatná surovina.')
            if not isinstance(row.get('productId'),str) or not isinstance(row.get('storeId'),str):raise ApiError('Vyberte produkt a sklad suroviny.')
            p=products.get(row.get('productId'));sid=row.get('storeId');qty=row.get('quantity');unit=row.get('unit')
            if not p or sid not in stores or (p.get('store') and p['store']!=sid) or (sid,p['id']) in seen or type(qty) not in (int,float) or not math.isfinite(qty) or not 0<qty<=1e9:raise ApiError('Surovina musí patřit do vybraného skladu a mít kladné množství.')
            if not isinstance(unit,str):raise ApiError('Vyberte jednotku suroviny.')
            normalized,amount=canonical(unit,qty)
            if normalized!=p['unit']:raise ApiError('Jednotka receptury neodpovídá skladové jednotce.')
            seen.add((sid,p['id']));clean.append({'productId':p['id'],'storeId':sid,'quantity':amount,'unit':normalized})
        with db(central=True) as c:
            owned(c,venue_id)
            execute(c,'INSERT INTO pos_recipes (id,venue_id,sales_code,effective_at,ingredients_json,actor_id,reason,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',(uid(),venue_id,code.strip(),effective,json.dumps(clean),g.user['id'],reason.strip(),time.time()))
            audit(c,g.user['id'],'pos_recipe_changed','Receptura: '+code.strip()+' · '+reason.strip())
        return jsonify(ok=True)

    @app.get('/api/owner/analytics/sales-template')
    @authenticated(admin=True)
    def template():
        response=make_response('\ufeffprodej_id;datum_cas;produkt_pokladny;pocet\nPRODEJ-001;2026-01-01T20:00:00+01:00;PIVO-05;2\n')
        response.headers['Content-Type']='text/csv; charset=utf-8';response.headers['Content-Disposition']='attachment; filename=noira-polozkove-prodeje.csv';response.headers['Cache-Control']='no-store';return response
