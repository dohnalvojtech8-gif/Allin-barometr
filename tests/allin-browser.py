"""Browser regression for the local disposable Allin server only."""
import uuid
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1000})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:10000/')
 page.locator('[name=username]').fill('owner');page.locator('[name=password]').fill('local-browser-test-password')
 page.locator('#auth-form button[type=submit]').click()
 page.locator('#owner-nav a').first.wait_for()
 assert page.locator('#owner-nav a').all_text_contents()==['◫Souhrnný přehled','▦Moje provozy','♧Uživatelé a přístupy','＋Vytvoření nového provozu','▥Porovnání provozů','◷Aktivita napříč provozy','⚙Nastavení majitele a účtu']
 suffix=uuid.uuid4().hex[:6]
 new_venue_id=None
 for name in ['Bar na náměstí '+suffix,'Vinárna Pod věží '+suffix]:
  page.locator('#owner-nav a[href="#create"]').click()
  page.locator('#create-venue [name=name]').fill(name)
  page.locator('#create-venue [name=address]').fill('Praha')
  page.locator('#create-venue button').click()
  page.wait_for_url('**/#venues');page.locator('.venue-card').filter(has_text=name).last.wait_for();new_venue_id=page.locator('.venue-card').filter(has_text=name).last.locator('[data-enter]').get_attribute('data-enter')
 page.locator('#owner-nav a[href="#overview"]').click();page.locator('.hub-stats').wait_for()
 page.screenshot(path='/tmp/allin-owner-desktop.png',full_page=True)
 page.locator('#owner-nav a[href="#team"]').click();page.locator('[data-hub-create-employee]').click()
 form=page.locator('#employee-form');form.locator('[name=venueId]').select_option(new_venue_id)
 for name,value in {'firstName':'První','lastName':'Zaměstnanec','username':'employee_'+suffix,'password':'employee-test-password','pin':'7391'}.items():form.locator('[name='+name+']').fill(value)
 form.locator('[type=submit]').click();page.get_by_role('heading',name='Zaměstnanecký profil je vytvořený').wait_for()
 page.locator('[data-auth-close]').first.click()
 page.locator('#owner-nav a[href="#venues"]').click()
 page.locator('[data-enter]').first.click()
 page.wait_for_url('**/v/**/');page.locator('#app').get_by_text('Každý sklad.',exact=False).wait_for()
 assert page.locator('.workspace').inner_text().find('Bar na náměstí')>=0
 page.goto(page.url+'#catalog');page.locator('[data-bundle-id]').first.wait_for()
 print('Venue catalog loads; URL:',page.url)
 page.goto('http://127.0.0.1:10000/#comparison');page.locator('.hub-compare-bars').wait_for()
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path='/tmp/allin-owner-mobile.png',full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
 page.locator('#owner-menu').click();page.locator('#owner-nav a[href="#activity"]').click();page.locator('#activity-events').wait_for()
 assert not errors,errors
 print('PASS: login, menu order, two venues, employee creation, venue entry, catalog, comparison, mobile navigation and no JavaScript errors')
 browser.close()
