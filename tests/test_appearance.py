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
