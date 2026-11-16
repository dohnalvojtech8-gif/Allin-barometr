"""Employee entry, venue role presets, individual exceptions and immutable history."""
import copy
import json
from tests.test_allin import hub,create,enter
from tests.test_employees import profile
import uuid
from server.app import app,db,one,allrows,execute,PRODUCTS
from server.allin import venue_context


def employee(hub,venue,**extra):
 client,h,_=hub;data={**profile(),**extra}
 response=client.post('/api/owner/venues/'+venue+'/members',json=data,headers=h)
 assert response.status_code==201,response.json
 return data,response.json['user']


def staff_client():
 client=app.test_client();client.environ_base['REMOTE_ADDR']='test-staff-'+uuid.uuid4().hex
 return client


def sign_in(data,venue=None):
 client=staff_client();response=client.post(('/v/'+venue if venue else '')+'/api/login',json={'username':data['username'],'password':data['password']})
 assert response.status_code==200,response.json
 return client,response


def test_main_login_routes_existing_staff_without_central_access(hub):
 client,h,_=hub;venue=create(hub,'Hlavní přihlášení');data,user=employee(hub,venue)
 staff,response=sign_in(data);prefix='/v/'+venue
 assert response.json['url']==prefix+'/'
 assert staff.get(prefix+'/api/me').json['user']['id']==user['id']
 assert staff.get('/api/me').status_code==401
 assert staff.get('/api/owner/venues').status_code==401
 assert staff.get(prefix+'/api/stock').status_code==200
 assert staff_client().post('/api/login',json={'username':data['username'],'password':'bad-password'}).status_code==401
 assert client.post('/api/owner/venues/'+venue+'/members/'+user['id'],json={'status':'suspended'},headers=h).status_code==200
 assert staff.get(prefix+'/api/me').status_code==401
 assert staff_client().post('/api/login',json={'username':data['username'],'password':data['password']}).status_code==401


def test_same_credentials_only_offer_verified_venues(hub):
 a=create(hub,'První');b=create(hub,'Druhý');c=create(hub,'Skrytý');data,_=employee(hub,a)
 employee(hub,b,**data);employee(hub,c,**{**data,'password':'another-test-password'})
 staff=staff_client();response=staff.post('/api/login',json=data)
 assert response.status_code==409,response.json
 assert {v['id'] for v in response.json['venues']}=={a,b}
 assert staff.get('/v/'+a+'/api/me').status_code==401
 response=staff.post('/api/login',json={**data,'venueId':b})
 assert response.status_code==200 and response.json['url']=='/v/'+b+'/'
 assert staff.get('/v/'+b+'/api/me').status_code==200
 assert staff.get('/v/'+a+'/api/me').status_code==401


def test_position_inheritance_exceptions_and_tenant_boundary(hub):
 client,h,_=hub;a=create(hub,'Pozice');b=create(hub,'Jiný provoz');url='/api/owner/venues/'+a+'/positions'
 result=client.get(url);assert result.status_code==200
 assert {'kuchar','cisnik','manager'} <= {p['id'] for p in result.json['positions']}
 preset={**result.json['defaults'],'stock.receive':False,'inventory.warehouse':False}
 made=client.post(url,json={'name':'Šéfkuchař','permissions':preset},headers=h)
 assert made.status_code==200,made.json
 position=next(p for p in made.json['positions'] if p['name']=='Šéfkuchař')
 data,user=employee(hub,a,positionId=position['id'])
 exception,custom=employee(hub,a,pin='4321',positionId=position['id'],permissions={**preset,'stock.receive':True})
 assert user['positionName']=='Šéfkuchař' and not user['permissions']['stock.receive']
 assert custom['permissions']['stock.receive']
 denied=client.post('/api/owner/venues/'+b+'/members',json={**profile(),'positionId':position['id']},headers=h)
 assert denied.status_code==404
 staff,_=sign_in(data)
 changed={**preset,'catalog.view':False,'inventory.bar':False,'inventory.adjust':True,'stock.receive':True}
 assert client.put(url+'/'+position['id'],json={'name':'Šéfkuchař','permissions':changed},headers=h).status_code==200
 assert staff.get('/v/'+a+'/api/me').status_code==401
 staff,_=sign_in(data);me=staff.get('/v/'+a+'/api/me').json
 assert me['user']['permissions']['stock.receive'] and not me['user']['permissions']['catalog.view']
 assert not me['user']['permissions']['inventory.adjust']
 assert staff.get('/v/'+a+'/api/admin/positions').status_code==403
 assert staff.get('/v/'+a+'/api/catalog').status_code==403
 assert staff.get('/v/'+a+'/api/shop').status_code==403
 assert staff.put('/v/'+a+'/api/state',json={'inventoryPlan':{'entries':[],'runId':'new'}},headers={'X-CSRF-Token':me['csrf']}).status_code==403
 # The exception survives a later preset change in the opposite direction.
 assert client.put(url+'/'+position['id'],json={'name':'Šéfkuchař','permissions':preset},headers=h).status_code==200
 custom_client,_=sign_in(exception)
 assert custom_client.get('/v/'+a+'/api/me').json['user']['permissions']['stock.receive']


def test_stock_inventory_needs_no_pin_and_history_cannot_be_rewritten(hub):
 client,h,owner=hub;venue=create(hub,'Evidence');prefix,vh=enter(hub,venue);data,user=employee(hub,venue)
 document={'stores':[{'id':'main','name':'Sklad'}],'products':[{'id':'p','name':'Zboží','store':'main','unit':'ks','kind':'piece','cost':0,'min':0,'tare':0,'capacity':0,'density':1,'category':'Zboží'}],'counts':[],'moves':[],'draft':None,'barInventories':[]}
 result=client.put(prefix+'/api/stock',json={'revision':0,'data':document},headers=vh);assert result.status_code==200,result.json
 staff,_=sign_in(data);me=staff.get(prefix+'/api/me').json;sh={'X-CSRF-Token':me['csrf']}
 current=staff.get(prefix+'/api/stock').json;document=current['data']
 document['counts'].append({'id':'count','inventoryId':'inv','product':'p','store':'main','qty':10,'at':'2026-01-01T10:00:00+00:00','actorId':owner,'actorName':'fake'})
 result=staff.put(prefix+'/api/stock',json={'revision':current['revision'],'data':document},headers=sh)
 assert result.status_code==200,result.json
 row=result.json['data']['counts'][0]
 assert row['actorId']==user['id'] and row['actorName']=='Tereza Nováková'
 assert row['at']!='2026-01-01T10:00:00+00:00'
 document=result.json['data'];revision=result.json['revision']
 for mutate in [lambda d:d['counts'][0].update(qty=2),lambda d:d['counts'].clear()]:
  altered=copy.deepcopy(document);mutate(altered)
  assert staff.put(prefix+'/api/stock',json={'revision':revision,'data':altered},headers=sh).status_code==403
 altered=copy.deepcopy(document);altered['counts'][0]['qty']=9
 assert client.put(prefix+'/api/stock',json={'revision':revision,'data':altered},headers=vh).status_code==200
 current=staff.get(prefix+'/api/stock').json
 current['data']['moves'].append({'id':'delivery','store':'main','product':'p','qty':2,'reason':'Příjem','at':'2026-01-01T10:00:00+00:00'})
 current['data']['barInventories'].append({'id':'bar','at':'2026-01-01T10:00:00+00:00','items':[{'name':'Lahev','qty':1,'unit':'l'}]})
 saved=staff.put(prefix+'/api/stock',json={'revision':current['revision'],'data':current['data']},headers=sh)
 assert saved.status_code==200,saved.json
 for key in ('moves','barInventories'):
  assert saved.json['data'][key][0]['actorId']==user['id']
  changed=copy.deepcopy(saved.json['data']);changed[key].clear()
  assert staff.put(prefix+'/api/stock',json={'revision':saved.json['revision'],'data':changed},headers=sh).status_code==403
 with db(central=True) as c:record=one(c,'SELECT * FROM allin_venues WHERE id=%s',(venue,))
 with app.test_request_context(),venue_context(record),db() as c:
  assert one(c,'SELECT actor_id FROM stock_change_log WHERE entity_id=%s AND revision=%s',('count',revision))['actor_id']==user['id']
 # Even a legacy stored history permission cannot grant an employee owner powers.
  execute(c,'UPDATE users SET permissions_json=%s WHERE id=%s',(json.dumps({'inventory.adjust':True}),user['id']))
  assert allrows(c,"SELECT * FROM events WHERE user_id=%s AND action='stock_saved'",(user['id'],))
 current=staff.get(prefix+'/api/stock').json;current['data']['counts'].clear()
 assert staff.put(prefix+'/api/stock',json={'revision':current['revision'],'data':current['data']},headers=sh).status_code==403


def test_bottle_history_server_author_and_append_only(hub):
 client,h,_=hub;venue=create(hub,'Měření');prefix,vh=enter(hub,venue);data,user=employee(hub,venue)
 staff,_=sign_in(data);me=staff.get(prefix+'/api/me').json;sh={'X-CSRF-Token':me['csrf']};pid=next(iter(PRODUCTS))
 assert staff.post(prefix+'/api/unlocks',json={'productId':pid},headers=sh).status_code==200
 value={'records':[{'productId':pid,'ml':100,'at':1,'actorName':'fake'}],'rows':[]}
 assert staff.put(prefix+'/api/state',json=value,headers=sh).status_code==200
 state=staff.get(prefix+'/api/me').json['state'];record=state['records'][0]
 assert record['actorId']==user['id'] and record['actorName']=='Tereza Nováková' and record['at']>1
 assert staff.put(prefix+'/api/state',json={'records':[]},headers=sh).status_code==403
 record['ml']=20
 assert staff.put(prefix+'/api/state',json={'records':[record]},headers=sh).status_code==403
