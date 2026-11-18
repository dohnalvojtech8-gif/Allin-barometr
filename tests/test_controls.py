import copy
import json
import secrets
import time
import uuid
from datetime import datetime,timedelta,timezone
import pytest
from tests.test_allin import hub,create,enter
from tests.test_employees import profile
from server.app import app,db,one,execute,password_hash,digest
from server.controls import validate_hours,validate_limits,within_hours,detect
from server.stock import at_minimum,low_stock,validate_stock


def hours(closed=True):
 return {'timezone':'Europe/Prague','days':{str(i):{'closed':closed,'open':'10:00','close':'22:00'} for i in range(7)}}


def document():
 return {'stores':[{'id':'s','name':'Bar'},{'id':'other','name':'Sklep'}], 'products':[{'id':'p','store':'s','name':'Sklenice','category':'Obaly','kind':'piece','unit':'ks','cost':20,'min':5,'minEnabled':True,'tare':0,'capacity':0,'density':1}], 'counts':[{'id':'c','product':'p','store':'s','qty':20,'at':(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()}], 'moves':[], 'draft':None,'barInventories':[]}


def save(client,prefix,headers,data):
 current=client.get(prefix+'/api/stock').json
 return client.put(prefix+'/api/stock',json={'revision':current['revision'],'data':data},headers=headers)


def test_minimum_boundary_optional_zero_unknown_and_archived():
 p=document()['products'][0]
 assert at_minimum(p,5) and at_minimum(p,4) and not at_minimum(p,6) and not at_minimum(p,None)
 assert not at_minimum({**p,'minEnabled':False},0)
 assert at_minimum({**p,'min':0,'minEnabled':True},0)
 assert not at_minimum({k:v for k,v in {**p,'min':0}.items() if k!='minEnabled'},0)
 data=document();data['counts'][0]['qty']=5;assert len(low_stock(data))==1
 data['stores'][0]['archivedAt']=datetime.now(timezone.utc).isoformat();assert low_stock(data)==[]
 data=document();data['products'][0].pop('min');data['products'][0].pop('minEnabled');clean=validate_stock(data);assert not at_minimum(clean['products'][0],0)
 for bad in (-1,True,float('inf')):
  data=document();data['products'][0]['min']=bad
  with pytest.raises(ValueError):validate_stock(data)


def test_opening_hours_handles_midnight_closed_days_and_validation():
 schedule=hours();schedule['days']['0']={'closed':False,'open':'20:00','close':'02:00'};schedule=validate_hours(schedule)
 # Monday evening and Tuesday early morning belong to Monday's overnight shift.
 moment=lambda s:datetime.fromisoformat(s).timestamp()
 assert within_hours(moment('2026-11-16T21:00:00+01:00'),schedule)
 assert within_hours(moment('2026-11-17T01:59:00+01:00'),schedule)
 assert not within_hours(moment('2026-11-17T02:00:00+01:00'),schedule)
 assert not within_hours(moment('2026-11-16T19:59:00+01:00'),schedule)
 assert within_hours(time.time(),{}) is None
 for mutation in (lambda h:h['days']['0'].update(closed=False,open='25:00'),lambda h:h['days'].pop('1'),lambda h:h.update(timezone='Not/AZone')):
  h=hours();mutation(h)
  with pytest.raises(ValueError):validate_hours(h)
 for bad in ({'outsideHours':1},{'lossPercent':float('nan')},{'repeatedCount':1},{'movementLimits':{'unknown':3}}):
  with pytest.raises(ValueError):validate_limits(bad)


def test_owner_controls_low_stock_and_case_resolution_is_scoped(hub):
 client,headers,_=hub;vid=create(hub,'Kontrolovaný bar');prefix,vh=enter(hub,vid);data=document()
 assert save(client,prefix,vh,data).status_code==200
 url='/api/owner/venues/'+vid+'/controls';response=client.put(url,json={'openingHours':hours(),'limits':{'movementLimits':{'ks':10}}},headers=headers)
 assert response.status_code==200,response.json
 assert response.json['openingHours']['days']['0']['closed']
 data=client.get(prefix+'/api/stock').json['data'];data['moves'].append({'id':'w1','product':'p','store':'s','qty':-15,'reason':'Odpis','note':'Rozbité sklenice','at':datetime.now(timezone.utc).isoformat()})
 assert save(client,prefix,vh,data).status_code==200
 venue=next(v for v in client.get('/api/owner/venues').json['venues'] if v['id']==vid)
 assert venue['belowMinimum']==1 and venue['lowStock'][0]['quantity']==5 and venue['lowStock'][0]['minimum']==5
 alerts=client.get('/api/owner/attention').json['alerts'];case=next(a for a in alerts if a['venueId']==vid and a['type']=='large_writeoff')
 assert any(a['type']=='outside_hours' for a in alerts) and case['actorName'] and case['evidenceIds']==['w1']
 action='/api/owner/venues/'+vid+'/attention/'+case['id']
 assert client.post(action,json={'resolved':True,'note':'Dodací obaly poškozené'},headers=headers).status_code==200
 saved=next(a for a in client.get('/api/owner/attention').json['alerts'] if a['id']==case['id'])
 assert saved['resolved'] and len(saved['history'])==1 and saved['note']=='Dodací obaly poškozené'
 assert client.post(action,json={'resolved':False,'note':'Je nutné doplnit podklady'},headers=headers).status_code==200
 saved=next(a for a in client.get('/api/owner/attention').json['alerts'] if a['id']==case['id']);assert not saved['resolved'] and len(saved['history'])==2
 assert client.post(action,json={'resolved':True,'note':'x'},headers=headers).status_code==400
 assert app.test_client().get('/api/owner/attention').status_code==401
 assert client.put(url,json={'openingHours':{'days':{}}},headers=headers).status_code==400
 assert client.put(url,json={}).status_code==403
 # A different central owner never sees or resolves another owner's cases.
 token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24);other=str(uuid.uuid4())
 with db(central=True) as c:
  execute(c,"INSERT INTO users (id,username,username_key,first_name,last_name,password_hash,role,created_at) VALUES (%s,%s,%s,'Other','Owner',%s,'admin',%s)",(other,other,other,password_hash('other-owner-password'),time.time()))
  execute(c,'INSERT INTO sessions (token_hash,user_id,csrf,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)',(digest(token),other,csrf,time.time(),time.time()+86400))
 stranger=app.test_client();stranger.set_cookie('barometr_session',token);oh={'X-CSRF-Token':csrf}
 assert stranger.get('/api/owner/attention').json['alerts']==[]
 assert stranger.put(url,json={},headers=oh).status_code==404
 assert stranger.post(action,json={'resolved':True,'note':'Pokus o cizí změnu'},headers=oh).status_code==404


def test_writeoff_is_separate_capability_and_cannot_be_forged(hub):
 client,h,_=hub;vid=create(hub,'Odpisy');prefix,vh=enter(hub,vid);assert save(client,prefix,vh,document()).status_code==200
 user=profile();created=client.post('/api/owner/venues/'+vid+'/members',json=user,headers=h).json['user']
 staff=app.test_client()
 def login():
  assert staff.post(prefix+'/api/login',json={'username':user['username'],'password':user['password']}).status_code==200
  return {'X-CSRF-Token':staff.get(prefix+'/api/me').json['csrf']}
 sh=login();data=staff.get(prefix+'/api/stock').json['data'];data['moves'].append({'id':'w2','product':'p','store':'s','qty':-15,'reason':'Odpis','note':'Poškozené sklenice','at':datetime.now(timezone.utc).isoformat()})
 assert save(staff,prefix,sh,data).status_code==403
 permissions={**created['permissions'],'stock.writeoff':True,'stock.move':False}
 assert client.post('/api/owner/venues/'+vid+'/members/'+created['id'],json={'permissions':permissions},headers=h).status_code==200
 sh=login();assert save(staff,prefix,sh,data).status_code==200
 saved=staff.get(prefix+'/api/stock').json['data'];record=saved['moves'][0]
 assert record['actorId']==created['id'] and record['note']=='Poškozené sklenice'
 for reason,note,qty,status in [('Výdej','',-1,403),('Odpis','',-1,400),('Odpis','Chybné kladné množství',1,400)]:
  attempt=copy.deepcopy(saved);attempt['moves'].append({'id':str(uuid.uuid4()),'store':'s','product':'p','reason':reason,'note':note,'qty':qty,'at':datetime.now(timezone.utc).isoformat()})
  assert save(staff,prefix,sh,attempt).status_code==status
 assert staff.get('/api/owner/attention').status_code==401


def test_detection_has_evidence_respects_limits_and_ignores_missing_baseline():
 data=document();now=time.time()
 for i in range(3):data['moves'].append({'id':'w'+str(i),'store':'s','product':'p','qty':-1,'reason':'Odpis','note':'Rozbité zboží','actorName':'Test','recordedAt':now-i*60,'at':datetime.fromtimestamp(now-i*60,timezone.utc).isoformat()})
 result=detect(data,limits={'movementLimits':{'ks':100}},now=now)
 assert any(a['type']=='repeated_writeoff' and len(a['evidenceIds'])==3 for a in result)
 assert not any(a['type'] in ('large_writeoff','inventory_difference','outside_hours') for a in result)
 assert not any(a['type']=='repeated_writeoff' for a in detect(data,limits={'repeatedCount':4},now=now))
 data['counts'].append({'id':'c2','store':'s','product':'p','qty':1,'expected':17,'unit':'ks','at':datetime.fromtimestamp(now,timezone.utc).isoformat()})
 assert any(a['type']=='inventory_difference' for a in detect(data,now=now))


def test_terminal_writeoff_requires_permission_reason_and_is_idempotent(hub):
 client,h,owner=hub;vid=create(hub,'Terminál odpisy');prefix,vh=enter(hub,vid)
 assert save(client,prefix,vh,document()).status_code==200
 values={**profile(),'permissions':{'stock.move':False,'stock.writeoff':True}}
 employee=client.post('/api/owner/venues/'+vid+'/members',json=values,headers=h).json['user']
 assert client.put(prefix+'/api/admin/users/'+owner+'/work-access',json={'pin':'9999','allowedStores':None},headers=vh).status_code==200
 assert client.post(prefix+'/api/work/device',json={},headers=vh).status_code==200
 def pin_login():
  gate=client.get(prefix+'/api/work/session').json
  assert client.post(prefix+'/api/work/login',json={'pin':values['pin']},headers={'X-CSRF-Token':gate['csrf']}).status_code==200
  return {'X-CSRF-Token':client.get(prefix+'/api/work/session').json['csrf']}
 wh=pin_login();stock=client.get(prefix+'/api/work/stock').json
 data={'store':'s','product':'p','qty':2,'reason':'Odpis','note':'Rozbitý výrobek','operationId':str(uuid.uuid4()),'revision':stock['revision']}
 assert client.post(prefix+'/api/work/move',json={**data,'reason':'Výdej'},headers=wh).status_code==403
 assert client.post(prefix+'/api/work/move',json={**data,'note':''},headers=wh).status_code==400
 assert client.post(prefix+'/api/work/move',json=data,headers=wh).status_code==200
 assert client.post(prefix+'/api/work/move',json=data,headers=wh).json['duplicate']
 assert client.post(prefix+'/api/work/move',json={**data,'note':'Jiný důvod'},headers=wh).status_code==409
 assert client.get(prefix+'/api/work/stock').json['products'][0]['qty']==18
 assert client.post('/api/owner/venues/'+vid+'/members/'+employee['id'],json={'permissions':{**employee['permissions'],'stock.writeoff':False}},headers=h).status_code==200
 wh=pin_login();data['operationId']=str(uuid.uuid4());data['revision']=client.get(prefix+'/api/work/stock').json['revision']
 assert client.post(prefix+'/api/work/move',json=data,headers=wh).status_code==403
