"""Local-only employee creation through both owner and venue UI, then password/PIN sign-in."""
import uuid
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:10000'
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':390,'height':844},service_workers='block');errors=[]
 page.on('pageerror',lambda error:errors.append(str(error)))
 page.goto(BASE);page.locator('[name=username]').fill('owner');page.locator('[name=password]').fill('local-browser-test-password');page.locator('#auth-form [type=submit]').click()
 page.locator('#owner-nav a').first.wait_for(state='attached')
 me=page.request.get(BASE+'/api/me').json();csrf={'X-CSRF-Token':me['csrf']};owner_id=me['user']['id'];suffix=uuid.uuid4().hex[:8]
 response=page.request.post(BASE+'/api/owner/venues',data={'name':'Profily '+suffix},headers=csrf)
 assert response.status==201,response.text()
 venue=response.json()['venue']['id'];venue_url=BASE+'/v/'+venue+'/'
 page.goto(BASE+'/#team');page.locator('[data-hub-create-employee]').click();form=page.locator('#employee-form')
 form.locator('[name=venueId]').select_option(venue)
 first={'firstName':'Jana','lastName':'Nováková','username':'staff_'+suffix,'password':'employee-browser-password','pin':'2468'}
 for key,value in first.items():form.locator('[name='+key+']').fill(value)
 page.locator('.noira-language select').select_option('de');assert form.locator('[name=password]').input_value()==first['password']
 page.get_by_role('heading',name='Mitarbeiterprofil erstellen').wait_for()
 form.locator('[type=submit]').click();page.get_by_role('heading',name='Mitarbeiterprofil erstellt').wait_for()
 assert first['password'] not in page.locator('#modal').inner_text() and page.locator('#modal [name=pin]').count()==0
 page.locator('[data-auth-close]').first.click();page.locator('tbody tr').filter(has_text=first['username']).wait_for()
 assert page.locator('[data-hub-invite]').count()==0 and page.request.get(BASE+'/api/me').json()['user']['id']==owner_id
 response=page.request.post(BASE+'/api/owner/venues/'+venue+'/enter',data={},headers=csrf);assert response.status==200
 page.goto(venue_url+'#users');page.locator('[data-create-employee]').wait_for()
 assert page.locator('[data-admin-invite]').count()==0
 page.locator('[data-create-employee]').click();form=page.locator('#employee-form')
 second={'firstName':'Nastavení','lastName':'Test','username':'local_'+suffix,'password':'second-browser-password','pin':'3579'}
 for key,value in second.items():form.locator('[name='+key+']').fill(value)
 page.locator('.noira-language select').select_option('en');page.get_by_role('heading',name='Create employee profile').wait_for()
 assert form.locator('[name=pin]').input_value()=='3579'
 page.screenshot(path='/tmp/noira-employee-form-mobile.png',full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 form.locator('[type=submit]').click();page.get_by_role('heading',name='Employee profile created').wait_for();page.locator('[data-auth-close]').first.click()
 page.locator('#users-body tr').filter(has_text=second['username']).wait_for()
 assert page.request.get(venue_url+'api/me').json()['user']['id']==owner_id
 staff=browser.new_page(service_workers='block');staff.goto(venue_url)
 assert staff.locator('[data-auth-mode=register]').count()==0
 staff.locator('[name=username]').fill(first['username']);staff.locator('[name=password]').fill(first['password']);staff.locator('#auth-form [type=submit]').click()
 staff.locator('.account-name').get_by_text(first['username'],exact=True).wait_for()
 assert staff.request.get(venue_url+'api/me').json()['user']['role']=='user'
 # The PIN set in the creation form works immediately on an owner-paired terminal.
 page.goto(venue_url+'#settings');page.locator('[data-work-access]').first.click()
 pin=page.locator('#work-access-form');pin.locator('[name=pin]').fill('1357');pin.locator('[type=submit]').click()
 page.get_by_role('heading',name='Work access saved').wait_for();page.locator('[data-auth-close]').first.click()
 page.locator('[data-start-work]').click();page.locator('[data-confirm-work]').click();page.wait_for_url('**/work');page.locator('#pin-form').wait_for()
 for digit in first['pin']:page.locator('[data-digit="'+digit+'"]').click()
 page.locator('#pin-form [type=submit]').click();page.locator('.work-header').wait_for()
 assert 'Jana Nováková' in page.locator('.work-header').inner_text()
 assert page.request.get(venue_url+'api/work/session').json()['isOwner'] is False
 assert not errors,errors
 print('PASS: owner and venue creation, all five fields, CZ/EN/DE forms, preserved input, mobile layout, owner session retained, employee password and PIN login')
 browser.close()
