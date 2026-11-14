import copy
import time
from datetime import datetime,timezone
from tests.test_accounts import login
from server.app import app

def payload():
 return {'stores':[{'id':'s1','name':'Sklad 1'}],'products':[{'id':'pizza','name':'Krabice pizza 32 cm','category':'Obaly','unit':'ks','kind':'piece','cost':8,'min':100,'tare':0,'capacity':0,'density':1,'supplier':'','barcode':''}],'counts':[{'id':'count1','store':'s1','product':'pizza','qty':345,'at':datetime.now(timezone.utc).isoformat()}],'moves':[],'draft':None}

def test_stock_is_account_owned_and_does_not_replace_profile_or_bottle_state():
 a,h=login();b,bh=login('AdminTwo','test-admin-two-password')
 before=a.get('/api/me').json
 initial=a.get('/api/stock').json
 r=a.put('/api/stock',json={'revision':initial['revision'],'data':payload()},headers=h)
 assert r.status_code==200,r.json
 assert a.get('/api/stock').json['data']['counts'][0]['qty']==345
 assert b.get('/api/stock').json['data']['products']==[]
 after=a.get('/api/me').json
 assert after['state']==before['state']
 assert after['user']['id']==before['user']['id']
 assert after['user']['first_name']==before['user']['first_name']
 assert app.test_client().get('/api/stock').status_code==401
 assert a.put('/api/stock',json={'revision':r.json['revision'],'data':payload()}).status_code==403

def test_stale_device_cannot_overwrite_newer_inventory():
 a,h=login();old=a.get('/api/stock').json
 first=a.put('/api/stock',json={'revision':old['revision'],'data':payload()},headers=h)
 assert first.status_code==200
 stale=payload();stale['counts'][0]['qty']=999
 assert a.put('/api/stock',json={'revision':old['revision'],'data':stale},headers=h).status_code==409
 assert a.get('/api/stock').json['data']['counts'][0]['qty']==345

def test_stock_rejects_invalid_references_nonfinite_counts_and_duplicate_ids():
 a,h=login()
 for mutate in [lambda d:d['counts'][0].update(store='other'),lambda d:d['counts'][0].update(qty=-1),lambda d:d['counts'][0].update(qty=float('inf')),lambda d:d['products'].append(copy.deepcopy(d['products'][0])),lambda d:d['products'][0].update(kind='keg',unit='ks')]:
  d=payload();mutate(d);rev=a.get('/api/stock').json['revision']
  assert a.put('/api/stock',json={'revision':rev,'data':d},headers=h).status_code==400
 assert a.get('/stock.js').status_code==200
 assert 'stock.js?v=0.12.1' in a.get('/').text

def test_stock_audit_freezes_expected_values_and_cannot_be_forged():
 a,h=login();d=payload();rev=a.get('/api/stock').json['revision'];r=a.put('/api/stock',json={'revision':rev,'data':d},headers=h);assert r.status_code==200
 current=a.get('/api/stock').json;d=current['data'];d['moves'].append({'id':'delivery-audit','product':'pizza','store':'s1','qty':20,'reason':'Příjem','at':datetime.now(timezone.utc).isoformat()})
 r=a.put('/api/stock',json={'revision':current['revision'],'data':d},headers=h);assert r.status_code==200
 current=a.get('/api/stock').json;d=current['data'];d['counts'].append({'id':'count-audit-2','inventoryId':'test-inventory-audit','product':'pizza','store':'s1','qty':350,'expected':99999,'at':datetime.now(timezone.utc).isoformat()})
 r=a.put('/api/stock',json={'revision':current['revision'],'data':d},headers=h);assert r.status_code==200,r.json
 assert r.json['data']['counts'][-1]['expected']==365
 changes=a.get('/api/admin/stock-changes?q=Krabice').json['changes']
 assert any(c['field']=='qty' and c['before']==345 and c['after']==365 for c in changes)
 assert any(c['field']=='qty' and c['before']==365 and c['after']==350 for c in changes)
 previous=len(changes);assert a.put('/api/stock',json={'revision':0,'data':d},headers=h).status_code==409
 assert len(a.get('/api/admin/stock-changes?q=Krabice').json['changes'])==previous

def test_permissions_shared_stock_receiving_and_server_denial():
 a,h=login();owner=a.get('/api/me').json['user']['id']
 from tests.test_accounts import invite
 code=invite(a,h)['code'];u=app.test_client();assert u.post('/api/register',json={'firstName':'Sklad','lastName':'Test','username':'permissions_stock','password':'test-password-safe','inviteCode':code}).status_code==200
 me=u.get('/api/me').json;uh={'X-CSRF-Token':me['csrf']};pid=me['user']['id']
 perms={k:False for k in me['user']['permissions']};perms.update({'stock.view':True,'stock.receive':True})
 assert a.post('/api/admin/users/'+pid+'/permissions',json={'permissions':perms,'stockOwnerId':owner},headers=h).status_code==200
 shared=u.get('/api/stock').json;assert shared['data']==a.get('/api/stock').json['data']
 changed=copy.deepcopy(shared['data']);changed['products'][0]['name']='Unauthorized rename'
 assert u.put('/api/stock',json={'revision':shared['revision'],'data':changed},headers=uh).status_code==403
 received=copy.deepcopy(shared['data']);received['moves'].append({'id':'authorized-receipt','product':'pizza','store':'s1','qty':4,'reason':'Příjem','at':datetime.now(timezone.utc).isoformat()})
 r=u.put('/api/stock',json={'revision':shared['revision'],'data':received},headers=uh);assert r.status_code==200,r.json
 assert a.get('/api/stock').json['data']['moves'][-1]['qty']==4
 assert u.get('/api/admin/stock-changes').status_code==403
 assert u.post('/api/admin/users/'+owner+'/permissions',json={'permissions':perms},headers=uh).status_code==403
 assert u.post('/api/unlocks',json={'productId':'amundsen'},headers=uh).status_code==403
 assert a.post('/api/admin/users/'+owner+'/permissions',json={'permissions':perms},headers=h).status_code==403
 assert u.put('/api/state',json={'rows':[],'records':[],'inventoryPlan':{'entries':[]}},headers=uh).status_code==403

def test_warehouse_rename_and_removal_preserve_history_and_block_new_stock():
 a,h=login();before=a.get('/api/stock').json;d=copy.deepcopy(before['data']);sid=d['stores'][0]['id'];old_name=d['stores'][0]['name']
 d['stores'][0]['name']='Přejmenovaný sklad'
 renamed=a.put('/api/stock',json={'revision':before['revision'],'data':d},headers=h);assert renamed.status_code==200,renamed.json
 assert renamed.json['data']['counts']==before['data']['counts']
 d=copy.deepcopy(renamed.json['data']);d['stores'][0]['archivedAt']=datetime.now(timezone.utc).isoformat()
 removed=a.put('/api/stock',json={'revision':renamed.json['revision'],'data':d},headers=h);assert removed.status_code==200,removed.json
 assert removed.json['data']['counts']==before['data']['counts']
 assert removed.json['data']['products']==before['data']['products']
 changes=a.get('/api/admin/stock-changes?store='+sid).json['changes']
 assert any(c['field']=='name' and c['before']==old_name and c['after']=='Přejmenovaný sklad' for c in changes)
 assert any(c['field']=='archivedAt' and c['after'] is not None for c in changes)
 invalid=copy.deepcopy(removed.json['data']);invalid['moves'].append({'id':'archived-receipt','product':invalid['products'][0]['id'],'store':sid,'qty':1,'reason':'Příjem','at':datetime.now(timezone.utc).isoformat()})
 assert a.put('/api/stock',json={'revision':removed.json['revision'],'data':invalid},headers=h).status_code==400
 d=copy.deepcopy(removed.json['data']);d['stores'][0]['archivedAt']=None
 restored=a.put('/api/stock',json={'revision':removed.json['revision'],'data':d},headers=h);assert restored.status_code==200,restored.json
 assert restored.json['data']['counts']==before['data']['counts']

def test_removal_of_warehouse_with_open_inventory_is_rejected():
 a,h=login();before=a.get('/api/stock').json;d=copy.deepcopy(before['data']);sid=d['stores'][0]['id']
 d['draft']={'store':sid,'products':[d['products'][0]['id']],'values':{},'at':datetime.now(timezone.utc).isoformat()}
 d['stores'][0]['archivedAt']=datetime.now(timezone.utc).isoformat()
 assert a.put('/api/stock',json={'revision':before['revision'],'data':d},headers=h).status_code==400
 assert a.get('/api/stock').json['revision']==before['revision']
