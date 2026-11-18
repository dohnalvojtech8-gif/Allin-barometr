"""Co-owners share a principal without sharing credentials or audit identity."""
import uuid
import itertools
from tests.test_accounts import app
from tests.test_allin import hub, create, enter
from server.app import PRODUCTS


client_ids=itertools.count(1)
def new_client():
    client=app.test_client();client.environ_base['REMOTE_ADDR']='192.0.2.'+str(next(client_ids))
    return client

def profile(**changes):
    return {'firstName':'Jana','lastName':'Spolumajitelka','username':'owner_'+uuid.uuid4().hex[:12],
            'password':'coowner-test-password','phone':'+420 777 111 222','email':'jana@example.cz',**changes}


def add(hub, **changes):
    client,headers,_=hub;values=profile(**changes)
    response=client.post('/api/owner/coowners',json=values,headers=headers)
    assert response.status_code==201,response.json
    other=new_client()
    assert other.post('/api/login',json={k:values[k] for k in ('username','password')}).status_code==200
    me=other.get('/api/me').json
    return (other,{'X-CSRF-Token':me['csrf']},response.json['user']['id']),values


def test_shared_existing_future_venues_and_audit(hub):
    primary,h,owner=hub;a=create(hub,'Společný bar');pa,ha=enter(hub,a)
    other,values=add(hub);client,ch,coowner=other
    assert client.get('/api/me').json['user']['stockOwnerId']==owner
    assert [v['id'] for v in client.get('/api/owner/venues').json['venues']]==[a]
    p,hc=enter(other,a)
    assert client.put(p+'/api/admin/users/'+owner+'/work-access',json={'pin':'1749','allowedStores':None},headers=hc).status_code==403
    assert client.get(p+'/api/stock').json==primary.get(pa+'/api/stock').json
    doc=client.get(p+'/api/stock').json
    doc['data']['stores'].append({'id':'shared','name':'Sdílený sklad'})
    assert client.put(p+'/api/stock',json=doc,headers=hc).status_code==200
    assert primary.get(pa+'/api/stock').json['data']['stores'][-1]['name']=='Sdílený sklad'
    events=primary.get('/api/owner/activity').json['events']
    assert any(e['user_id']==coowner and e['action']=='stock_saved' for e in events)
    b=create(other,'Provoz vytvořený spolumajitelem')
    pb,hb=enter(hub,b)
    assert client.get('/api/owner/venues').json['venues'][1]['owner_id']==owner
    assert len(primary.get('/api/owner/venues').json['venues'])==2
    assert primary.get(pb+'/api/stock').json['data']['stores'][0]['id']=='main'
    # Catalog, bottle inventory state, and snapshots belong to the shared venue.
    pid=next(iter(PRODUCTS))
    assert primary.post(pa+'/api/unlocks',json={'productId':pid},headers=ha).status_code==200
    assert pid in client.get(p+'/api/me').json['state']['unlocks']
    assert client.get(p+'/api/products/'+pid).status_code==200
    assert client.put(p+'/api/state',json={'cycle':'Denní'},headers=hc).status_code==200
    assert primary.get(pa+'/api/me').json['state']['cycle']=='Denní'
    image='data:image/jpeg;base64,/9j/2Q=='
    assert primary.put(pa+'/api/scan-photos/shared',json={'image':image},headers=ha).status_code==200
    assert client.get(p+'/api/scan-photos/shared').status_code==200
    assert client.put(p+'/api/scan-photos/shared',json={'image':image},headers=hc).status_code==200
    # Independent owners and anonymous clients still have no access.
    stranger=new_client()
    assert stranger.post('/api/login',json={'username':'AdminTwo','password':'test-admin-two-password'}).status_code==200
    sh={'X-CSRF-Token':stranger.get('/api/me').json['csrf']}
    assert stranger.post('/api/owner/venues/'+a+'/enter',json={},headers=sh).status_code==404
    assert stranger.put('/api/owner/coowners/'+coowner+'/status',json={'status':'suspended'},headers=sh).status_code==404
    assert app.test_client().get('/api/owner/coowners').status_code==401


def test_coowner_can_manage_employees_controls_and_positions(hub):
    a=create(hub,'Správa');other,_=add(hub);client,h,_=other
    values={'firstName':'Petr','lastName':'Zaměstnanec','username':'staff_'+uuid.uuid4().hex[:10],
            'password':'employee-test-password','pin':'9841'}
    response=client.post('/api/owner/venues/'+a+'/members',json=values,headers=h)
    assert response.status_code==201,response.json
    id=response.json['user']['id']
    assert client.post('/api/owner/venues/'+a+'/members/'+id,json={'status':'suspended'},headers=h).status_code==200
    assert client.put('/api/owner/venues/'+a+'/manager',json={'managerFirstName':'Petr','managerLastName':'Novák'},headers=h).status_code==200
    for url in ['/api/owner/venues/'+a+'/positions','/api/owner/venues/'+a+'/controls','/api/owner/attention','/api/owner/pos','/api/owner/analytics']:
        r=client.get(url);assert r.status_code==200,(url,r.json)
    # A regular employee cannot create owners, even when providing an admin role.
    primary,ph,_=hub
    primary.post('/api/owner/venues/'+a+'/members/'+id,json={'status':'active'},headers=ph)
    staff=new_client();assert staff.post('/api/login',json={k:values[k] for k in ('username','password')}).status_code==200
    me=staff.get('/v/'+a+'/api/me').json
    assert staff.post('/api/owner/coowners',json=profile(),headers={'X-CSRF-Token':me['csrf']}).status_code==401
    assert staff.post('/v/'+a+'/api/owner/coowners',json=profile(),headers={'X-CSRF-Token':me['csrf']}).status_code==403


def test_suspend_revokes_hub_venue_and_terminal_and_restore_needs_login(hub):
    primary,ph,owner=hub;a=create(hub,'Odebrání přístupu');other,values=add(hub)
    client,h,id=other;p,vh=enter(other,a)
    second=new_client()
    assert second.post('/api/login',json={k:values[k] for k in ('username','password')}).status_code==200
    enter((second,{'X-CSRF-Token':second.get('/api/me').json['csrf']},id),a)
    # Co-owners cannot suspend the primary account or another co-owner.
    assert client.put('/api/owner/coowners/'+owner+'/status',json={'status':'suspended'},headers=h).status_code==403
    assert client.put('/api/owner/coowners/'+id+'/status',json={'status':'suspended'},headers=h).status_code==403
    assert client.put(p+'/api/admin/users/'+id+'/work-access',json={'pin':'9861','allowedStores':None},headers=vh).status_code==200
    assert client.post(p+'/api/work/device',json={},headers=vh).status_code==200
    status=client.get(p+'/api/work/session').json
    assert client.post(p+'/api/work/login',json={'pin':'9861'},headers={'X-CSRF-Token':status['csrf']}).status_code==200
    assert client.get(p+'/api/work/stock').status_code==200
    url='/api/owner/coowners/'+id+'/status'
    assert primary.put(url,json={'status':'suspended'},headers=ph).status_code==200
    assert client.get('/api/me').status_code==401
    assert second.get(p+'/api/me').status_code==401
    assert client.get(p+'/api/work/stock').status_code==401
    status=client.get(p+'/api/work/session').json
    assert client.post(p+'/api/work/login',json={'pin':'9861'},headers={'X-CSRF-Token':status['csrf']}).status_code==401
    assert client.post('/api/login',json={k:values[k] for k in ('username','password')}).status_code==401
    assert primary.put(url,json={'status':'active'},headers=ph).status_code==200
    assert second.get(p+'/api/me').status_code==401
    assert client.get(p+'/api/work/stock').status_code==401
    assert client.post('/api/login',json={k:values[k] for k in ('username','password')}).status_code==200
    enter((client,{'X-CSRF-Token':client.get('/api/me').json['csrf']},id),a)


def test_validation_csrf_and_no_secret_leak(hub):
    client,h,_=hub
    assert client.post('/api/owner/coowners',json=profile()).status_code==403
    for changes in [{'password':'short'},{'username':'špatné jméno'},{'firstName':''},{'phone':'invalid'},{'email':'invalid'}]:
        assert client.post('/api/owner/coowners',json=profile(**changes),headers=h).status_code==400
    other,values=add(hub)
    assert client.post('/api/owner/coowners',json={**values,'username':values['username'].upper()},headers=h).status_code==409
    response=client.get('/api/owner/coowners')
    assert 'password' not in response.get_data(as_text=True)
    assert 'csrf' not in response.get_data(as_text=True)
    # Further owners join the same workspace instead of forming a nested group.
    third,_=add(other)
    assert third[0].get('/api/me').json['user']['stockOwnerId']==hub[2]
    assert len(client.get('/api/owner/coowners').json['owners'])==3
