from tests.test_allin import app,hub,create,enter


def test_owner_appearance_shared_with_venues_and_validated(hub):
    client,headers,_=hub
    first=create(hub,'První provoz')
    second=create(hub,'Druhý provoz')
    first_url,first_headers=enter(hub,first)
    second_url,_=enter(hub,second)
    assert client.get('/api/appearance').json=={'theme':1}
    for theme in (1,2,3,4,6,8):
        assert client.put('/api/appearance',json={'theme':theme},headers=headers).json=={'theme':theme}
        assert client.get(first_url+'/api/appearance').json=={'theme':theme}
        assert client.get(second_url+'/api/appearance').json=={'theme':theme}
    for invalid in (0,5,7,9,10,'2',True,None):
        assert client.put('/api/appearance',json={'theme':invalid},headers=headers).status_code==400
    assert client.put(first_url+'/api/appearance',json={'theme':2},headers=first_headers).status_code==403
    assert app.test_client().get('/api/appearance').status_code==401
    assert client.get('/api/appearance').json=={'theme':8}


def test_appearance_is_owner_scoped_and_staff_read_only(hub):
    import uuid
    client,headers,_=hub
    venue=create(hub,'Provoz pro obsluhu')
    prefix,_=enter(hub,venue)
    assert client.put('/api/appearance',json={'theme':3},headers=headers).status_code==200
    other=app.test_client()
    assert other.get(prefix+'/api/appearance').status_code==401
    invite=client.post('/api/owner/venues/'+venue+'/invites',json={'label':'Obsluha','days':7,'maxUses':1},headers=headers)
    assert invite.status_code==200
    staff=app.test_client()
    result=staff.post(prefix+'/api/register',json={'firstName':'Jan','lastName':'Test','username':'app_'+uuid.uuid4().hex[:10],'password':'employee-password','inviteCode':invite.json['code']})
    assert result.status_code==200
    assert staff.get(prefix+'/api/appearance').json=={'theme':3}
    csrf=staff.get(prefix+'/api/me').json['csrf']
    assert staff.put(prefix+'/api/appearance',json={'theme':8},headers={'X-CSRF-Token':csrf}).status_code==403
    assert client.get('/api/appearance').json=={'theme':3}


def test_coowner_shares_and_other_owner_is_isolated(hub):
    from tests.test_coowners import add
    from tests.test_accounts import login
    client,headers,_=hub
    assert client.put('/api/appearance',json={'theme':8},headers=headers).status_code==200
    coowner,_=add(hub)
    other,other_headers,_=coowner
    assert other.get('/api/appearance').json=={'theme':8}
    assert other.put('/api/appearance',json={'theme':6},headers=other_headers).status_code==200
    assert client.get('/api/appearance').json=={'theme':6}
    outsider,outsider_headers=login()
    assert outsider.get('/api/appearance').json=={'theme':1}
    assert outsider.put('/api/appearance',json={'theme':4},headers=outsider_headers).status_code==200
    assert client.get('/api/appearance').json=={'theme':6}
