import copy
import secrets
import time
import uuid
import pytest
from tests.test_accounts import login,invite
from server.app import app,db,execute,one
from server.permissions import effective_permissions


def configure(manager,headers,uid,pin,stores=None):
 return manager.put('/api/admin/users/'+uid+'/work-access',json={'pin':pin,'allowedStores':stores},headers=headers)

def pin_login(client,pin):
 status=client.get('/api/work/session')
 assert status.status_code==200,status.json
 response=client.post('/api/work/login',json={'pin':pin},headers={'X-CSRF-Token':status.json['csrf']})
 if response.status_code==200:return {'X-CSRF-Token':client.get('/api/work/session').json['csrf']}
 return response

@pytest.fixture
def terminal():
 # Each fixture owns its rate-limit budget in the disposable test database.
 with db() as c:execute(c,'DELETE FROM rate_buckets')
 manager,headers=login();owner=manager.get('/api/me').json['user']['id']
 data={'stores':[{'id':'work-a','name':'Sklad A'},{'id':'work-b','name':'Soukromý sklad'}], 'products':[{'id':pid,'store':sid,'name':name,'category':'Zboží','unit':'ks','kind':'piece','cost':10,'min':2,'tare':0,'capacity':0,'density':1} for pid,sid,name in [('work-p1','work-a','Sklenice'),('work-p2','work-b','Tajná položka')]],'counts':[{'id':'work-c1','product':'work-p1','store':'work-a','qty':20,'at':'2026-01-01T12:00:00+00:00'},{'id':'work-c2','product':'work-p2','store':'work-b','qty':50,'at':'2026-01-01T12:00:00+00:00'}],'moves':[],'draft':None,'barInventories':[]}
 current=manager.get('/api/stock').json
 assert manager.put('/api/stock',json={'revision':current['revision'],'data':data},headers=headers).status_code==200
 code=invite(manager,headers)['code'];employee=app.test_client()
 assert employee.post('/api/register',json={'firstName':'Jana','lastName':'Skladová','username':'work_'+uuid.uuid4().hex[:12],'password':'employee-test-password','inviteCode':code}).status_code==200
 me=employee.get('/api/me').json;uid=me['user']['id'];eh={'X-CSRF-Token':me['csrf']}
 permissions=me['user']['permissions'];permissions['work.inventory']=False;permissions['stock.audit']=False
 assert manager.post('/api/admin/users/'+uid+'/permissions',json={'permissions':permissions,'stockOwnerId':owner},headers=headers).status_code==200
 for attempt in range(100):
  employee_pin=f'{secrets.randbelow(9000):04d}'
  if configure(manager,headers,uid,employee_pin,['work-a']).status_code==200:break
 else:raise AssertionError('Cannot assign test PIN')
 assert configure(manager,headers,owner,'9999').status_code==200
 device,dh=login();assert device.post('/api/work/device',json={},headers=dh).status_code==200
 return manager,headers,owner,employee,eh,uid,employee_pin,device,permissions


def test_pin_is_separate_from_account_and_owner_pin_keeps_terminal_running(terminal):
 m,h,owner,e,eh,uid,pin,d,perms=terminal
 assert d.get('/api/me').status_code==401
 assert d.get('/api/work/stock').status_code==401
 wh=pin_login(d,pin)
 assert isinstance(wh,dict)
 assert d.get('/api/me').status_code==401
 assert d.post('/api/work/leave',json={},headers=wh).status_code==403
 assert d.post('/api/work/lock',json={},headers=wh).status_code==200
 wh=pin_login(d,'9999')
 assert d.get('/api/work/session').json['isOwner'] is True
 assert d.get('/api/work/stock').status_code==200
 # Logging in as owner must never unpair the terminal.
 assert d.post('/api/work/lock',json={},headers=wh).status_code==200
 assert d.get('/api/work/session').json['locked'] is True
 assert isinstance(pin_login(d,pin),dict)


def test_pin_validation_unique_hashed_and_revocation(terminal):
 m,h,owner,e,eh,uid,pin,d,perms=terminal
 for invalid in ['123','12345','abcd',1234,'１２３４']:
  assert configure(m,h,uid,invalid).status_code==400
 assert configure(m,h,uid,'9999').status_code==400
 assert e.put('/api/admin/users/'+uid+'/work-access',json={'pin':'1234','allowedStores':None},headers=eh).status_code==403
 with db() as c:
  stored=one(c,'SELECT pin_hash FROM work_access WHERE user_id=%s',(uid,))['pin_hash']
 assert stored!=pin and stored.startswith('scrypt$')
 detail=m.get('/api/admin/users/'+uid+'/work-access').json
 assert detail['hasPin'] and 'pin_hash' not in detail and 'pin' not in detail
 wh=pin_login(d,pin)
 assert m.put('/api/admin/users/'+uid+'/work-access',json={'removePin':True,'allowedStores':['work-a']},headers=h).status_code==200
 assert d.get('/api/work/stock').status_code==401


def test_warehouse_scope_is_enforced_in_both_apps(terminal):
 m,h,owner,e,eh,uid,pin,d,perms=terminal
 wh=pin_login(d,pin);visible=d.get('/api/work/stock').json
 assert [s['id'] for s in visible['stores']]==['work-a']
 assert {p['id'] for p in visible['products']}=={'work-p1'}
 hidden={'reason':'Příjem','store':'work-b','product':'work-p2','qty':2,'operationId':str(uuid.uuid4()),'revision':visible['revision']}
 assert d.post('/api/work/move',json=hidden,headers=wh).status_code==403
 perms['stock.edit']=False
 assert m.post('/api/admin/users/'+uid+'/permissions',json={'permissions':perms,'stockOwnerId':owner},headers=h).status_code==200
 full=e.get('/api/stock').json
 assert [s['id'] for s in full['data']['stores']]==['work-a']
 saved=e.put('/api/stock',json={'revision':full['revision'],'data':full['data']},headers=eh)
 assert saved.status_code==200,saved.json
 assert len(m.get('/api/stock').json['data']['stores'])==2
 injected=copy.deepcopy(saved.json['data']);injected['stores'].append({'id':'work-b','name':'Forbidden'})
 assert e.put('/api/stock',json={'revision':saved.json['revision'],'data':injected},headers=eh).status_code==403
 assert e.get('/api/admin/stock-changes').status_code==403


def test_quick_issue_receipt_idempotency_conflicts_and_actor(terminal):
 m,h,owner,e,eh,uid,pin,d,perms=terminal
 wh=pin_login(d,pin);current=d.get('/api/work/stock').json
 move={'reason':'Výdej','store':'work-a','product':'work-p1','qty':3,'operationId':str(uuid.uuid4()),'revision':current['revision']}
 assert d.post('/api/work/move',json=move,headers=wh).status_code==200
 assert d.post('/api/work/move',json=move,headers=wh).json['duplicate'] is True
 assert d.get('/api/work/stock').json['products'][0]['qty']==17
 stale={**move,'operationId':str(uuid.uuid4())}
 assert d.post('/api/work/move',json=stale,headers=wh).status_code==409
 current=d.get('/api/work/stock').json
 impossible={**move,'revision':current['revision'],'operationId':str(uuid.uuid4()),'qty':100}
 assert d.post('/api/work/move',json=impossible,headers=wh).status_code==400
 impossible['qty']=-2
 assert d.post('/api/work/move',json=impossible,headers=wh).status_code==400
 receipt={**move,'revision':current['revision'],'operationId':str(uuid.uuid4()),'reason':'Příjem','qty':5}
 assert d.post('/api/work/move',json=receipt,headers=wh).status_code==200
 latest=m.get('/api/stock').json['latestChanges']['work-a|work-p1']
 assert latest['name']=='Jana Skladová' and latest['before']==17 and latest['after']==22
 # A PIN cannot be used to call the regular document API.
 assert d.put('/api/stock',json={'data':{}},headers=wh).status_code==401


def test_server_idle_timeout_and_csrf(terminal):
 m,h,owner,e,eh,uid,pin,d,perms=terminal
 assert d.post('/api/work/login',json={'pin':pin}).status_code==403
 wh=pin_login(d,pin)
 assert d.post('/api/work/touch',json={}).status_code==403
 assert d.post('/api/work/touch',json={},headers=wh).status_code==200
 with db() as c:execute(c,'UPDATE work_sessions SET last_activity=%s WHERE user_id=%s',(time.time()-301,uid))
 assert d.get('/api/work/stock').status_code==401
 assert d.post('/api/work/touch',json={},headers=wh).status_code==401
 assert d.get('/api/work/session').json['locked'] is True
 assert isinstance(pin_login(d,pin),dict)


def test_special_inventory_permission_and_shared_history(terminal):
 m,h,owner,e,eh,uid,pin,d,perms=terminal
 wh=pin_login(d,pin);current=d.get('/api/work/stock').json
 count={'store':'work-a','values':{'work-p1':13},'revision':current['revision'],'operationId':str(uuid.uuid4())}
 assert d.post('/api/work/inventory',json=count,headers=wh).status_code==403
 assert d.get('/api/work/changes').status_code==403
 perms.update({'work.inventory':True,'stock.audit':True})
 assert m.post('/api/admin/users/'+uid+'/permissions',json={'permissions':perms,'stockOwnerId':owner},headers=h).status_code==200
 assert d.post('/api/work/inventory',json=count,headers=wh).status_code==200
 assert d.post('/api/work/inventory',json=count,headers=wh).json['duplicate'] is True
 all_data=m.get('/api/stock').json['data']
 records=[r for r in all_data['counts'] if r.get('inventoryId')==count['operationId']]
 assert len(records)==1 and records[0]['expected']==20 and records[0]['qty']==13
 assert d.get('/api/work/stock').json['products'][0]['qty']==13
 changes=d.get('/api/work/changes').json['changes']
 assert any(r['name']=='Jana Skladová' and r['after']==13 for r in changes)
 assert all(r['store_name']!='Soukromý sklad' for r in changes)
 regular=e.get('/api/admin/stock-changes').json
 assert all(r['store_id']=='work-a' for r in regular['changes'])
 assert all(s['store_id']=='work-a' for s in regular['stores'])


def test_pin_attempt_limit_and_suspension(terminal):
 m,h,owner,e,eh,uid,pin,d,perms=terminal
 status=d.get('/api/work/session').json
 for i in range(8):
  r=d.post('/api/work/login',json={'pin':'not-a-pin'},headers={'X-CSRF-Token':status['csrf']})
  assert r.status_code==401,r.json
 assert d.post('/api/work/login',json={'pin':pin},headers={'X-CSRF-Token':status['csrf']}).status_code==429
 # Revoke attempts only in the disposable test DB, then test status checking.
 with db() as c:execute(c,'DELETE FROM rate_buckets')
 wh=pin_login(d,pin)
 assert m.post('/api/admin/users/'+uid+'/status',json={'status':'suspended'},headers=h).status_code==200
 assert d.get('/api/work/stock').status_code==401


def test_owner_can_explicitly_unpair_and_work_assets_are_public(terminal):
 m,h,owner,e,eh,uid,pin,d,perms=terminal
 wh=pin_login(d,'9999')
 assert d.post('/api/work/leave',json={},headers=wh).status_code==200
 assert d.get('/api/work/session').status_code==401
 for path in ['/work','/work.js','/work.css']:
  assert app.test_client().get(path).status_code==200


def test_scoped_roundtrip_preserves_shared_product_assignment_and_legacy_store_order():
 from server.work import scoped_stock,merge_scoped_stock
 data={'stores':[{'id':'a','name':'Dostupný'},{'id':'b','name':'Soukromý'}],'products':[{'id':'shared','name':'Sdílený produkt','store':'b'},{'id':'legacy','name':'Původní produkt'}],'counts':[{'id':'a1','product':'shared','store':'a','qty':4,'at':'2026-01-01T12:00:00Z'}],'moves':[],'draft':None,'barDraft':None,'barInventories':[]}
 visible=scoped_stock(data,['a'])
 assert 'store' not in next(p for p in visible['products'] if p['id']=='shared')
 merged=merge_scoped_stock(data,visible,['a'])
 assert merged==data


def test_paired_terminal_uses_owner_appearance_when_locked_and_unlocked(terminal):
 m,h,owner,e,eh,uid,pin,d,perms=terminal
 assert m.put('/api/appearance',json={'theme':8},headers=h).status_code==200
 assert d.get('/api/work/session').json['theme']==8
 wh=pin_login(d,pin)
 assert isinstance(wh,dict)
 assert d.get('/api/work/session').json['theme']==8
 assert m.put('/api/appearance',json={'theme':4},headers=h).status_code==200
 assert d.get('/api/work/session').json['theme']==4
