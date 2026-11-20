"""Product setup, saved keg scope and bottle reconciliation against real stock."""
import copy
import json
import uuid
from datetime import datetime,timezone
import pytest
from tests.test_allin import hub,create,enter
from tests.test_employees import profile
from server.app import app,db,one,allrows,execute,PRODUCTS
from server.allin import venue_context
from server.stock import current_quantity,validate_stock


def product(**values):
 return {'id':str(uuid.uuid4()),'store':'main','name':'Zboží','category':'Obal','kind':'piece','unit':'ks','cost':0,'min':0,'minEnabled':False,'capacity':0,'tare':0,'density':1,'packSize':1,'fullWeightKg':0,**values}


def setup(hub):
 client,h,owner=hub;venue=create(hub,'Nové produkty');prefix,vh=enter(hub,venue)
 return client,venue,prefix,vh


def add(client,prefix,headers,values,opening=0):
 current=client.get(prefix+'/api/stock').json
 return client.post(prefix+'/api/stock/products',json={'product':values,'openingQty':opening,'revision':current['revision']},headers=headers)


def bottle(ml=340,id='bar-bottle',capacity=500):
 return {'id':id,'productId':'amundsen','capacity':capacity,'label':'Vodka na baru','start':capacity,'ml':ml,'sold40':0,'sold20':0,'otherMl':0}


def state(client,prefix,h,rows,plan=False):
 current=client.get(prefix+'/api/me').json['state'];current['rows']=rows
 if plan:current['inventoryPlan']={'runId':'test-round','entries':[{'id':'entry','productId':'amundsen','capacity':500,'rowId':rows[0]['id'],'status':'done'}]}
 response=client.put(prefix+'/api/state',json=current,headers=h);assert response.status_code==200,response.json


def bar_run(rows,id=None):
 return {'id':id or str(uuid.uuid4()),'at':datetime.now(timezone.utc).isoformat(),'items':[{'id':r['id'],'barRowId':r['id'],'source':'bar','catalogProductId':r['productId'],'bottleMl':r['capacity'],'originalMl':r['ml'],'name':'Vodka','qty':r['ml'],'unit':'ml','expected':None,'cost':0} for r in rows]}


def close(client,prefix,h,run):
 current=client.get(prefix+'/api/stock').json;current['data']['barInventories'].append(run)
 return client.put(prefix+'/api/stock',json={'revision':current['revision'],'data':current['data']},headers=h)


def prepare_liquor(hub):
 client,venue,prefix,h=setup(hub)
 assert client.post(prefix+'/api/unlocks',json={'productId':'amundsen'},headers=h).status_code==200
 p=product(name='Vodka Amundsen 500',category='Lihoviny',kind='liquid',catalogProductId='amundsen',catalogCapacityMl=500,capacity=.5)
 response=add(client,prefix,h,p,5);assert response.status_code==201,response.json
 return client,venue,prefix,h,p


def test_default_custom_categories_and_opening_balance(hub):
 client,venue,prefix,h=setup(hub)
 resources=client.get(prefix+'/api/stock/resources?store=main').json
 assert [r['name'] for r in resources['categories']]==['Obal','Sud','Lihoviny']
 assert resources['kegs']==[] and resources['catalog']==[]
 for unit in ('ks','l','ml','kg','balení'):
  p=product(unit=unit);response=add(client,prefix,h,p)
  assert response.status_code==201,response.json
  assert current_quantity(response.json['data'],p['id'],'main')==0
  assert next(c for c in response.json['data']['counts'] if c['product']==p['id'])['opening']
 current=client.get(prefix+'/api/stock').json;current['data']['stores'][0]['categories']=[{'name':'Pivo','kind':'keg'},{'name':'Pochutiny','kind':'piece'}]
 assert client.put(prefix+'/api/stock',json=current,headers=h).status_code==200
 assert client.get(prefix+'/api/stock/resources?store=main').json['categories'][0]['name']=='Pivo'
 current=client.get(prefix+'/api/stock').json;current['data']['stores'][0]['categories']=[]
 assert client.put(prefix+'/api/stock',json=current,headers=h).status_code==200
 assert client.get(prefix+'/api/stock/resources?store=main').json['categories']==[]
 assert len(client.get(prefix+'/api/stock').json['data']['products'])==5


def test_activated_liquor_link_is_per_venue_and_variant(hub):
 client,venue,prefix,h,p=prepare_liquor(hub)
 catalog=client.get(prefix+'/api/stock/resources?store=main').json['catalog'];assert [r['id'] for r in catalog]==['amundsen']
 assert 500 in [v['ml'] for v in catalog[0]['variants']]
 assert add(client,prefix,h,product(kind='liquid',catalogProductId='amundsen',catalogCapacityMl=333)).status_code==400
 assert add(client,prefix,h,product(kind='liquid',catalogProductId='amundsen',catalogCapacityMl=500),2.5).status_code==400
 other=create(hub,'Jiný bar');pb,hb=enter(hub,other)
 assert client.get(pb+'/api/stock/resources?store=main').json['catalog']==[]
 assert add(client,pb,hb,p,5).status_code==400


def test_keg_profile_is_saved_by_weighing_and_not_shared_between_venues(hub):
 client,venue,prefix,h=setup(hub);p=product(name='Můj sud 50 l',category='Sud',kind='keg',unit='l',capacity=50,tare=7,fullWeightKg=77)
 response=add(client,prefix,h,p);assert response.status_code==201,response.json
 current=client.get(prefix+'/api/stock').json;current['data']['counts'].append({'id':'weigh','inventoryId':'weigh','product':p['id'],'store':'main','qty':25,'at':'2026-11-19T12:00:00+00:00'})
 reading={'productId':p['id'],'storeId':'main','target':'stock','gross':42,'tare':7,'fullWeightKg':77,'capacity':50,'density':1,'readingRole':'partial'}
 response=client.put(prefix+'/api/stock',json={**current,'kegMeasurement':reading},headers=h);assert response.status_code==200,response.json
 saved=client.get(prefix+'/api/stock/resources?store=main').json['kegs'][0]
 assert saved['tare']==7 and saved['fullWeightKg']==77 and saved['measured']
 new=product(name='Jiný název výrobku',category='Sud',kind='keg',unit='l',capacity=50,tare=7,fullWeightKg=77,kegProfileId=saved['id'],kegWeightState='empty')
 response=add(client,prefix,h,new,3);assert response.status_code==201,response.json
 assert current_quantity(response.json['data'],new['id'],'main')==3
 # Stale writes cannot append readings or modify a saved calibration.
 assert client.put(prefix+'/api/stock',json={**current,'kegMeasurement':{**reading,'tare':8}},headers=h).status_code==409
 with db(central=True) as c:v=one(c,'SELECT * FROM allin_venues WHERE id=%s',(venue,))
 with app.test_request_context(),venue_context(v),db() as c:assert one(c,'SELECT COUNT(*) AS n FROM stock_keg_readings')['n']==1
 other=create(hub,'Oddělený');other_prefix,other_h=enter(hub,other)
 assert client.get(other_prefix+'/api/stock/resources?store=main').json['kegs']==[]
 assert add(client,other_prefix,other_h,new).status_code==400


def test_bar_preview_counts_340_ml_plus_five_500_ml_bottles(hub):
 client,venue,prefix,h,p=prepare_liquor(hub);rows=[bottle()];state(client,prefix,h,rows)
 run=bar_run(rows);current=client.get(prefix+'/api/stock').json
 response=client.post(prefix+'/api/stock/bar-preview',json={'revision':current['revision'],'bar':run},headers=h);assert response.status_code==200,response.json
 summary=response.json['bar']['bottleSummary'][0]
 assert summary['barMl']==340 and summary['stockMl']==2500 and summary['totalMl']==2840
 assert summary['totalBottles']==6 and summary['fullBottles']==5 and summary['partialBottles']==1
 response=close(client,prefix,h,response.json['bar']);assert response.status_code==200,response.json
 assert current_quantity(response.json['data'],p['id'],'main')==5
 assert response.json['data']['barInventories'][-1]['bottleSummary'][0]['totalMl']==2840


def test_zero_bottles_are_archived_once_with_inventory_and_not_reintroduced(hub):
 client,venue,prefix,h,p=prepare_liquor(hub);state(client,prefix,h,[bottle()],plan=True)
 state(client,prefix,h,[bottle(0)],plan=True)
 original=client.get(prefix+'/api/me').json['state'];assert original['rows'][0]['ml']==0
 run=bar_run([bottle(0)]);current=client.get(prefix+'/api/stock').json
 preview=client.post(prefix+'/api/stock/bar-preview',json={'revision':current['revision'],'bar':run},headers=h).json['bar']
 assert preview['bottleSummary'][0]['consumedBottles']==1
 assert preview['bottleSummary'][0]['emptyBottles']==1
 result=close(client,prefix,h,preview);assert result.status_code==200,result.json
 archived=result.json['data']['barInventories'][-1]
 assert archived['archivedEmptyBottles'][0]['bottle']['ml']==0 and archived['bottleSummary'][0]['consumedBottles']==1
 current_state=client.get(prefix+'/api/me').json['state'];assert current_state['rows']==[] and current_state['inventoryPlan']['entries']==[]
 assert client.put(prefix+'/api/state',json=original,headers=h).status_code==409
 fresh=client.get(prefix+'/api/stock').json
 next_preview=client.post(prefix+'/api/stock/bar-preview',json={'revision':fresh['revision'],'bar':bar_run([])},headers=h)
 assert next_preview.status_code==200 and next_preview.json['bar']['bottleSummary']==[]
 assert current_quantity(fresh['data'],p['id'],'main')==5


def test_size_groups_empty_initial_bottle_and_stock_count_correction(hub):
 client,venue,prefix,h,p=prepare_liquor(hub)
 second=product(name='Vodka 700',category='Lihoviny',kind='liquid',catalogProductId='amundsen',catalogCapacityMl=700,capacity=.7)
 assert add(client,prefix,h,second,2).status_code==201
 rows=[bottle(340),bottle(700,id='full-700',capacity=700),bottle(0,id='initially-empty',capacity=500)];state(client,prefix,h,rows)
 run=bar_run(rows);run['stockCounts']={p['id']:4}
 current=client.get(prefix+'/api/stock').json
 preview=client.post(prefix+'/api/stock/bar-preview',json={'revision':current['revision'],'bar':run},headers=h)
 assert preview.status_code==200,preview.json
 sizes={r['bottleMl']:r for r in preview.json['bar']['bottleSummary']}
 assert sizes[500]['stockBottles']==4 and sizes[700]['stockBottles']==2
 assert sizes[700]['fullBottles']==3 and sizes[500]['partialBottles']==1
 assert sizes[500]['consumedBottles']==0  # An initially empty bottle was never sold.
 result=close(client,prefix,h,preview.json['bar']);assert result.status_code==200,result.json
 assert current_quantity(result.json['data'],p['id'],'main')==4
 assert all(r['ml']>0 for r in client.get(prefix+'/api/me').json['state']['rows'])


def test_inline_zero_correction_requires_reason_and_archives(hub):
 client,venue,prefix,h,p=prepare_liquor(hub);rows=[bottle()];state(client,prefix,h,rows)
 run=bar_run(rows);run['items'][0]['qty']=0
 assert close(client,prefix,h,run).status_code==400
 run['adjustmentReason']='Ověřeno, lahev je zcela prázdná'
 result=close(client,prefix,h,run);assert result.status_code==200,result.json
 assert result.json['data']['barInventories'][-1]['bottleSummary'][0]['consumedBottles']==1
 assert client.get(prefix+'/api/me').json['state']['rows']==[]


def test_empty_measurement_correction_does_not_count_a_sale(hub):
 client,venue,prefix,h,p=prepare_liquor(hub);state(client,prefix,h,[bottle()]);state(client,prefix,h,[bottle(0)])
 run=bar_run([bottle(0)]);run['items'][0]['qty']=120;run['adjustmentReason']='Oprava chybně odečtené nulové hladiny'
 result=close(client,prefix,h,run);assert result.status_code==200,result.json
 summary=result.json['data']['barInventories'][-1]['bottleSummary'][0]
 assert summary['consumedBottles']==0 and summary['emptyBottles']==0 and summary['partialBottles']==1
 assert client.get(prefix+'/api/me').json['state']['rows'][0]['ml']==120


def test_employee_zero_archival_and_returned_inventory_restoration(hub):
 from tests.test_intelligence import staff
 client,venue,prefix,h,p=prepare_liquor(hub);employee,eh,user=staff(hub,venue)
 assert employee.post(prefix+'/api/unlocks',json={'productId':'amundsen'},headers=eh).status_code==200
 state(employee,prefix,eh,[bottle()]);state(employee,prefix,eh,[bottle(0)],plan=True)
 run=bar_run([bottle(0)]);result=close(employee,prefix,eh,run)
 assert result.status_code==200 and result.json['pendingInventoryIds']==[run['id']],result.json
 assert employee.get(prefix+'/api/me').json['state']['rows']==[]
 url=prefix+'/api/inventory/submissions/'+run['id']
 detail=client.get(url).json['submission'];assert detail['content']['bars'][0]['bottleSummary'][0]['consumedBottles']==1
 assert client.post(url+'/decision',json={'action':'return','revision':1,'reason':'Prověřte chybně prázdnou lahev'},headers=h).status_code==200
 quantities={bar['id']+':'+str(i):item['qty'] for bar in detail['content']['bars'] for i,item in enumerate(bar['items'])};quantities[run['id']+':0']=120
 response=employee.post(url+'/resubmit',json={'revision':2,'reason':'Ověřeno ručně, v lahvi zbývá 120 ml','quantities':quantities},headers=eh)
 assert response.status_code==200,response.json
 assert employee.get(prefix+'/api/me').json['state']['rows'][0]['ml']==120
 detail=client.get(url).json['submission'];summary=detail['content']['bars'][0]['bottleSummary'][0]
 assert summary['consumedBottles']==0 and summary['partialBottles']==1
 approved=client.post(url+'/decision',json={'action':'approve','revision':3},headers=h)
 assert approved.status_code==200,approved.json
 assert current_quantity(employee.get(prefix+'/api/stock').json['data'],p['id'],'main')==5


def test_coowner_archives_shared_bar_with_own_audit_identity(hub):
 from tests.test_coowners import add as coowner
 client,venue,prefix,h,p=prepare_liquor(hub);other,values=coowner(hub);account,ch,actor=other;cp,headers=enter(other,venue)
 state(client,prefix,h,[bottle()]);state(account,cp,headers,[bottle(0)])
 result=close(account,cp,headers,bar_run([bottle(0)]));assert result.status_code==200,result.json
 assert client.get(prefix+'/api/me').json['state']['rows']==[]
 assert result.json['data']['barInventories'][-1]['bottleSummary'][0]['consumedBottles']==1
 with db(central=True) as c:v=one(c,'SELECT * FROM allin_venues WHERE id=%s',(venue,))
 with app.test_request_context(),venue_context(v),db() as c:
  event=one(c,'SELECT * FROM bar_bottle_depletions');assert event['user_id']==hub[2] and event['actor_name']=='Jana Spolumajitelka'
  assert one(c,"SELECT user_id FROM events WHERE action='empty_bottles_archived'")['user_id']==actor
