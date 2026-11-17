"""Exercise the production routing boundary with two owners and independent venues."""
import json
import secrets
import time
import uuid
import pytest
from tests.test_accounts import app
from server.app import db,execute,one,password_hash,digest,PRODUCTS

@pytest.fixture
def hub(monkeypatch):
 monkeypatch.delenv('ALLIN_LEGACY_TEST_API',raising=False)
 client=app.test_client();id=str(uuid.uuid4());token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
 with db() as c:
  execute(c,"INSERT INTO users (id,username,username_key,first_name,last_name,password_hash,role,created_at) VALUES (%s,%s,%s,'Test','Majitel',%s,'admin',%s)",(id,id,id,password_hash('test-owner-password'),time.time()))
  execute(c,'INSERT INTO sessions (token_hash,user_id,csrf,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)',(digest(token),id,csrf,time.time(),time.time()+86400))
 client.set_cookie('barometr_session',token)
 return client,{'X-CSRF-Token':csrf},id

def create(hub,name):
 client,h,_=hub;r=client.post('/api/owner/venues',json={'name':name,'address':'Praha'},headers=h)
 assert r.status_code==201,r.json
 return r.json['venue']['id']

def enter(hub,venue):
 client,h,_=hub;r=client.post('/api/owner/venues/'+venue+'/enter',json={},headers=h)
 assert r.status_code==200,r.json
 assert r.json['url']=='/v/'+venue+'/'
 me=client.get('/v/'+venue+'/api/me');assert me.status_code==200,me.json
 return '/v/'+venue,{'X-CSRF-Token':me.json['csrf']}

def test_two_venues_isolate_stock_shop_photos_and_admins(hub):
 client,h,owner=hub;a=create(hub,'První bar');b=create(hub,'Druhý bar');pa,ha=enter(hub,a);pb,hb=enter(hub,b)
 assert client.get('/api/stock').status_code==403
 assert client.get(pa+'/api/owner/venues').status_code==403
 assert client.get('/v/'+str(uuid.uuid4())+'/api/me').status_code==404
 assert client.get(pa+'/').status_code==200
 assert b'owner.js' not in client.get(pa+'/').data
 assert b'owner.js' in client.get('/').data
 stock=client.get(pa+'/api/stock').json
 data={'stores':[{'id':'private','name':'Pouze první bar'}],'products':[],'counts':[],'moves':[],'draft':None,'barInventories':[]}
 assert client.put(pa+'/api/stock',json={'revision':stock['revision'],'data':data},headers=ha).status_code==200
 assert client.get(pb+'/api/stock').json['data']['stores'][0]['name']!='Pouze první bar'
 pid=next(iter(PRODUCTS))
 assert client.post(pa+'/api/unlocks',json={'productId':pid},headers=ha).status_code==200
 assert pid in client.get(pa+'/api/me').json['state']['unlocks']
 assert pid not in client.get(pb+'/api/me').json['state']['unlocks']
 assert client.get(pb+'/api/products/'+pid).status_code==403
 assert client.put(pa+'/api/scan-photos/private-photo',json={'image':'data:image/jpeg;base64,/9j/2Q=='},headers=ha).status_code==200
 assert client.get(pa+'/api/scan-photos/private-photo').status_code==200
 assert client.get(pb+'/api/scan-photos/private-photo').status_code==404
 assert len(client.get(pa+'/api/admin/users').json['users'])==1
 assert len(client.get(pb+'/api/admin/users').json['users'])==1
 # A valid session and CSRF token from A never authorize B.
 rogue=app.test_client();cookie=client.get_cookie('barometr_session_'+a,path=pa)
 rogue.set_cookie('barometr_session_'+b,cookie.value,path=pb)
 assert rogue.get(pb+'/api/me').status_code==401
 assert client.post(pb+'/api/unlocks',json={'productId':pid},headers=ha).status_code==403
 assert client.post(pa+'/api/logout',json={},headers=ha).status_code==200
 assert client.get(pa+'/api/me').status_code==401
 assert client.get(pb+'/api/me').status_code==200
 assert client.get('/api/me').status_code==200
 assert client.get(pb+'/manifest.webmanifest').json['start_url']==pb+'/'
 assert client.post('/api/logout',json={},headers=h).status_code==200
 assert client.get(pb+'/api/me').status_code==401


def test_owner_boundaries_staff_invites_and_revocation(hub):
 client,h,owner=hub;a=create(hub,'Tým A');b=create(hub,'Tým B');pa,ha=enter(hub,a);pb,hb=enter(hub,b)
 # Independent central owner cannot open this owner's venue.
 outsider=app.test_client();token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24);oid=str(uuid.uuid4())
 with db() as c:
  execute(c,"INSERT INTO users (id,username,username_key,first_name,last_name,password_hash,role,created_at) VALUES (%s,%s,%s,'Other','Owner',%s,'admin',%s)",(oid,oid,oid,password_hash('another-password'),time.time()))
  execute(c,'INSERT INTO sessions (token_hash,user_id,csrf,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)',(digest(token),oid,csrf,time.time(),time.time()+86400))
 outsider.set_cookie('barometr_session',token)
 assert outsider.get('/api/owner/venues').json['venues']==[]
 assert outsider.post('/api/owner/venues/'+a+'/enter',json={},headers={'X-CSRF-Token':csrf}).status_code==404
 assert outsider.get(pa+'/api/me').status_code==401
 invitation=client.post('/api/owner/venues/'+a+'/invites',json={'label':'Barman','days':7,'maxUses':1},headers=h)
 assert invitation.status_code==200,invitation.json
 staff=app.test_client();username='staff_'+uuid.uuid4().hex[:10]
 registration={'firstName':'Jan','lastName':'Barman','username':username,'password':'employee-password','inviteCode':invitation.json['code']}
 assert staff.post(pb+'/api/register',json=registration).status_code==400
 assert staff.post(pa+'/api/register',json=registration).status_code==200
 me=staff.get(pa+'/api/me').json;sid=me['user']['id'];sh={'X-CSRF-Token':me['csrf']}
 assert me['user']['stockOwnerId']==owner
 assert staff.get(pb+'/api/me').status_code==401
 assert staff.get('/api/me').status_code==401
 assert staff.get(pa+'/api/admin/users').status_code==403
 team=client.get('/api/owner/team').json['members']
 assert any(m['id']==sid and m['venueId']==a for m in team)
 assert not any(m['id']==sid and m['venueId']==b for m in team)
 assert client.post('/api/owner/venues/'+b+'/members/'+sid,json={'status':'suspended'},headers=h).status_code==404
 assert client.post('/api/owner/venues/'+a+'/members/'+sid,json={'status':'suspended'},headers=h).status_code==200
 assert staff.get(pa+'/api/me').status_code==401
 events=client.get('/api/owner/activity').json['events']
 assert any(e['venueId']==a and e['action']=='registered' for e in events)
 assert all(e['venueId'] in (a,b) for e in events)


def test_shared_terminal_remains_in_its_venue(hub):
 client,h,owner=hub;a=create(hub,'Terminál A');b=create(hub,'Terminál B');pa,ha=enter(hub,a);pb,hb=enter(hub,b)
 r=client.put(pa+'/api/admin/users/'+owner+'/work-access',json={'pin':'1234','allowedStores':None},headers=ha)
 assert r.status_code==200,r.json
 r=client.post(pa+'/api/work/device',json={},headers=ha);assert r.status_code==200,r.json
 assert client.get(pa+'/api/me').status_code==401
 assert client.get('/api/me').status_code==200
 status=client.get(pa+'/api/work/session');assert status.status_code==200,status.json
 assert client.get(pb+'/api/work/session').status_code==401
 assert client.post(pa+'/api/work/login',json={'pin':'1234'},headers={'X-CSRF-Token':status.json['csrf']}).status_code==200
 assert client.get(pa+'/api/work/stock').status_code==200
 assert client.get(pb+'/api/work/stock').status_code==401
 assert client.get(pb+'/api/me').status_code==200


def test_summary_uses_real_stock_and_latest_shortage(hub):
 client,h,owner=hub;a=create(hub,'Srovnání');pa,ha=enter(hub,a)
 product={'id':'p','name':'Lahev','store':'main','category':'Nápoje','unit':'ks','kind':'piece','cost':20,'min':9,'tare':0,'capacity':0,'density':1}
 data={'stores':[{'id':'main','name':'Hlavní sklad'}],'products':[product,{**product,'id':'unmeasured','name':'Nezměřeno'}],
 'counts':[{'id':'c1','inventoryId':'first','product':'p','store':'main','qty':10,'at':'2025-01-01T10:00:00+00:00'}],
 'moves':[],'draft':None,'barInventories':[]}
 assert client.put(pa+'/api/stock',json={'revision':0,'data':data},headers=ha).status_code==200
 first=next(v for v in client.get('/api/owner/venues').json['venues'] if v['id']==a)
 assert first['quantities']=={'ks':10} and first['unmeasuredPositions']==1
 assert first['latestShortage'] is None
 data['counts'].append({'id':'c2','inventoryId':'second','product':'p','store':'main','qty':8,'at':'2025-01-02T10:00:00+00:00'})
 assert client.put(pa+'/api/stock',json={'revision':1,'data':data},headers=ha).status_code==200
 second=next(v for v in client.get('/api/owner/venues').json['venues'] if v['id']==a)
 assert second['quantities']=={'ks':8} and second['latestShortage']=={'ks':2}
 assert second['inventories']==2 and second['belowMinimum']==1


def test_owner_password_can_change_from_each_venue(hub):
 client,h,owner=hub;a=create(hub,'Heslo A');b=create(hub,'Heslo B');pa,ha=enter(hub,a);pb,hb=enter(hub,b)
 assert client.post(pa+'/api/password',json={'oldPassword':'wrong','newPassword':'new-owner-password'},headers=ha).status_code==403
 assert client.post(pa+'/api/password',json={'oldPassword':'test-owner-password','newPassword':'owner-next-password'},headers=ha).status_code==200
 other=app.test_client()
 assert other.post('/api/login',json={'username':owner,'password':'test-owner-password'}).status_code==401
 assert other.post('/api/login',json={'username':owner,'password':'owner-next-password'}).status_code==200
 assert client.post(pb+'/api/password',json={'oldPassword':'owner-next-password','newPassword':'owner-last-password'},headers=hb).status_code==200
 assert other.get('/api/me').status_code==401
 assert client.get('/api/me').status_code==200
 assert client.post(pa+'/api/password',json={'oldPassword':'owner-last-password','newPassword':'4062'},headers=ha).status_code==200
 assert other.post('/api/login',json={'username':owner,'password':'4062'}).status_code==200


def test_summary_keeps_units_separate_and_omits_financial_fields(hub):
 client,h,owner=hub;a=create(hub,'Jednotky');pa,ha=enter(hub,a)
 base={'store':'main','category':'Zboží','cost':999,'min':0,'tare':0,'capacity':0,'density':1}
 products=[{**base,'id':'piece','name':'Kusy','kind':'piece','unit':'ks'},{**base,'id':'weight','name':'Hmotnost','kind':'weight','unit':'kg'}]
 counts=[{'id':'piece-count','inventoryId':'mixed','store':'main','product':'piece','qty':12,'at':'2025-01-01T12:00:00+00:00'},
 {'id':'weight-count','inventoryId':'mixed','store':'main','product':'weight','qty':2.5,'at':'2025-01-01T12:00:00+00:00'}]
 data={'stores':[{'id':'main','name':'Sklad'}],'products':products,'counts':counts,'moves':[],'draft':None,'barInventories':[]}
 assert client.put(pa+'/api/stock',json={'revision':0,'data':data},headers=ha).status_code==200
 summary=client.get('/api/owner/venues').json['venues'][0]
 assert summary['quantities']=={'ks':12,'kg':2.5}
 assert 'stockValue' not in summary and 'unpricedShortage' not in summary



def test_optional_venue_manager_and_owner_only_updates(hub):
 client,h,_=hub
 response=client.post('/api/owner/venues',json={'name':'S manažerem','managerFirstName':' Jana ','managerLastName':' Nováková '},headers=h)
 assert response.status_code==201,response.json
 venue=response.json['venue'];url='/api/owner/venues/'+venue['id']+'/manager'
 assert venue['manager_first_name']=='Jana' and venue['manager_last_name']=='Nováková'
 assert client.put(url,json={'managerFirstName':'Petr','managerLastName':'Dvořák'},headers=h).status_code==200
 row=next(v for v in client.get('/api/owner/venues').json['venues'] if v['id']==venue['id'])
 assert row['manager_first_name']=='Petr' and row['manager_last_name']=='Dvořák'
 for values in [{'managerFirstName':'Jana'},{'managerLastName':'Nováková'},{'managerFirstName':None},{'managerFirstName':'x'*65,'managerLastName':'Y'}]:
  assert client.put(url,json=values,headers=h).status_code==400
  assert client.post('/api/owner/venues',json={'name':'Neplatný',**values},headers=h).status_code==400
 assert client.put(url,json={},headers=h).status_code==200
 row=next(v for v in client.get('/api/owner/venues').json['venues'] if v['id']==venue['id'])
 assert row['manager_first_name']==row['manager_last_name']==''
 assert client.put(url,json={}).status_code==403
 assert app.test_client().put(url,json={}).status_code==401
 # An authenticated second owner cannot update a foreign venue.
 token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24);other=str(uuid.uuid4())
 with db(central=True) as c:
  execute(c,"INSERT INTO users (id,username,username_key,first_name,last_name,password_hash,role,created_at) VALUES (%s,%s,%s,'Other','Owner',%s,'admin',%s)",(other,other,other,password_hash('other-owner-password'),time.time()))
  execute(c,'INSERT INTO sessions (token_hash,user_id,csrf,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)',(digest(token),other,csrf,time.time(),time.time()+86400))
 stranger=app.test_client();stranger.set_cookie('barometr_session',token)
 assert stranger.put(url,json={'managerFirstName':'Foreign','managerLastName':'Owner'},headers={'X-CSRF-Token':csrf}).status_code==404
 plain=create(hub,'Bez manažera')
 row=next(v for v in client.get('/api/owner/venues').json['venues'] if v['id']==plain)
 assert row['manager_first_name']==row['manager_last_name']==''
