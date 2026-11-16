import base64
import json
from tests.test_allin import hub,create,enter
from server.app import app,db,one,allrows
from server.allin import venue_context
import server.notifications as notifications


def subscription(suffix='owner'):
 from cryptography.hazmat.primitives.asymmetric import ec
 from cryptography.hazmat.primitives import serialization
 pub=ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
 enc=lambda raw:base64.urlsafe_b64encode(raw).decode().rstrip('=')
 return {'endpoint':'https://fcm.googleapis.com/fcm/send/'+suffix,'keys':{'auth':enc(b'x'*16),'p256dh':enc(pub)}}


def test_settings_and_subscriptions_are_private_and_scoped(hub):
 client,h,owner=hub
 assert app.test_client().get('/api/notifications').status_code==401
 initial=client.get('/api/notifications');assert initial.status_code==200,initial.json
 assert set(initial.json['preferences'])==set(notifications.DEFAULTS)
 assert len(base64.urlsafe_b64decode(initial.json['publicKey']+'='))==65
 assert 'private_key' not in initial.text
 assert client.put('/api/notifications',json={'preferences':notifications.DEFAULTS}).status_code==403
 assert client.put('/api/notifications',json={'preferences':{'inventory':'true'}},headers=h).status_code==400
 prefs={**notifications.DEFAULTS,'inventory':False}
 assert client.put('/api/notifications',json={'preferences':prefs},headers=h).status_code==200
 sub=subscription();assert client.post('/api/notifications/subscription',json={'subscription':sub},headers=h).status_code==200
 assert client.get('/api/notifications').json['devices']==1
 assert client.get('/api/notifications/device',query_string={'endpoint':sub['endpoint']}).json['subscribed']
 a=create(hub,'Nastavení A');pa,ha=enter(hub,a)
 assert client.get(pa+'/api/notifications').json['preferences']['inventory'] is True
 assert client.get(pa+'/api/notifications').json['devices']==0
 assert client.delete(pa+'/api/notifications/subscription',json={'endpoint':sub['endpoint']},headers=ha).status_code==200
 assert client.get('/api/notifications').json['devices']==1
 assert client.delete('/api/notifications/subscription',json={'endpoint':sub['endpoint']},headers=h).status_code==200
 assert client.get('/api/notifications').json['devices']==0


def test_push_endpoint_validation_and_test_delivery(hub,monkeypatch):
 client,h,owner=hub;sub=subscription()
 for endpoint in ('http://fcm.googleapis.com/test','https://localhost/test','https://169.254.169.254/latest/meta-data','https://fcm.googleapis.com:bad/test','https://evil.example/test'):
  assert client.post('/api/notifications/subscription',json={'subscription':{**sub,'endpoint':endpoint}},headers=h).status_code==400
 assert client.post('/api/notifications/subscription',json={'subscription':sub},headers=h).status_code==200
 sent=[];monkeypatch.setattr(notifications,'deliver',lambda s,p,k:sent.append((s,p)))
 assert client.post('/api/notifications/test',json={'endpoint':'https://fcm.googleapis.com/other'},headers=h).status_code==400
 assert client.post('/api/notifications/test',json={'endpoint':sub['endpoint']},headers=h).status_code==200
 assert sent[0][1]['title']=='NOIRA · oznámení fungují'
 # Key material is loadable by the actual Web Push signer.
 from py_vapid import Vapid
 with db(central=True) as c:key=one(c,"SELECT private_key FROM notification_keys WHERE id='vapid'")
 assert Vapid.from_string(key['private_key']).sign({'sub':'mailto:allinbarometr@seznam.cz','aud':'https://fcm.googleapis.com'})


def test_stock_events_are_transactional_and_dispatch_respects_preferences(hub,monkeypatch):
 client,h,owner=hub;a=create(hub,'Sklad oznámení');pa,ha=enter(hub,a)
 sub=subscription('inventory-owner');assert client.post('/api/notifications/subscription',json={'subscription':sub},headers=h).status_code==200
 data={'stores':[{'id':'main','name':'Sklad'}],'products':[{'id':'p','store':'main','name':'Lahev','category':'Zboží','kind':'piece','unit':'ks','cost':0,'min':3,'tare':0,'capacity':0,'density':1}],
 'counts':[{'id':'count','inventoryId':'inventory','store':'main','product':'p','qty':1,'at':'2025-01-01T12:00:00+00:00'}],'moves':[],'draft':None,'barInventories':[]}
 assert client.put(pa+'/api/stock',json={'revision':0,'data':data},headers=ha).status_code==200
 with db(central=True) as c:venue=one(c,'SELECT * FROM allin_venues WHERE id=%s',(a,))
 with app.test_request_context(),venue_context(venue),db() as c:
  events=allrows(c,'SELECT * FROM notification_outbox')
 assert {e['kind'] for e in events}=={'inventory','low_stock'}
 sent=[];monkeypatch.setattr(notifications,'deliver',lambda s,p,k:sent.append(p))
 assert client.put('/api/notifications',json={'preferences':{**notifications.DEFAULTS,'inventory':False}},headers=h).status_code==200
 notifications.dispatch(app,venue)
 assert len(sent)==1 and 'nízká zásoba' in sent[0]['title']
 with app.test_request_context(),venue_context(venue),db() as c:
  assert one(c,'SELECT count(*) AS n FROM notification_outbox WHERE sent_at IS NULL')['n']==0
