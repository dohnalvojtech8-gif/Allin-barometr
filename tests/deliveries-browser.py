"""Isolated mobile receipt, owner consolidation, invoice and bar-transfer regression."""
import os,uuid,base64
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:10000';ARTIFACTS=Path('/tmp/noira-ci-artifacts');ARTIFACTS.mkdir(exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox'],**({'executable_path':os.environ['NOIRA_CHROMIUM']} if os.getenv('NOIRA_CHROMIUM') else {}))
 page=browser.new_page(viewport={'width':390,'height':844},service_workers='block');errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(BASE);page.locator('[name=username]').fill('owner');page.locator('[name=password]').fill(os.getenv('NOIRA_TEST_PASSWORD','ci-owner-test-password'));page.locator('#auth-form [type=submit]').click();page.locator('#owner-nav a').first.wait_for(state='attached')
 h={'X-CSRF-Token':page.request.get(BASE+'/api/me').json()['csrf']};suffix=uuid.uuid4().hex[:6]
 venue=page.request.post(BASE+'/api/owner/venues',data={'name':'Dodávky UI '+suffix},headers=h).json()['venue']['id'];page.request.post(BASE+'/api/owner/venues/'+venue+'/enter',data={},headers=h)
 prefix=BASE+'/v/'+venue;vh={'X-CSRF-Token':page.request.get(prefix+'/api/me').json()['csrf']}
 doc=page.request.get(prefix+'/api/stock').json();doc['data']['stores'] += [{'id':'kitchen','name':'Kuchyně'},{'id':'cellar','name':'Sklep'}];assert page.request.put(prefix+'/api/stock',data=doc,headers=vh).status==200
 assert page.request.post(prefix+'/api/unlocks',data={'productId':'amundsen'},headers=vh).status==200
 products=[]
 for sid,name,unit in [('main','Vodka 500 ml','ks'),('kitchen','Mouka','kg'),('cellar','Sud','l')]:
  item={'id':str(uuid.uuid4()),'store':sid,'name':name,'category':'Lihoviny' if sid=='main' else 'Obal','kind':'liquid' if sid=='main' else 'piece','unit':unit,'cost':0,'min':0,'tare':0,'capacity':.5 if sid=='main' else 0,'density':1}
  if sid=='main':item.update(catalogProductId='amundsen',catalogCapacityMl=500)
  result=page.request.post(prefix+'/api/stock/products',data={'product':item,'openingQty':0,'revision':page.request.get(prefix+'/api/stock').json()['revision']},headers=vh);assert result.status==201,result.text();products.append(item)
 page.goto(prefix+'/#receive');form=page.locator('#multi-delivery-form');form.wait_for();form.locator('[name=supplier]').fill('Dodavatel UI '+suffix);form.locator('[name=reference]').fill('FA-UI-'+suffix)
 for sid in ['kitchen','cellar']:form.locator('[name=nextStore]').select_option(sid);form.locator('[data-add-delivery-store]').click();page.locator('[data-delivery-store="'+sid+'"]').wait_for()
 for index,item in enumerate(products):page.locator('[data-delivery-qty="'+item['store']+'|'+item['id']+'"]').fill(str(index+5))
 assert form.locator('[data-delivery-totals]').inner_text()=='3 položek · 3 skladů'
 data=page.evaluate("()=>{const c=document.createElement('canvas');c.width=700;c.height=900;const x=c.getContext('2d');x.fillStyle='white';x.fillRect(0,0,700,900);x.fillStyle='black';x.font='30px sans-serif';x.fillText('FAKTURA TEST',40,70);x.fillText('Dodavatel UI',40,140);return c.toDataURL('image/jpeg',.85)}")
 image=ARTIFACTS/'invoice-fixture.jpg';image.write_bytes(base64.b64decode(data.split(',',1)[1]));form.locator('details').first.locator('summary').click();form.locator('[data-invoice-files]').set_input_files(str(image));form.locator('[data-draft-photos] img').wait_for()
 form.locator('[type=submit]').click();dialog=page.locator('#delivery-dialog');dialog.get_by_role('heading',name='Kontrola celé dodávky').wait_for();assert dialog.locator('.delivery-review-store').count()==3
 dialog.locator('[data-confirm-delivery]').click();page.wait_for_url('**#delivery/**');page.locator('#delivery-detail .delivery-store-detail').last.wait_for();assert page.locator('.delivery-store-detail').count()==3
 assert page.locator('#delivery-detail .delivery-photos img').count()==1
 assert page.locator('#delivery-detail .delivery-photos img').evaluate('(e)=>e.complete&&e.naturalWidth>0')
 id=page.url.split('#delivery/')[1];assert len(page.request.get(prefix+'/api/stock').json()['data']['moves'])==3
 for width in [320,390,1440]:page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),width
 page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(300);page.screenshot(path=str(ARTIFACTS/'delivery-detail-light-mobile.png'),full_page=True,animations='disabled')
 assert page.evaluate('getComputedStyle(document.body).backgroundColor')=='rgb(244, 247, 251)'
 page.goto(prefix+'/#deliveries');page.locator('.delivery-row').wait_for();assert page.locator('.delivery-row').count()==1
 page.locator('[name=q]').fill('nicnenajdu');page.locator('#delivery-filters [type=submit]').click();page.locator('#delivery-history').get_by_text('Žádné dodávky neodpovídají filtrům.',exact=True).wait_for()
 page.locator('[data-clear-deliveries]').click();page.locator('.delivery-row').wait_for()
 for lang,title in [('en','Delivery history'),('de','Lieferhistorie'),('cs','Historie dodávek')]:page.evaluate('(lang)=>NoiraI18n.set(lang)',lang);assert title in page.locator('#app').inner_text()
 page.goto(prefix+'/#warehouse/main');page.locator('[data-stock-action=to-bar]').click();transfer=page.locator('#bar-transfer-form');transfer.wait_for();transfer.locator('[name=bottles]').fill('2');assert '2 × 500 ml' in transfer.inner_text();transfer.locator('[type=submit]').click();transfer.wait_for(state='hidden')
 stock=page.request.get(prefix+'/api/stock').json()['data'];assert stock['moves'][-1]['qty']==-2 and stock['moves'][-1]['transferTarget']=='bar'
 state=page.request.get(prefix+'/api/me').json()['state'];assert len(state['rows'])==2 and all(r['ml']==500 for r in state['rows'])
 page.goto(prefix+'/#movements');page.locator('#app').get_by_text('Na bar: +2 × 500 ml',exact=True).wait_for()
 page.goto(BASE+'/#deliveries');page.locator('[data-choose-venue=all]').click();page.locator('[data-pick-venue]').wait_for();page.locator('[name=q]').fill('UI '+suffix);page.locator('#delivery-filters [type=submit]').click();page.wait_for_function('(suffix)=>document.querySelectorAll(".delivery-row").length===1&&document.querySelector(".delivery-row").textContent.includes(suffix)',arg=suffix)
 assert page.locator('.delivery-row').count()==1 and page.locator('.delivery-venue-tag').inner_text()=='Dodávky UI '+suffix
 page.locator('[data-pick-colors]').click();color=page.locator('[data-color-venue="'+venue+'"]');color.evaluate("e=>{e.value='#db2777';e.dispatchEvent(new Event('change',{bubbles:true}))}")
 page.wait_for_function("()=>document.querySelector('.delivery-row')?.style.getPropertyValue('--venue-color')==='#db2777'");page.locator('#delivery-dialog [data-close-dialog]').click();page.screenshot(path=str(ARTIFACTS/'owner-deliveries-light-mobile.png'),full_page=True,animations='disabled')
 page.locator('.delivery-row').click();page.locator('#delivery-detail .delivery-store-detail').last.wait_for();assert page.locator('#delivery-detail .delivery-store-detail').count()==3
 assert page.locator('#delivery-detail .delivery-photos img').evaluate('(e)=>e.complete&&e.naturalWidth>0')
 schedule={'timezone':'Europe/Prague','days':{str(i):{'closed':False,'open':'00:00','close':'00:00'} for i in range(7)}}
 assert page.request.put(BASE+'/api/owner/venues/'+venue+'/controls',data={'openingHours':schedule},headers=h).status==200
 page.goto(BASE+'/#venues');card=page.locator('[data-venue-id="'+venue+'"]');card.locator('.opening-state.is-open').wait_for();assert card.evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(255, 255, 255)';assert 'Nonstop' in card.locator('.opening-widget').inner_text()
 page.goto(prefix+'/#warehouse/main');page.locator('.app-header .opening-state.is-open').wait_for()
 for day in schedule['days'].values():day['closed']=True
 assert page.request.put(BASE+'/api/owner/venues/'+venue+'/controls',data={'openingHours':schedule},headers=h).status==200
 page.evaluate('()=>NoiraOpening.refresh()');page.locator('.app-header .opening-state.is-closed').wait_for()
 page.screenshot(path=str(ARTIFACTS/'warehouse-light-mobile.png'),full_page=True,animations='disabled')
 assert not errors,errors
 print('PASS: 3-store atomic delivery, invoice compression/display, searchable history, light mobile theme, translations, 2-click bottle transfer, audit visibility and owner colour consolidation')
 browser.close()
