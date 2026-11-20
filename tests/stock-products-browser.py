"""Product setup and bottle reconciliation on an isolated test server only."""
import os
import uuid
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:10000'
ARTIFACTS=Path('/tmp/noira-ci-artifacts');ARTIFACTS.mkdir(exist_ok=True)

with sync_playwright() as p:
 options={'headless':True,'args':['--no-sandbox']}
 if os.getenv('NOIRA_CHROMIUM'):options['executable_path']=os.environ['NOIRA_CHROMIUM']
 browser=p.chromium.launch(**options)
 context=browser.new_context(viewport={'width':390,'height':844},service_workers='block')
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(BASE);page.locator('[name=username]').fill('owner');page.locator('[name=password]').fill(os.getenv('NOIRA_TEST_PASSWORD','ci-owner-test-password'));page.locator('#auth-form button[type=submit]').click()
 page.locator('#owner-nav a').first.wait_for(state='attached')
 h={'X-CSRF-Token':page.request.get(BASE+'/api/me').json()['csrf']}
 result=page.request.post(BASE+'/api/owner/venues',data={'name':'Produkty a lahve UI '+uuid.uuid4().hex[:6]},headers=h);assert result.status==201,result.text()
 venue=result.json()['venue']['id'];page.request.post(BASE+'/api/owner/venues/'+venue+'/enter',data={},headers=h)
 prefix=BASE+'/v/'+venue;vh={'X-CSRF-Token':page.request.get(prefix+'/api/me').json()['csrf']}
 page.goto(prefix+'/#warehouse/main');page.locator('[data-stock-action=add-product]').click()
 form=page.locator('#stock-product-form');form.wait_for()
 assert form.locator('[name=category] option').all_text_contents()==['Obal','Sud','Lihoviny']
 assert form.locator('[name=unit] option').evaluate_all('(els)=>els.map(e=>e.value)')==['ks','l','ml','kg','balení']
 assert not form.locator('[data-weight-parameters]').evaluate('(e)=>e.open')
 assert not form.locator('[data-keg-section]').is_visible()
 assert form.locator('select,input').first.get_attribute('name')=='category'
 form.locator('[name=name]').fill('Přepravka');form.locator('[type=submit]').click();form.wait_for(state='hidden')
 assert page.request.get(prefix+'/api/stock').json()['data']['counts'][0]['qty']==0
 # Category settings retain products and allow customer-defined categories.
 page.goto(prefix+'/#warehouse/main');page.locator('[data-stock-action=product-categories]').click()
 categories=page.locator('#stock-categories-form');categories.locator('[data-add-category]').click()
 categories.locator('[data-category-name]').last.fill('Suroviny');categories.locator('[data-category-kind]').last.select_option('weight');categories.locator('[type=submit]').click();categories.wait_for(state='hidden')
 page.locator('[data-stock-action=add-product]').click();form=page.locator('#stock-product-form');form.wait_for()
 form.locator('[name=category]').select_option('Sud');assert form.locator('[data-keg-section]').is_visible()
 assert form.locator('[data-keg-select] option').count()==1
 form.locator('[name=name]').fill('Vlastní sud 50 l');form.locator('[data-weight-parameters] summary').click()
 for key,value in [('capacity','50'),('tare','7'),('fullWeightKg','57')]:form.locator('[name='+key+']').fill(value)
 form.locator('[name=openingQty]').fill('9');form.locator('[data-keg-state=empty]').check();assert form.locator('[name=openingQty]').input_value()=='9'
 form.locator('[type=submit]').click();form.wait_for(state='hidden')
 document=page.request.get(prefix+'/api/stock').json();keg=next(r for r in document['data']['products'] if r['kind']=='keg')
 page.goto(prefix+'/#weigh/main/'+keg['id']);page.locator('#weight-form').wait_for();page.locator('#weight-form [name=display]').fill('32');page.locator('#weight-form button[type=submit],#weight-form button.primary').last.click()
 page.locator('[data-stock-action=save-weight]').click();page.wait_for_timeout(300)
 assert page.request.get(prefix+'/api/stock/resources?store=main').json()['kegs'][0]['measured']
 page.goto(prefix+'/#warehouse/main');page.locator('[data-stock-action=add-product]').click();form.wait_for()
 form.locator('[name=category]').select_option('Sud');form.locator('[name=name]').fill('Můj vlastní název')
 form.locator('[data-keg-select]').select_option(index=1);assert form.locator('[name=name]').input_value()=='Můj vlastní název'
 assert not form.locator('[data-weight-parameters]').evaluate('(e)=>e.open')
 form.locator('[data-keg-state=full]').check();assert form.locator('[name=openingQty]').input_value()=='0'
 page.locator('#stock-dialog').evaluate('(e)=>e.close()')
 # Link only an activated bottle and its actual catalog size.
 assert page.request.post(prefix+'/api/unlocks',data={'productId':'amundsen'},headers=vh).status==200
 page.locator('[data-stock-action=add-product]').click();form.wait_for();form.locator('[name=category]').select_option('Lihoviny')
 assert form.locator('[name=catalogProductId] option').count()==2
 form.locator('[name=catalogProductId]').select_option('amundsen');form.locator('[name=catalogCapacityMl]').select_option('500')
 form.locator('[name=name]').fill('Amundsen 500 ml sklad');form.locator('[name=openingQty]').fill('5');form.locator('[type=submit]').click();form.wait_for(state='hidden')
 sku=next(r for r in page.request.get(prefix+'/api/stock').json()['data']['products'] if r.get('catalogProductId')=='amundsen')
 def measurement(ml):
  s=page.request.get(prefix+'/api/me').json()['state'];s['rows']=[{'id':'bottle-ui','productId':'amundsen','capacity':500,'label':'Vodka UI','start':500,'ml':ml,'sold40':0,'sold20':0,'otherMl':0}]
  s['inventoryPlan']={'runId':str(uuid.uuid4()),'entries':[{'id':'ui-entry','productId':'amundsen','capacity':500,'rowId':'bottle-ui','status':'done'}]}
  r=page.request.put(prefix+'/api/state',data=s,headers=vh);assert r.status==200,r.text()
 measurement(340);page.goto(prefix+'/#barreview');page.reload();page.locator('.bottle-size-summary').wait_for()
 text=page.locator('#bar-stock-review').inner_text();assert '340 ml' in text and '5 × 500 ml' in text and '2\u00a0840 ml' in text,text
 assert page.locator('.bottle-total strong').inner_text()=='6'
 page.locator('[data-edit-bar]').click();assert page.locator('[data-stock-action=close-bar]').is_disabled()
 page.locator('[data-edit-bar-item]').fill('320');page.locator('[name=reason]').fill('Ruční kontrola hladiny před uložením');page.locator('#bar-review-edit [type=submit]').click()
 page.locator('.bottle-size-summary').filter(has_text='320 ml').wait_for()
 page.screenshot(path=str(ARTIFACTS/'bottle-summary-mobile.png'),full_page=True)
 for width in [320,390,1440]:
  page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),width
 for lang,expected in [('en','Total bottles'),('de','Flaschen insgesamt'),('cs','Lahve celkem')]:
  page.evaluate('(lang)=>NoiraI18n.set(lang)',lang);assert expected in page.locator('#bar-stock-review').inner_text()
 page.locator('[data-stock-action=close-bar]').click();page.wait_for_url('**#audit/**');page.locator('#app').get_by_text('Uložený přehled lahví',exact=True).wait_for()
 assert page.request.get(prefix+'/api/me').json()['state']['rows'][0]['ml']==320
 # A later empty measurement is counted once, archived and absent from active state.
 measurement(0);page.goto(prefix+'/#barreview');page.reload();page.locator('.bottle-size-summary').wait_for()
 assert page.locator('.bottle-inventory-stats>div').nth(3).locator('strong').inner_text()=='1'
 page.locator('[data-stock-action=close-bar]').click();page.wait_for_url('**#audit/**');page.locator('#app').get_by_text('Archivované prázdné lahve',exact=True).wait_for()
 current=page.request.get(prefix+'/api/me').json()['state'];assert current['rows']==[] and current['inventoryPlan']['entries']==[]
 saved=page.request.get(prefix+'/api/stock').json()['data'];assert next(r for r in saved['counts'] if r['product']==sku['id'])['qty']==5
 assert page.locator('#nav a[href="#menu"]').count()==0
 page.goto(prefix+'/#menu');assert page.locator('#app [data-function-card]').count()==0;page.locator('#app .overview-hero').wait_for()
 page.goto(BASE);page.locator('[href="#menu"]').click();page.locator('#owner-main h1').filter(has_text='Všechny funkce').wait_for();assert page.locator('#owner-main .venue-grid a').count()==9
 assert not errors,errors
 print('PASS: custom categories, all units, zero opening stock, saved keg calibration, independent weight/quantity, activated liquor, size-specific bottle summary, editable confirmation, one-time depletion, archival, owner-only menu, translations and mobile widths')
 browser.close()
