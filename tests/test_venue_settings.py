import uuid
from pathlib import Path
import pytest
from tests.test_allin import hub,create,enter
from tests.test_employees import profile
from tests.test_accounts import app,db,one,execute
from server.app import TEST_DB
from server.venue_settings import CARD_DEFAULTS,CARD_STYLES


def test_archive_revokes_existing_staff_owner_and_terminal_access_and_restore(hub):
 client,h,owner=hub;a=create(hub,'Archivovat bar');b=create(hub,'Zachovat bar');p,vh=enter(hub,a)
 values=profile();created=client.post('/api/owner/venues/'+a+'/members',json=values,headers=h)
 assert created.status_code==201
 staff=app.test_client();assert staff.post(p+'/api/login',json={k:values[k] for k in ('username','password')}).status_code==200
 assert staff.get(p+'/api/me').status_code==200
 assert client.put(p+'/api/admin/users/'+owner+'/work-access',json={'pin':'8931','allowedStores':None},headers=vh).status_code==200
 assert client.post(p+'/api/work/device',json={},headers=vh).status_code==200
 assert client.post('/api/owner/venues/'+a+'/archive',json={},headers=h).status_code==200
 assert [v['id'] for v in client.get('/api/owner/venues').json['venues']]==[b]
 archived=client.get('/api/owner/venues?archived=1').json['venues'];assert [v['id'] for v in archived]==[a]
 assert archived[0]['archived_at']
 for who in (client,staff):
  for path in ('/api/me','/api/stock','/api/work/session','/'):
   assert who.get(p+path).status_code==410
 assert 'Provoz je archivovaný' in client.get(p+'/').get_data(as_text=True)
 assert client.post('/api/owner/venues/'+a+'/enter',json={},headers=h).status_code==409
 assert staff.post('/api/login',json={k:values[k] for k in ('username','password')}).status_code==401
 assert client.get('/api/owner/team').json['members']==[]
 assert client.post('/api/owner/venues/'+a+'/restore',json={},headers=h).status_code==200
 assert staff.get(p+'/api/me').status_code==401
 assert client.get(p+'/api/work/session').status_code==401
 assert len(client.get('/api/owner/venues').json['venues'])==2
 assert client.get('/api/owner/venues?archived=1').json['venues']==[]
 assert len(client.get('/api/owner/team').json['members'])==1
 enter(hub,a)
 assert client.get(p+'/api/stock').json['data']['stores'][0]['id']=='main'


def test_delete_requires_name_and_preserves_other_venues_and_owners(hub):
 client,h,owner=hub;a=create(hub,'Smazat jen tento');b=create(hub,'Zachovat druhý');p,vh=enter(hub,a)
 path=Path(TEST_DB).with_name('venue_'+a+'.sqlite3');assert path.exists()
 url='/api/owner/venues/'+a
 assert client.delete(url,json={'confirmation':'špatně'},headers=h).status_code==400
 assert path.exists() and client.get(p+'/api/me').status_code==200
 assert client.delete(url,json={'confirmation':'Smazat jen tento'}).status_code==403
 with db(central=True) as c:
  execute(c,'INSERT INTO pos_connections (venue_id,provider,updated_at) VALUES (%s,%s,%s)',(a,'manual',0))
 assert client.delete(url,json={'confirmation':'Smazat jen tento'},headers=h).status_code==200
 assert not path.exists()
 assert client.get(p+'/api/me').status_code==404
 assert client.get('/api/me').json['user']['id']==owner
 assert [v['id'] for v in client.get('/api/owner/venues').json['venues']]==[b]
 with db(central=True) as c:
  assert one(c,'SELECT venue_id FROM pos_connections WHERE venue_id=%s',(a,)) is None
  assert one(c,'SELECT id FROM users WHERE id=%s',(owner,))


def test_card_appearance_validation_persistence_and_foreign_owner_denial(hub):
 client,h,_=hub;a=create(hub,'Vzhled');url='/api/owner/venues/'+a+'/card'
 settings={**CARD_DEFAULTS,'background':'#123456','accent':'#AaBbCc','font':'georgia','radius':0,'bold':True,'italic':True,'shadow':True}
 for style in CARD_STYLES:
  r=client.put(url,json={**settings,'style':style},headers=h);assert r.status_code==200,r.json
 result=client.get('/api/owner/venues').json['venues'][0]['cardStyle']
 assert result['background']=='#123456' and result['accent']=='#aabbcc' and result['radius']==0 and result['bold']
 for invalid in ({'background':'red'},{'font':'url(evil)'},{'style':'unknown'},{'titleSize':True},{'radius':33},{'shadow':'yes'},{'italic':1},{'extra':'value'}):
  assert client.put(url,json=invalid,headers=h).status_code==400
 assert client.put(url,json=settings).status_code==403
 # A foreign central owner cannot mutate lifecycle or appearance.
 from tests.test_coowners import new_client
 other=new_client();assert other.post('/api/login',json={'username':'AdminTwo','password':'test-admin-two-password'}).status_code==200
 oh={'X-CSRF-Token':other.get('/api/me').json['csrf']}
 for suffix,method in [('/archive','post'),('/restore','post'),('/card','put'),('','delete')]:
  r=getattr(other,method)('/api/owner/venues/'+a+suffix,json=settings,headers=oh);assert r.status_code==404


def test_coowner_shares_appearance_and_can_manage_venue_lifecycle(hub):
 from tests.test_coowners import add
 client,h,_=hub;a=create(hub,'Společný provoz')
 (other,oh,_),_=add(hub)
 assert other.put('/api/owner/venues/'+a+'/card',json={'font':'georgia'},headers=oh).status_code==200
 assert client.get('/api/owner/venues').json['venues'][0]['cardStyle']['font']=='georgia'
 assert other.post('/api/owner/venues/'+a+'/archive',json={},headers=oh).status_code==200
 assert client.get('/api/owner/venues?archived=1').json['venues'][0]['id']==a
 assert other.post('/api/owner/venues/'+a+'/restore',json={},headers=oh).status_code==200
 assert other.delete('/api/owner/venues/'+a,json={'confirmation':'Společný provoz'},headers=oh).status_code==200
 assert client.get('/api/me').status_code==200
