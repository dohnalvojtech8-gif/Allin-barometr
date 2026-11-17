"""Approval boundaries, missing-data handling and reproducible operational evidence."""
import copy
import json
import uuid
from datetime import datetime,timezone
import pytest
from tests.test_allin import hub,create,enter
from tests.test_employees import profile
from server.app import app,db,one,execute,allrows
from server.allin import venue_context
from server.analytics import analyze,observations,margins
from server.operations import parse_sales,reconcile

def stock():
 return {'stores':[{'id':'main','name':'Kuchyně'}],'products':[{'id':'flour','name':'Mouka','store':'main','category':'Suroviny','unit':'kg','kind':'weight','cost':0,'min':0,'tare':0,'capacity':0,'density':1}],
 'counts':[],'moves':[],'draft':None,'barInventories':[]}

def staff(hub,venue,pin='2468',permissions=None):
 client,h,_=hub;values=profile(pin=pin)
 if permissions is not None:values['permissions']=permissions
 response=client.post('/api/owner/venues/'+venue+'/members',json=values,headers=h);assert response.status_code==201,response.json
 account=app.test_client();account.environ_base['REMOTE_ADDR']='intelligence-'+uuid.uuid4().hex
 assert account.post('/api/login',json={'username':values['username'],'password':values['password']}).status_code==200
 prefix='/v/'+venue;me=account.get(prefix+'/api/me').json
 return account,{'X-CSRF-Token':me['csrf']},me['user']

def setup(hub):
 client,h,_=hub;venue=create(hub,'Kontrola');prefix,vh=enter(hub,venue);document=stock()
 document['counts']=[{'id':'opening','product':'flour','store':'main','qty':100,'at':'2026-01-01T10:00:00+00:00'}]
 assert client.put(prefix+'/api/stock',json={'revision':0,'data':document},headers=vh).status_code==200
 return client,venue,prefix,vh

def submit(account,headers,prefix):
 current=account.get(prefix+'/api/stock').json;document=current['data'];id='inventory-'+uuid.uuid4().hex
 document['counts'].append({'id':id+'-flour','inventoryId':id,'store':'main','product':'flour','qty':90,'at':datetime.now(timezone.utc).isoformat()})
 response=account.put(prefix+'/api/stock',json={'revision':current['revision'],'data':document},headers=headers)
 assert response.status_code==200,response.json
 assert response.json['pendingInventoryIds']==[id]
 assert len(response.json['data']['counts'])==1
 return id

def test_submission_review_correction_and_authoritative_stock(hub):
 client,venue,prefix,vh=setup(hub);employee,eh,user=staff(hub,venue)
 id=submit(employee,eh,prefix);url=prefix+'/api/inventory/submissions/'+id
 detail=employee.get(url).json;assert detail['submission']['status']=='pending'
 assert employee.post(url+'/decision',json={'action':'approve','revision':1},headers=eh).status_code==403
 manager,mh,manager_user=staff(hub,venue,pin='3579',permissions={'inventory.review':True})
 decision=manager.post(url+'/decision',json={'action':'return','revision':1,'reason':'Nesouhlasí počet balení'},headers=mh)
 assert decision.status_code==200,decision.json
 assert employee.post(url+'/resubmit',json={'revision':2,'reason':'','quantities':{id+'-flour':95}},headers=eh).status_code==400
 assert employee.post(url+'/resubmit',json={'revision':2,'reason':'Ověřeno přepočtem balení','quantities':{id+'-flour':95}},headers=eh).status_code==200
 approved=manager.post(url+'/decision',json={'action':'approve','revision':3},headers=mh);assert approved.status_code==200,approved.json
 assert manager.post(url+'/decision',json={'action':'approve','revision':3},headers=mh).status_code==409
 current=employee.get(prefix+'/api/stock').json
 count=next(r for r in current['data']['counts'] if r.get('reviewId')==id)
 assert count['qty']==95 and count['actorId']==user['id']
 assert manager.get(url).json['submission']['reviewed_by']==manager_user['id']
 altered=copy.deepcopy(current['data']);next(r for r in altered['counts'] if r.get('reviewId')==id)['qty']=94
 assert manager.put(prefix+'/api/stock',json={'revision':current['revision'],'data':altered,'correctionReason':'Oprava testem'},headers=mh).status_code==403
 assert client.put(prefix+'/api/stock',json={'revision':current['revision'],'data':altered},headers=vh).status_code==400
 assert client.put(prefix+'/api/stock',json={'revision':current['revision'],'data':altered,'correctionReason':'Dohledaná chyba převodu balení'},headers=vh).status_code==200
 actions=client.get(url).json['events'];assert [e['action'] for e in actions]==['submitted','returned','resubmitted','approved','corrected']
 assert actions[-1]['actor_id']==hub[2] and actions[-1]['reason']=='Dohledaná chyba převodu balení'
 assert employee.get('/api/owner/analytics').status_code==401
 assert employee.get(prefix+'/api/owner/analytics').status_code==403

def test_no_self_approval_cross_venue_access_or_forged_actor(hub):
 client,venue,prefix,vh=setup(hub);manager,mh,user=staff(hub,venue,permissions={'inventory.review':True})
 id=submit(manager,mh,prefix);url=prefix+'/api/inventory/submissions/'+id
 assert manager.post(url+'/decision',json={'action':'approve','revision':1},headers=mh).status_code==403
 other=create(hub,'Jiný provoz');other_prefix,other_h=enter(hub,other)
 assert client.get(other_prefix+'/api/inventory/submissions/'+id).status_code==404
 assert client.post(other_prefix+'/api/inventory/submissions/'+id+'/decision',json={'action':'approve','revision':1},headers=other_h).status_code==404
 # Review notifications carry an explicit capability audience.
 with db(central=True) as c:record=one(c,'SELECT * FROM allin_venues WHERE id=%s',(venue,))
 with app.test_request_context(),venue_context(record),db() as c:
  notice=one(c,"SELECT * FROM notification_outbox WHERE kind='inventory_review'")
  assert json.loads(notice['payload_json'])['requiredPermission']=='inventory.review'
 assert client.post(url+'/decision',json={'action':'approve','revision':1},headers=vh).status_code==200

def test_missing_baseline_unit_separation_and_repeated_spikes():
 document=stock()
 document['counts']=[{'id':'c'+str(i),'product':'flour','store':'main','qty':qty,'expected':100 if i else None,'at':f'2026-01-{i+1:02d}T10:00:00+00:00'} for i,qty in enumerate([100,99,99,99,99,99,60])]
 document['products'].append({**document['products'][0],'id':'bottle','name':'Lahev','unit':'ks','kind':'piece'})
 document['counts'].append({'id':'piece','product':'bottle','store':'main','qty':1,'expected':2,'at':'2026-01-07T10:00:00+00:00'})
 report=analyze(document,'2026-01-01','2026-01-31')
 assert report['withoutBaseline']==1
 assert {r['unit'] for r in report['byMonth']}=={'ks','kg'}
 assert any(a['type']=='recurring_shortage' for a in report['alerts'])
 assert any(a['type']=='unusual_deviation' and a['sampleCount']==5 for a in report['alerts'])
 assert next(r for r in report['observations'] if r['id']=='c0')['consumption'] is None

def test_consumption_sales_coverage_recipes_and_declared_waste():
 document=stock();document['counts']=[{'id':'first','store':'main','product':'flour','qty':100,'at':'2026-01-01T10:00:00+00:00'},{'id':'last','store':'main','product':'flour','qty':70,'expected':100,'at':'2026-01-02T10:00:00+00:00'}]
 document['moves']=[{'id':'waste','store':'main','product':'flour','qty':-5,'reason':'Odpis','at':'2026-01-01T11:00:00+00:00'}]
 values=observations(document);assert values[-1]['consumption']==25
 sales=[{'sales_code':'DISH','quantity':25,'sold_at':'2026-01-01T20:00:00+00:00'}]
 recipes=[{'id':'r','sales_code':'DISH','effective_at':'2025-01-01T00:00:00+00:00','created_at':1,'ingredients_json':json.dumps([{'productId':'flour','storeId':'main','unit':'g','quantity':1000}])}]
 days=[{'business_date':day,'register_id':'main'} for day in ('2026-01-01','2026-01-02')]
 result=reconcile(values,sales,recipes,days,days,document['products'])
 assert result[-1]['status']=='complete' and result[-1]['theoreticalConsumption']==25 and not result[-1]['alert']
 assert reconcile(values,sales,recipes,[],days,document['products'])[-1]['status']=='incomplete_sales'
 assert reconcile(values,sales,[],days,days,document['products'])[-1]['status']=='missing_recipe'
 sales[0]['quantity']=10
 assert reconcile(values,sales,recipes,days,days,document['products'])[-1]['alert']

def test_margin_is_not_fabricated_and_currencies_are_separate():
 result=margins([{'business_date':'2026-01-01','currency':'CZK','revenue_net':100000,'cogs':None,'operating_costs':0},{'business_date':'2026-01-01','currency':'EUR','revenue_net':10000,'cogs':4000,'operating_costs':1000}])
 assert result[0]['grossMarginPercent'] is None and result[0]['profitEstimate'] is None
 assert result[1]['grossMarginPercent']==60 and result[1]['profitEstimate']==5000

def test_item_csv_timezone_duplicate_and_window_validation():
 csv='prodej_id;datum_cas;produkt_pokladny;pocet\n1;2026-01-01T20:00:00+01:00;DISH;2\n'
 rows=parse_sales(csv,'2026-01-01','2026-01-01');assert rows[0]['sold_at']=='2026-01-01T19:00:00+00:00'
 for invalid in [csv+'1;2026-01-01T20:00:00+01:00;DISH;2\n',csv.replace('20:00:00+01:00','20:00:00'),csv.replace(';2\n',';NaN\n')]:
  with pytest.raises(ValueError):parse_sales(invalid,'2026-01-01','2026-01-01')
 with pytest.raises(ValueError):parse_sales(csv,'2026-01-02','2026-01-02')

def test_owner_recipe_and_sales_import_are_versioned_and_idempotent(hub):
 client,venue,prefix,vh=setup(hub);h=hub[1]
 recipe={'salesCode':'DISH','from':'2026-01-01','ingredients':[{'productId':'flour','storeId':'main','unit':'g','quantity':250}],'reason':'Výchozí receptura pokrmu'}
 url='/api/owner/analytics/'+venue
 assert client.post(url+'/recipes',json=recipe,headers=h).status_code==200
 payload={'from':'2026-01-01','to':'2026-01-01','register':'hlavni','complete':True,'csv':'prodej_id;datum_cas;produkt_pokladny;pocet\n1;2026-01-01T20:00:00+01:00;DISH;2\n'}
 assert client.post(url+'/sales-import',json={**payload,'complete':False},headers=h).status_code==400
 for _ in range(2):assert client.post(url+'/sales-import',json=payload,headers=h).status_code==200
 with db(central=True) as c:
  assert one(c,'SELECT COUNT(*) AS n FROM pos_item_sales WHERE venue_id=%s',(venue,))['n']==1
  assert one(c,'SELECT COUNT(*) AS n FROM pos_item_imports WHERE venue_id=%s',(venue,))['n']==2
  assert json.loads(one(c,'SELECT ingredients_json FROM pos_recipes WHERE venue_id=%s',(venue,))['ingredients_json'])[0]['quantity']==.25
 report=client.get('/api/owner/analytics?from=2026-01-01&to=2026-01-31&venue='+venue)
 assert report.status_code==200,report.json
 assert report.json['venues'][0]['recipes'][0]['salesCode']=='DISH'
 assert client.get('/api/owner/analytics?from=bad').status_code==400
