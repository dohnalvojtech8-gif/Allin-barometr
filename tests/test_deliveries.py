"""Atomic delivery receipts, private invoices, owner consolidation and bar transfers."""
import copy
import uuid
from tests.test_allin import hub,create,enter
from tests.test_stock_products import product,add,prepare_liquor,bottle,state,bar_run,close
from tests.test_intelligence import staff
from server.app import app,db,one,allrows,execute
from server.stock import current_quantity
from server.allin import venue_context

JPEG='data:image/jpeg;base64,/9j/2Q=='
def setup(hub):
 client,h,owner=hub;venue=create(hub,'Dodávky');prefix,vh=enter(hub,venue)
 doc=client.get(prefix+'/api/stock').json;doc['data']['stores'] += [{'id':'kitchen','name':'Kuchyně'},{'id':'cellar','name':'Sklep'}]
 assert client.put(prefix+'/api/stock',json=doc,headers=vh).status_code==200
 products=[]
 for sid,name,unit in [('main','Lahev','ks'),('kitchen','Mouka','kg'),('cellar','Sud','l')]:
  p=product(store=sid,name=name,unit=unit);assert add(client,prefix,vh,p).status_code==201;products.append(p)
 return client,venue,prefix,vh,products

def receive(client,prefix,h,products,**extra):
 values={'id':str(uuid.uuid4()),'revision':client.get(prefix+'/api/stock').json['revision'],'supplier':'Velkoobchod Alfa','reference':'FA-2026-001','note':'Ranní dodávka','items':[{'product':p['id'],'store':p['store'],'qty':i+2} for i,p in enumerate(products)],**extra}
 return client.post(prefix+'/api/deliveries',json=values,headers=h),values

def photo():return {'id':str(uuid.uuid4()),'name':'Faktura.jpg','image':JPEG}

def test_one_delivery_posts_to_three_stores_once_and_freezes_history(hub):
 client,venue,prefix,h,products=setup(hub);attachment=photo();response,values=receive(client,prefix,h,products,photos=[attachment])
 assert response.status_code==201,response.json
 for i,p in enumerate(products):assert current_quantity(response.json['data'],p['id'],p['store'])==i+2
 history=client.get(prefix+'/api/deliveries').json;assert history['total']==1
 row=history['deliveries'][0];assert row['id']==values['id'] and len(row['stores'])==3 and row['photoCount']==1
 retry=client.post(prefix+'/api/deliveries',json=values,headers=h);assert retry.status_code==200 and retry.json['duplicate']
 assert len(retry.json['data']['moves'])==3
 values['items'][0]['qty']=9;assert client.post(prefix+'/api/deliveries',json=values,headers=h).status_code==409
 detail=client.get(prefix+'/api/deliveries/'+row['id']).json['delivery'];assert detail['actorName']=='Test Majitel' and len(detail['items'])==3
 image=client.get(prefix+'/api/deliveries/'+row['id']+'/photos/'+attachment['id']);assert image.status_code==200 and image.headers['Content-Type']=='image/jpeg' and 'no-store' in image.headers['Cache-Control']
 assert app.test_client().get(prefix+'/api/deliveries/'+row['id']+'/photos/'+attachment['id']).status_code==401
 current=client.get(prefix+'/api/stock').json;current['data']['products'][0]['name']='Přejmenovaný produkt';assert client.put(prefix+'/api/stock',json=current,headers=h).status_code==200
 assert client.get(prefix+'/api/deliveries/'+row['id']).json['delivery']['items'][0]['name']=='Lahev'

def test_receipt_validation_rolls_back_all_stores_and_photos(hub):
 client,venue,prefix,h,products=setup(hub);before=client.get(prefix+'/api/stock').json
 bad=[{'product':p['id'],'store':p['store'],'qty':2} for p in products];bad[-1]['store']='missing'
 response,values=receive(client,prefix,h,products,items=bad,photos=[photo()]);assert response.status_code==403,response.json
 assert client.get(prefix+'/api/stock').json['revision']==before['revision'] and client.get(prefix+'/api/deliveries').json['total']==0
 response,values=receive(client,prefix,h,products,photos=[{**photo(),'image':'data:image/jpeg;base64,ZmFrZQ=='}]);assert response.status_code==400
 response,values=receive(client,prefix,h,products,revision=0);assert response.status_code==409
 assert client.get(prefix+'/api/deliveries').json['total']==0

def test_history_search_filters_scope_and_separate_invoice_permissions(hub):
 client,venue,prefix,h,products=setup(hub);response,values=receive(client,prefix,h,products);assert response.status_code==201
 assert client.get(prefix+'/api/deliveries?q=mouka').json['total']==1
 assert client.get(prefix+'/api/deliveries?store=kitchen&supplier=Velkoobchod+Alfa').json['total']==1
 assert client.get(prefix+'/api/deliveries?q=nikde').json['total']==0
 assert client.get(prefix+'/api/deliveries?from=2020-01-01&to=2021-01-01').json['total']==0
 assert client.get(prefix+'/api/deliveries?from=invalid').status_code==400
 employee,eh,user=staff(hub,venue,permissions={'deliveries.view':False})
 assert employee.get(prefix+'/api/deliveries').status_code==403
 assert employee.get(prefix+'/api/deliveries/'+values['id']).status_code==403
 assert employee.post(prefix+'/api/deliveries/'+values['id']+'/photos',json=photo(),headers=eh).status_code==403
 limited,lh,lu=staff(hub,venue,pin='3579')
 assert client.put(prefix+'/api/admin/users/'+lu['id']+'/work-access',json={'pin':'3579','allowedStores':['main']},headers=h).status_code==200
 assert limited.get(prefix+'/api/deliveries').json['total']==0
 assert limited.get(prefix+'/api/deliveries/'+values['id']).status_code==404
 assert receive(limited,prefix,lh,products)[0].status_code==403
 view,viewh,vu=staff(hub,venue,pin='4680',permissions={'stock.receive':False})
 assert view.get(prefix+'/api/deliveries').status_code==200
 assert view.post(prefix+'/api/deliveries/'+values['id']+'/photos',json=photo(),headers=viewh).status_code==403
 assert view.put(prefix+'/api/deliveries/'+values['id'],json={'supplier':'Oprava'},headers=viewh).status_code==405

def test_legacy_receipts_and_terminal_style_movements_join_history(hub):
 client,venue,prefix,h,products=setup(hub);doc=client.get(prefix+'/api/stock').json;p=products[0]
 from datetime import datetime,timezone
 doc['data']['moves'].append({'id':'old-receipt','deliveryId':'old-delivery','product':p['id'],'store':'main','qty':5,'reason':'Příjem','supplier':'Starý dodavatel','reference':'OLD-1','at':datetime.now(timezone.utc).isoformat()})
 assert client.put(prefix+'/api/stock',json=doc,headers=h).status_code==200
 result=client.get(prefix+'/api/deliveries').json;assert result['total']==1 and result['deliveries'][0]['legacy']
 id=result['deliveries'][0]['id'];assert client.post(prefix+'/api/deliveries/'+id+'/photos',json=photo(),headers=h).status_code==200
 assert client.get(prefix+'/api/deliveries').json['deliveries'][0]['photoCount']==1

def test_owner_consolidation_colors_and_tenant_boundaries(hub):
 client,venue,prefix,h,products=setup(hub);response,values=receive(client,prefix,h,products,photos=[photo()]);assert response.status_code==201
 other=create(hub,'Druhý provoz');pb,hb=enter(hub,other);p=product();assert add(client,pb,hb,p).status_code==201
 assert receive(client,pb,hb,[p])[0].status_code==201
 assert client.get(pb+'/api/deliveries/'+values['id']).status_code==404
 result=client.get('/api/owner/deliveries').json;assert result['total']==2 and len({r['venueId'] for r in result['deliveries']})==2 and len({r['color'] for r in result['deliveries']})==2
 assert client.get('/api/owner/deliveries?venue='+venue).json['total']==1
 assert client.get('/api/owner/deliveries?store='+venue+':main').json['total']==1
 assert client.put('/api/owner/venues/'+venue+'/delivery-color',json={'color':'#db2777'},headers=hub[1]).status_code==200
 assert client.get('/api/owner/deliveries?venue='+venue).json['deliveries'][0]['color']=='#db2777'
 detail=client.get('/api/owner/deliveries/'+venue+'/'+values['id']);assert detail.status_code==200,detail.json
 picture=detail.json['delivery']['photos'][0]['id'];assert client.get('/api/owner/deliveries/'+venue+'/'+values['id']+'/photos/'+picture).status_code==200
 assert client.post('/api/owner/deliveries/'+venue+'/'+values['id']+'/photos',json=photo(),headers=hub[1]).status_code==200
 employee,eh,user=staff(hub,venue);assert employee.get('/api/owner/deliveries').status_code==401
 assert client.get('/api/owner/deliveries?venue='+str(uuid.uuid4())).status_code==404
 assert client.put('/api/owner/venues/'+str(uuid.uuid4())+'/delivery-color',json={'color':'#112233'},headers=hub[1]).status_code==404

def test_transfer_removes_stock_adds_full_bar_bottles_once_and_audits(hub):
 client,venue,prefix,h,p=prepare_liquor(hub);values={'id':str(uuid.uuid4()),'revision':client.get(prefix+'/api/stock').json['revision'],'store':'main','product':p['id'],'bottles':2}
 response=client.post(prefix+'/api/stock/to-bar',json=values,headers=h);assert response.status_code==200,response.json
 assert current_quantity(response.json['data'],p['id'],'main')==3
 rows=client.get(prefix+'/api/me').json['state']['rows'];assert len(rows)==2 and all(r['ml']==500 and r['capacity']==500 for r in rows)
 retry=client.post(prefix+'/api/stock/to-bar',json=values,headers=h);assert retry.status_code==200 and retry.json['duplicate']
 assert len(client.get(prefix+'/api/me').json['state']['rows'])==2
 result=close(client,prefix,h,bar_run(rows));assert result.status_code==200,result.json
 summary=result.json['data']['barInventories'][-1]['bottleSummary'][0]
 assert summary['totalBottles']==5 and summary['fullBottles']==5 and summary['consumedBottles']==0
 with db(central=True) as c:v=one(c,'SELECT * FROM allin_venues WHERE id=%s',(venue,))
 with app.test_request_context(),venue_context(v),db() as c:
  assert one(c,'SELECT COUNT(*) AS n FROM bar_stock_transfers')['n']==1
  assert one(c,'SELECT COUNT(*) AS n FROM bar_bottle_depletions')['n']==0
  assert one(c,"SELECT COUNT(*) AS n FROM events WHERE action='bottles_to_bar'")['n']==1

def test_bar_transfer_permissions_stale_balance_and_pack_units(hub):
 client,venue,prefix,h,p=prepare_liquor(hub)
 for bottles,status in [(6,400),(1.5,400),(0,400),(101,400)]:
  response=client.post(prefix+'/api/stock/to-bar',json={'id':str(uuid.uuid4()),'revision':client.get(prefix+'/api/stock').json['revision'],'store':'main','product':p['id'],'bottles':bottles},headers=h);assert response.status_code==status,response.json
 assert client.get(prefix+'/api/me').json['state'].get('rows',[])==[]
 employee,eh,user=staff(hub,venue,permissions={'stock.move':False})
 assert employee.post(prefix+'/api/stock/to-bar',json={},headers=eh).status_code==403
 pack=product(name='Balení 6 lahví',kind='liquid',catalogProductId='amundsen',catalogCapacityMl=500,capacity=.5,unit='balení',packSize=6)
 assert add(client,prefix,h,pack,1).status_code==201
 values={'id':str(uuid.uuid4()),'revision':client.get(prefix+'/api/stock').json['revision'],'store':'main','product':pack['id'],'bottles':1}
 result=client.post(prefix+'/api/stock/to-bar',json=values,headers=h);assert result.status_code==200,result.json
 assert abs(current_quantity(result.json['data'],pack['id'],'main')-5/6)<1e-9
 state=client.get(prefix+'/api/me').json['state'];assert len(state['rows'])==1
 # A full recount can represent the five remaining bottles as a partial pack.
 doc=client.get(prefix+'/api/stock').json;doc['data']['counts'].append({'id':str(uuid.uuid4()),'product':pack['id'],'store':'main','qty':5/6,'at':doc['data']['moves'][-1]['at']})
 assert client.put(prefix+'/api/stock',json=doc,headers=h).status_code==200
 stale=client.post(prefix+'/api/stock/to-bar',json={**values,'id':str(uuid.uuid4())},headers=h);assert stale.status_code==409

def test_employee_bar_transfer_auto_activates_bottle_without_pin(hub):
 client,venue,prefix,h,p=prepare_liquor(hub);employee,eh,user=staff(hub,venue)
 values={'id':str(uuid.uuid4()),'revision':employee.get(prefix+'/api/stock').json['revision'],'store':'main','product':p['id'],'bottles':1}
 response=employee.post(prefix+'/api/stock/to-bar',json=values,headers=eh);assert response.status_code==200,response.json
 me=employee.get(prefix+'/api/me').json;assert 'amundsen' in me['state']['unlocks'] and me['state']['rows'][0]['ml']==500
 assert client.get(prefix+'/api/me').json['state'].get('rows',[])==[]
 assert current_quantity(client.get(prefix+'/api/stock').json['data'],p['id'],'main')==4


def test_coowner_shares_delivery_colors_and_bar_stock(hub):
 from tests.test_coowners import add as add_owner
 client,venue,prefix,h,p=prepare_liquor(hub);other,values=add_owner(hub);account,ch,actor_id=other;cp,eh=enter(other,venue)
 assert account.put('/api/owner/venues/'+venue+'/delivery-color',json={'color':'#0f766e'},headers=ch).status_code==200
 result=account.post(cp+'/api/stock/to-bar',json={'id':str(uuid.uuid4()),'revision':account.get(cp+'/api/stock').json['revision'],'store':'main','product':p['id'],'bottles':1},headers=eh)
 assert result.status_code==200,result.json
 assert client.get(prefix+'/api/me').json['state']['rows'][0]['ml']==500
 assert result.json['transfer']['actorName']=='Jana Spolumajitelka'
 response,receipt=receive(account,cp,eh,[p]);assert response.status_code==201,response.json
 assert client.get('/api/owner/deliveries').json['deliveries'][0]['color']=='#0f766e'
 assert client.get('/api/owner/deliveries').json['deliveries'][0]['actorId']==actor_id
