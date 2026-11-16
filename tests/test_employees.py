import json
import secrets
import time
import uuid
import pytest
from tests.test_allin import hub, create, enter
from server.app import app, db, one, allrows, execute, password_hash, password_ok, digest
from server.allin import venue_context


def profile(username=None, pin='1234'):
 return {'firstName':'Tereza','lastName':'Nováková','username':username or 'team_'+uuid.uuid4().hex[:12],
         'password':'employee-test-password','pin':pin}


def test_create_login_and_terminal_without_invitation(hub):
 client,h,owner=hub;venue_id=create(hub,'Profily');prefix,vh=enter(hub,venue_id)
 data=profile();url='/api/owner/venues/'+venue_id+'/members'
 response=client.post(url,json={**data,'role':'admin','permissions':{'users.manage':True}},headers=h)
 assert response.status_code==201,response.json
 user=response.json['user'];uid=user['id']
 assert user['role']=='user' and user['stockOwnerId']==owner and not user['permissions']['users.manage']
 assert response.json['hasPin'] and response.json['venueUrl']==prefix+'/'
 assert client.get('/api/me').json['user']['id']==owner
 assert client.get(prefix+'/api/me').json['user']['id']==owner
 with db(central=True) as c:venue=one(c,'SELECT * FROM allin_venues WHERE id=%s',(venue_id,))
 with app.test_request_context(),venue_context(venue),db() as c:
  account=one(c,'SELECT * FROM users WHERE id=%s',(uid,));access=one(c,'SELECT * FROM work_access WHERE user_id=%s',(uid,))
  assert account['password_hash']!=data['password'] and password_ok(data['password'],account['password_hash'])
  assert access['pin_hash']!=data['pin'] and password_ok(data['pin'],access['pin_hash'])
  assert access['owner_id']==owner and access['stores_json']=='null'
  events=allrows(c,"SELECT * FROM events WHERE action='employee_created'")
  assert len(events)==1 and events[0]['user_id']==owner
  assert not one(c,'SELECT id FROM invitation_uses WHERE user_id=%s',(uid,))
  assert events[0]['detail']=='Vytvoření zaměstnaneckého profilu: '+data['username']
 assert not {'password','pin','password_hash','pin_hash'} & response.json.keys()
 assert not {'password','pin','password_hash','pin_hash'} & user.keys()
 staff=app.test_client();login=staff.post(prefix+'/api/login',json={'username':data['username'],'password':data['password']})
 assert login.status_code==200,login.json
 me=staff.get(prefix+'/api/me').json
 assert me['user']['id']==uid and staff.get(prefix+'/api/stock').status_code==200
 assert staff.post(prefix+'/api/admin/users',json=profile(pin='4321'),headers={'X-CSRF-Token':me['csrf']}).status_code==403
 assert staff.get(prefix+'/api/owner/pos').status_code==403
 assert client.put(prefix+'/api/admin/users/'+owner+'/work-access',json={'pin':'9999','allowedStores':None},headers=vh).status_code==200
 assert client.post(prefix+'/api/work/device',json={},headers=vh).status_code==200
 gate=client.get(prefix+'/api/work/session').json
 assert client.post(prefix+'/api/work/login',json={'pin':data['pin']},headers={'X-CSRF-Token':gate['csrf']}).status_code==200
 session=client.get(prefix+'/api/work/session').json
 assert session['isOwner'] is False and session['name']=='Tereza Nováková'
 assert client.get(prefix+'/api/work/stock').status_code==200


def test_atomic_validation_and_case_insensitive_duplicates(hub):
 client,h,owner=hub;venue_id=create(hub,'Validace');prefix,vh=enter(hub,venue_id)
 data=profile();url=prefix+'/api/admin/users'
 assert client.post(url,json=data,headers=vh).status_code==201
 count=lambda:len(client.get(prefix+'/api/admin/users').json['users'])
 baseline=count()
 for field,bad in [('firstName',''),('lastName',''),('username','two words'),('password','short'),('pin','123'),('pin','１２３４'),('pin',1234),('pin',None)]:
  values=profile(pin='4321');values[field]=bad
  assert client.post(url,json=values,headers=vh).status_code==400,(field,bad)
  assert count()==baseline
 assert client.post(url,json=profile(username=data['username'].upper(),pin='4321'),headers=vh).status_code==409
 assert client.post(url,json=profile(pin=data['pin']),headers=vh).status_code==409
 assert count()==baseline
 assert client.post(url,json=profile(pin='4321')).status_code==403
 assert app.test_client().post('/api/owner/venues/'+venue_id+'/members',json=profile()).status_code==401
 # Independent venues may use the same credentials without sharing any user records.
 other=create(hub,'Samostatný profil');response=client.post('/api/owner/venues/'+other+'/members',json=data,headers=h)
 assert response.status_code==201 and response.json['user']['id']!=client.get(prefix+'/api/admin/users').json['users'][0]['id']


def test_other_owner_and_delegated_manager_cannot_create_profiles(hub):
 client,h,owner=hub;venue_id=create(hub,'Oprávnění');prefix,vh=enter(hub,venue_id)
 token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24);other=str(uuid.uuid4())
 with db(central=True) as c:
  execute(c,"INSERT INTO users (id,username,username_key,first_name,last_name,password_hash,role,created_at) VALUES (%s,%s,%s,'Other','Owner',%s,'admin',%s)",(other,other,other,password_hash('other-owner-password'),time.time()))
  execute(c,'INSERT INTO sessions (token_hash,user_id,csrf,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)',(digest(token),other,csrf,time.time(),time.time()+86400))
 stranger=app.test_client();stranger.set_cookie('barometr_session',token)
 assert stranger.post('/api/owner/venues/'+venue_id+'/members',json=profile(),headers={'X-CSRF-Token':csrf}).status_code==404
 data=profile();created=client.post(prefix+'/api/admin/users',json=data,headers=vh).json['user']
 perms=created['permissions'];perms['users.manage']=True
 assert client.post('/api/owner/venues/'+venue_id+'/members/'+created['id'],json={'permissions':perms},headers=h).status_code==200
 manager=app.test_client();manager.post(prefix+'/api/login',json={'username':data['username'],'password':data['password']})
 csrf=manager.get(prefix+'/api/me').json['csrf']
 assert manager.get(prefix+'/api/admin/users').status_code==200
 assert manager.post(prefix+'/api/admin/users',json=profile(pin='4321'),headers={'X-CSRF-Token':csrf}).status_code==403
 assert client.post('/api/owner/venues/'+venue_id+'/members',json=profile(pin='4321'),headers={**h,'Origin':'https://evil.example'}).status_code==403
