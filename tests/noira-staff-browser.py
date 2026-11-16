"""Local browser regression for position creation, employee provisioning and main-address login."""
import uuid
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:10000'
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':390,'height':844},service_workers='block');errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(BASE);page.locator('[name=username]').fill('owner');page.locator('[name=password]').fill('local-browser-test-password');page.locator('#auth-form [type=submit]').click();page.locator('#owner-nav a').first.wait_for(state='attached')
 me=page.request.get(BASE+'/api/me').json();headers={'X-CSRF-Token':me['csrf']};suffix=uuid.uuid4().hex[:8]
 venue=page.request.post(BASE+'/api/owner/venues',data={'name':'Pozice '+suffix},headers=headers).json()['venue']['id']
 page.goto(BASE+'/#team');page.locator('[data-position-venue]').select_option(venue);page.locator('[data-new-position]').click();form=page.locator('#position-form');form.locator('[name=name]').fill('Kuchař '+suffix)
 for check in form.locator('[data-staff-permission]').all():check.uncheck()
 form.locator('[data-staff-permission="stock.view"]').check();form.locator('[data-staff-permission="inventory.history"]').check();form.locator('[type=submit]').click();page.locator('#position-form').wait_for(state='detached')
 positions=page.request.get(BASE+'/api/owner/venues/'+venue+'/positions').json()['positions'];position=next(x for x in positions if x['name']=='Kuchař '+suffix)
 page.locator('[data-hub-create-employee]').click();form=page.locator('#employee-form');form.locator('[name=venueId]').select_option(venue);form.locator('[data-position]').select_option(position['id'])
 values={'firstName':'Petr','lastName':'Kuchař','username':'chef_'+suffix,'password':'staff-browser-password','pin':'1469'}
 for key,value in values.items():form.locator('[name='+key+']').fill(value)
 assert not form.locator('[data-staff-permission="inventory.warehouse"]').is_checked()
 form.locator('summary').click();form.locator('[data-staff-permission="reports.view"]').check();form.locator('[type=submit]').click();page.get_by_role('heading',name='Zaměstnanecký profil je vytvořený').wait_for();page.locator('[data-auth-close]').first.click()
 row=page.locator('tbody tr').filter(has_text=values['username']);row.wait_for();assert 'Kuchař '+suffix in row.inner_text()
 staff=browser.new_page(viewport={'width':390,'height':844},service_workers='block');staff.on('pageerror',lambda e:errors.append(str(e)))
 staff.goto(BASE);staff.locator('[name=username]').fill(values['username']);staff.locator('[name=password]').fill(values['password']);staff.locator('#auth-form [type=submit]').click();staff.wait_for_url('**/v/'+venue+'/**');staff.locator('.account-name').wait_for()
 assert staff.locator('#nav a[href="#barnew"]').count()==0
 assert staff.locator('#nav a[href="#stockcount"]').count()==0
 assert staff.locator('#nav a[href="#catalog"]').count()==0
 assert staff.locator('#nav a[href="#warehouses"]').count()==1
 assert staff.locator('#nav a[href="#reports"]').count()==1
 staff.goto(BASE+'/v/'+venue+'/#stockcount');staff.locator('#app .profile-card').wait_for() if staff.locator('#app .profile-card').count() else staff.get_by_role('heading',name='Můj profil',exact=True).wait_for()
 assert staff.locator('#app [data-count-save]').count()==0
 staff.goto(BASE+'/v/'+venue+'/#menu');staff.locator('#app').wait_for();assert staff.evaluate('document.documentElement.scrollWidth<=innerWidth')
 staff.screenshot(path='/tmp/noira-staff-mobile.png',full_page=True)
 assert staff.request.get(BASE+'/api/me').status==401
 assert not errors,errors
 print('PASS: custom position UI, per-employee override, root login redirects to venue, forbidden navigation and direct routes hidden, mobile layout, isolated owner access')
 browser.close()
