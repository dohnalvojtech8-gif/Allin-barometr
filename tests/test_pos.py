import pytest
from tests.test_allin import hub,create,enter
from server.app import app,db,one,execute,digest,password_hash
from server.pos import parse_csv
import secrets,time,uuid

CSV='datum;kasa;mena;trzby_bez_dph;naklady_zbozi;provozni_naklady;uzaverka_id\n2025-01-01;bar;CZK;10000,50;3000;2000;UZ1\n2025-01-02;bar;CZK;5000;;;UZ2\n'

def test_money_and_csv_validation():
 rows=parse_csv(CSV,'csv');assert rows[0]['revenue_net']==1000050 and rows[0]['cogs']==300000
 assert rows[1]['cogs'] is None
 assert parse_csv('datum;trzby_bez_dph\n2025-01-01;10\n','csv','Moje kasa')[0]['register_id']=='Moje kasa'
 for bad in ['datum;trzby\n2025-01-01;12\n','datum;trzby_bez_dph\n2025-01-01;NaN\n','datum;trzby_bez_dph\n2025-01-01;1.234\n','datum;trzby_bez_dph\n2999-01-01;10\n']:
  with pytest.raises(ValueError):parse_csv(bad,'csv')
 with pytest.raises(ValueError):parse_csv(CSV+CSV.splitlines()[1]+'\n','csv')


def test_import_history_corrections_and_unknown_profit(hub):
 client,h,_=hub;a=create(hub,'Denní historie')
 assert client.put('/api/owner/pos/'+a,json={'provider':'dotykacka','registerLabel':'Bar'},headers=h).status_code==200
 url='/api/owner/pos/'+a+'/import'
 first=client.post(url,json={'csv':CSV},headers=h);assert first.status_code==200,first.json
 assert first.json=={'inserted':2,'updated':0,'unchanged':0}
 assert client.post(url,json={'csv':CSV},headers=h).json['unchanged']==2
 rows=client.get('/api/owner/pos/days',query_string={'venue':a}).json
 assert rows['total']==2
 missing,known=rows['days'];assert missing['profit'] is None and known['profit']==500050
 correction=CSV.replace('10000,50','11000,50')
 assert client.post(url,json={'csv':correction},headers=h).json['updated']==1
 detail=client.get('/api/owner/pos/days/'+known['id']).json
 assert detail['day']['revision']==2 and len(detail['revisions'])==2
 assert detail['revisions'][1]['data']['revenue_net']==1000050
 filtered=client.get('/api/owner/pos/days',query_string={'venue':a,'from':'2025-01-02','to':'2025-01-02'}).json
 assert filtered['total']==1 and filtered['totals'][0]['missing']==1
 assert client.get('/api/owner/pos/days?from=2025-03-01&to=2025-01-01').status_code==400
 status=client.get('/api/owner/pos').json
 venue=next(v for v in status['venues'] if v['id']==a);assert venue['automaticSync'] is False and venue['latest']['business_date']=='2025-01-02'
 assert client.get('/api/owner/pos/export',query_string={'venue':a}).status_code==200
 assert client.get('/api/owner/pos/template').status_code==200


def test_owner_only_access_even_inside_venue_and_against_other_owners(hub):
 client,h,owner=hub;a=create(hub,'Soukromé finance');pa,ha=enter(hub,a)
 assert client.post('/api/owner/pos/'+a+'/import',json={'csv':CSV},headers=h).status_code==200
 assert app.test_client().get('/api/owner/pos').status_code==401
 assert client.get(pa+'/api/owner/pos').status_code==403
 assert client.get(pa+'/api/owner/pos/days').status_code==403
 # Ordinary root account, including users.manage, cannot access financial endpoints.
 token=secrets.token_urlsafe(32);user_id=str(uuid.uuid4());csrf=secrets.token_urlsafe(24)
 with db(central=True) as c:
  execute(c,"INSERT INTO users (id,username,username_key,first_name,last_name,password_hash,role,created_at,permissions_json) VALUES (%s,%s,%s,'Staff','Member',%s,'user',%s,%s)",(user_id,user_id,user_id,password_hash('staff-password'),time.time(),'{"users.manage":true}'))
  execute(c,'INSERT INTO sessions (token_hash,user_id,csrf,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)',(digest(token),user_id,csrf,time.time(),time.time()+86400))
 outsider=app.test_client();outsider.set_cookie('barometr_session',token)
 assert outsider.get('/api/owner/pos').status_code==403
 with db(central=True) as c:execute(c,"UPDATE users SET role='admin' WHERE id=%s",(user_id,))
 assert outsider.get('/api/owner/pos').json['venues']==[]
 assert outsider.get('/api/owner/pos/days').json['days']==[]
 assert outsider.get('/api/owner/pos/days?venue='+a).status_code==404
 detail_id=client.get('/api/owner/pos/days?venue='+a).json['days'][0]['id']
 assert outsider.get('/api/owner/pos/days/'+detail_id).status_code==404
 assert outsider.post('/api/owner/pos/'+a+'/import',json={'csv':CSV},headers={'X-CSRF-Token':csrf}).status_code==404


def test_atomic_import_and_currency_separation(hub):
 client,h,_=hub;a=create(hub,'Měny');url='/api/owner/pos/'+a+'/import'
 assert client.post(url,json={'csv':CSV},headers=h).status_code==200
 # Another currency on a separate register remains separate in totals.
 euro='datum;kasa;mena;trzby_bez_dph;naklady_zbozi;provozni_naklady\n2025-01-01;eur;EUR;100;20;30\n'
 assert client.post(url,json={'csv':euro},headers=h).status_code==200
 totals=client.get('/api/owner/pos/days?venue='+a).json['totals'];assert {t['currency'] for t in totals}=={'CZK','EUR'}
 assert all(type(t['revenue_net']) is int for t in totals)
 assert client.post(url,json={'csv':euro.replace('2025-01-01','2025-01-02')},headers=h).status_code==200
 latest=next(v for v in client.get('/api/owner/pos').json['venues'] if v['id']==a)['latestResults']
 assert {d['currency'] for d in latest}=={'CZK','EUR'}
 assert next(d for d in latest if d['currency']=='CZK')['profit'] is None
 before=client.get('/api/owner/pos/days?venue='+a).json['total']
 conflict='datum;kasa;mena;trzby_bez_dph\n2025-01-03;novy;CZK;500\n2025-01-01;bar;EUR;999\n'
 assert client.post(url,json={'csv':conflict},headers=h).status_code==409
 assert client.get('/api/owner/pos/days?venue='+a).json['total']==before
