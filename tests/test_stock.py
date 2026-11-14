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
 assert 'stock.js?v=0.11.0' in a.get('/').text
