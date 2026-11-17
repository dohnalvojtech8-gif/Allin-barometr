"""Run only against the isolated CI server; no production credentials or data."""
import os
import uuid
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:10000'

def login(page,username,password):
 page.goto(BASE);page.locator('[name=username]').fill(username);page.locator('[name=password]').fill(password);page.locator('#auth-form [type=submit]').click()

with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox']);errors=[]
 context=browser.new_context(viewport={'width':390,'height':844},service_workers='block')
 owner=context.new_page();owner.on('pageerror',lambda e:errors.append(str(e)))
 login(owner,'owner','ci-owner-test-password');owner.locator('#owner-nav a').first.wait_for(state='attached')
 headers={'X-CSRF-Token':owner.request.get(BASE+'/api/me').json()['csrf']}
 venue=owner.request.post(BASE+'/api/owner/venues',data={'name':'Analytika UI'},headers=headers).json()['venue']['id']
 response=owner.request.post(BASE+'/api/owner/venues/'+venue+'/enter',data={},headers=headers);assert response.status==200
 prefix=BASE+'/v/'+venue;vh={'X-CSRF-Token':owner.request.get(prefix+'/api/me').json()['csrf']}
 document={'stores':[{'id':'main','name':'Kuchyně'}],'products':[{'id':'flour','name':'Mouka','category':'Suroviny','store':'main','unit':'kg','kind':'weight','cost':0,'min':0,'tare':0,'capacity':0,'density':1}],'counts':[{'id':'opening','product':'flour','store':'main','qty':100,'at':'2026-01-01T10:00:00+00:00'}],'moves':[],'draft':None,'barInventories':[]}
 response=owner.request.put(prefix+'/api/stock',data={'revision':0,'data':document},headers=vh);assert response.status==200,response.text()
 suffix=uuid.uuid4().hex[:8]
 for username,pin,rights in [('worker_'+suffix,'2468',{}),('manager_'+suffix,'3579',{'inventory.review':True})]:
  response=owner.request.post(BASE+'/api/owner/venues/'+venue+'/members',data={'firstName':username,'lastName':'Test','username':username,'password':'browser-test-password','pin':pin,'permissions':rights},headers=headers);assert response.status==201,response.text()
 worker=browser.new_page(viewport={'width':390,'height':844},service_workers='block');worker.on('pageerror',lambda e:errors.append(str(e)))
 login(worker,'worker_'+suffix,'browser-test-password');worker.wait_for_url('**/v/'+venue+'/**');worker.locator('.account-name').wait_for()
 worker.goto(prefix+'/#stockcount/main');worker.locator('#start-count button').click();worker.locator('#count-form').wait_for()
 with worker.expect_response(lambda r:'/api/stock' in r.url and r.request.method=='PUT') as saved:
  worker.locator('[data-count=flour]').fill('90')
 assert saved.value.status==200
 worker.locator('#count-form button.primary').click();worker.locator('[data-stock-action=close-count]').click();worker.wait_for_url('**#reviews/**')
 worker.locator('[data-review-detail] table').wait_for();assert worker.locator('[data-review-decision]').count()==0
 pending=worker.request.get(prefix+'/api/inventory/submissions').json()['submissions'][0]['id']
 assert worker.request.get(prefix+'/api/stock').json()['data']['counts'][-1]['qty']==100
 manager=browser.new_page(viewport={'width':390,'height':844},service_workers='block');manager.on('pageerror',lambda e:errors.append(str(e)))
 login(manager,'manager_'+suffix,'browser-test-password');manager.wait_for_url('**/v/'+venue+'/**');manager.goto(prefix+'/#reviews/'+pending)
 decision=manager.locator('[data-review-decision]');decision.wait_for();decision.locator('[name=reason]').fill('Ověřte převod balení');decision.locator('[value=return]').click();manager.locator('[data-review-detail]').get_by_text('Vrácená k opravě',exact=True).wait_for()
 worker.reload();form=worker.locator('[data-review-edit]');form.wait_for();form.locator('[data-correct-key]').fill('95');form.locator('[name=reason]').fill('Balení přepočtena a ověřena');form.locator('button').click();worker.locator('[data-review-detail]').get_by_text('Čeká na schválení',exact=True).wait_for()
 manager.reload();decision=manager.locator('[data-review-decision]');decision.locator('[value=approve]').click();manager.locator('[data-review-detail]').get_by_text('Schválená',exact=True).wait_for()
 current=manager.request.get(prefix+'/api/stock').json();assert next(r for r in current['data']['counts'] if r.get('reviewId')==pending)['qty']==95
 assert manager.request.get(BASE+'/api/owner/analytics').status==401
 owner.goto(BASE+'/#comparison');owner.locator('#owner-intelligence h3').filter(has_text='1. Vývoj manka').wait_for();owner.locator('#owner-intelligence h3').filter(has_text='4. Tržby a marže').wait_for()
 assert owner.locator('#owner-nav a').count()==7
 owner.locator('#owner-intelligence details').evaluate('(el)=>el.open=true');recipe=owner.locator('[data-recipe-form]');recipe.locator('[name=venue]').select_option(venue);recipe.locator('[name=salesCode]').fill('DISH');recipe.locator('[name=from]').fill('2026-01-01');recipe.locator('[data-quantity]').fill('0.25');recipe.locator('[name=reason]').fill('Výchozí ověřená receptura');recipe.locator('button.primary').click()
 owner.locator('#owner-intelligence td').filter(has_text='DISH').first.wait_for()
 owner.locator('#owner-intelligence details').evaluate('(el)=>el.open=true');imports=owner.locator('[data-item-import]');imports.locator('[name=venue]').select_option(venue);imports.locator('[name=from]').fill('2026-01-01');imports.locator('[name=to]').fill('2026-01-01')
 imports.locator('[name=file]').set_input_files({'name':'sales.csv','mimeType':'text/csv','buffer':b'prodej_id;datum_cas;produkt_pokladny;pocet\n1;2026-01-01T20:00:00+01:00;DISH;2\n'});imports.locator('[name=complete]').check();imports.locator('button').click()
 owner.locator('#owner-intelligence summary').wait_for()
 owner.wait_for_function('!document.querySelector("[data-item-import] [name=file]").files.length')
 assert owner.evaluate('document.documentElement.scrollWidth<=innerWidth')
 Path('/tmp/noira-ci-artifacts').mkdir(exist_ok=True)
 owner.screenshot(path='/tmp/noira-ci-artifacts/owner-analytics-mobile.png',full_page=True)
 worker.screenshot(path='/tmp/noira-ci-artifacts/employee-review-mobile.png',full_page=True)
 assert not errors,errors
 print('PASS: employee UI submits without PIN, manager return and approval, employee correction, approved balance, owner-only finance, recipe and POS item import, mobile layout')
 browser.close()
