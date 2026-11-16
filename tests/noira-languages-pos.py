"""Local browser acceptance: owner-only POS reporting and language switching without losing input."""
import uuid
from playwright.sync_api import sync_playwright
ORIGIN='http://127.0.0.1:10000'
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':390,'height':844},service_workers='block')
 errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
 page.goto(ORIGIN)
 page.locator('.noira-language select').select_option('en')
 page.get_by_role('heading',name='Your bar. Your overview.').wait_for()
 page.locator('[name=username]').fill('owner');page.locator('[name=password]').fill('local-browser-test-password')
 page.locator('.noira-language select').select_option('de')
 assert page.locator('[name=username]').input_value()=='owner'
 assert page.locator('[name=password]').input_value()=='local-browser-test-password'
 page.get_by_role('button',name='Anmelden →').click();page.locator('#owner-nav a').first.wait_for(state='attached')
 assert page.locator('html').get_attribute('lang')=='de'
 page.goto(ORIGIN+'/#create');page.locator('#create-venue [name=name]').fill('Nastavení')
 page.locator('.noira-language select').select_option('en')
 assert page.locator('#create-venue [name=name]').input_value()=='Nastavení'
 page.locator('#create-venue button').click();page.wait_for_url('**/#venues')
 card=page.locator('.venue-card').filter(has=page.get_by_role('heading',name='Nastavení',exact=True)).last
 card.wait_for();venue=card.locator('[data-enter]').get_attribute('data-enter')
 # Use the real CSV form; no provider API is represented as connected.
 page.goto(ORIGIN+'/#settings');form=page.locator('#pos-import-form');form.wait_for()
 assert page.get_by_text('Mode: manual CSV import',exact=True).count()>0
 form.locator('[name=venue]').select_option(venue)
 form.locator('[name=file]').set_input_files({'name':'daily.csv','mimeType':'text/csv','buffer':b'datum;kasa;mena;trzby_bez_dph;naklady_zbozi;provozni_naklady;uzaverka_id\n2025-01-01;bar;CZK;10000;3000;2000;UZ1\n2025-01-02;bar;CZK;5000;;;UZ2\n'})
 form.get_by_role('button',name='Import closings').click()
 page.get_by_text('Import complete: 2 new, 0 updated, 0 unchanged.',exact=True).wait_for()
 page.goto(ORIGIN+'/#comparison');history=page.locator('#pos-history');history.locator('form').wait_for()
 history.locator('[name=venue]').select_option(venue);history.locator('[name=from]').fill('2025-01-02');history.locator('[name=to]').fill('2025-01-02')
 history.get_by_role('button',name='Apply filters').click();history.locator('[data-pos-detail]').first.wait_for()
 assert history.locator('[data-pos-detail]').count()==1
 assert 'Costs missing' in history.inner_text()
 page.locator('.noira-language select').select_option('de')
 assert history.locator('[name=from]').input_value()=='2025-01-02'
 assert '5.000,00' in history.locator('.pos-totals').inner_text()
 crumb=page.locator('#owner-breadcrumb').bounding_box();assert crumb['width']>250 and crumb['height']<60
 for field in history.locator('.pos-filters input').all():
  bounds=field.bounding_box();assert bounds['x']>=0 and bounds['x']+bounds['width']<=390
 history.get_by_role('heading',name='Tagesergebnisse der Filialen').wait_for()
 assert history.locator('tbody tr').first.locator('td').nth(1).inner_text().startswith('Nastavení')
 history.locator('[data-pos-detail]').click();page.get_by_role('heading',name='Korrekturhistorie').wait_for();page.locator('[data-auth-close]').click()
 page.screenshot(path='/tmp/noira-owner-german-mobile.png',full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.reload();page.locator('#pos-history form').wait_for();assert page.locator('.noira-language select').input_value()=='de'
 page.goto(ORIGIN+'/#venues');page.locator('[data-enter="'+venue+'"]').click();page.wait_for_url('**/v/**/');page.locator('#app .overview-hero').wait_for()
 assert page.locator('.workspace').inner_text().find('Nastavení')>=0
 assert page.evaluate('typeof window.NoiraPOS')=='undefined'
 venue_url=page.url
 page.goto(venue_url+'#settings');page.locator('#cycle').wait_for()
 assert page.locator('#cycle option').first.inner_text()=='Täglich'
 assert page.locator('#cycle option').first.get_attribute('value')=='Denní'
 page.locator('.noira-language select').select_option('cs');assert page.locator('#cycle option').first.inner_text()=='Denní'
 page.locator('.noira-language select').select_option('en');assert page.locator('#cycle option').first.inner_text()=='Daily'
 page.reload();page.locator('#cycle').wait_for();assert page.locator('.noira-language select').input_value()=='en'
 # Exercise real warehouse forms and the PIN terminal in the selected language.
 page.goto(venue_url+'#warehouses');page.locator('[data-stock-action="add-store"]').click()
 page.locator('#store-form [name=name]').fill('Nastavení');page.locator('#store-form button').click()
 page.locator('[data-stock-action="add-product"]').wait_for()
 assert page.locator('.top h1').inner_text()=='Nastavení'
 page.locator('[data-stock-action="add-product"]').click();product=page.locator('#stock-product-form')
 product.locator('[name=name]').fill('Nastavení');assert product.locator('[name=unit]').input_value()=='ks'
 product.locator('button[type=submit],button.primary').last.click();page.locator('#stock-dialog').wait_for(state='hidden')
 page.get_by_role('link',name='Nastavení',exact=True).last.click();assert page.locator('.top h1').inner_text()=='Nastavení'
 page.goto(venue_url+'#settings');page.locator('[data-work-access]').first.click()
 pinform=page.locator('#work-access-form');pinform.locator('[name=pin]').fill('1234');pinform.locator('button[type=submit]').click()
 page.get_by_role('heading',name='Work access saved').wait_for()
 page.locator('[data-auth-close]').click();page.locator('[data-start-work]').click();page.locator('[data-confirm-work]').click()
 page.wait_for_url('**/work');page.locator('#pin-form').wait_for()
 page.get_by_role('heading',name='Enter your PIN').wait_for()
 for digit in '1234':page.locator('[data-digit="'+digit+'"]').click()
 page.locator('#pin-form [type=submit]').click();page.locator('.work-product').first.wait_for()
 page.locator('.noira-language select').select_option('de');page.get_by_role('heading',name='Waren im Lager').wait_for()
 page.locator('.work-product').first.click();assert page.locator('#work-sheet-title').inner_text()=='Nastavení'
 page.locator('[data-work=close]').click();page.locator('[data-work=lock]').click();page.get_by_role('heading',name='PIN eingeben').wait_for()
 assert not errors,errors
 print('PASS: CZ/EN/DE, persisted preference, retained forms and Czech option values, original venue names, CSV import, daily filters and revisions, owner-only POS UI, mobile overflow')
 browser.close()
