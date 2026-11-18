/* Isolated server: NOIRA_TEST_URL, AdminOne / test-admin-one-password. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=process.env.NOIRA_TEST_URL||'http://127.0.0.1:8085';
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);await page.locator('[name=username]').fill('AdminOne');await page.locator('[name=password]').fill('test-admin-one-password');await page.locator('#auth-form [type=submit]').click();await page.locator('#owner-nav a').first().waitFor({state:'attached'});
  await page.goto(base+'/#create');await page.locator('#create-venue').waitFor();
  let releaseWrite,posts=0;
  await page.route('**/api/owner/venues',async route=>{if(route.request().method()==='POST'){posts++;await new Promise(resolve=>releaseWrite=resolve)}await route.continue()});
  const venueName='Motion QA '+Date.now();await page.locator('#create-venue [name=name]').fill(venueName);await page.locator('#create-venue [type=submit]').click();
  const submit=page.locator('#create-venue [type=submit]');await page.waitForFunction(()=>document.querySelector('#create-venue [type=submit]').hasAttribute('data-motion-busy'));
  assert.equal(await submit.getAttribute('aria-busy'),'true');assert.match(await submit.innerText(),/Ukládám/);
  await page.evaluate(()=>document.querySelector('#create-venue').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})));assert.equal(posts,1,'pending form must not submit twice');
  assert.equal(await page.locator('#motion-progress').count(),0);releaseWrite();await page.waitForURL('**/#venues');
  const card=page.locator('.venue-card').filter({hasText:venueName});await card.waitFor();await card.locator('[data-venue-manager]').click();
  assert(await card.evaluate(n=>n.classList.contains('motion-selected')),'selected venue has persistent highlight');
  await page.waitForFunction(()=>document.querySelector('.modal-content').getAnimations().some(a=>a.effect.getKeyframes().some(k=>String(k.clipPath).includes('44%'))));
  await page.locator('#venue-manager-form [name=managerFirstName]').fill('Jana');await page.locator('#venue-manager-form [name=managerLastName]').fill('Nováková');
  let fail=true;await page.route('**/api/owner/venues/*/manager',route=>fail?route.fulfill({status:400,json:{error:'Testovací chyba uložení'}}):route.continue());
  await page.locator('#venue-manager-form [type=submit]').click();await page.locator('#modal .form-error').filter({hasText:'Testovací chyba'}).waitFor();
  await page.waitForFunction(()=>!document.querySelector('#venue-manager-form [type=submit]').hasAttribute('data-motion-busy'));
  assert.equal(await page.locator('#venue-manager-form [data-motion-success]').count(),0,'failed saves must not show a check');
  assert.match(await page.locator('#venue-manager-form [type=submit]').innerText(),/Uložit manažera/);
  fail=false;await page.locator('#venue-manager-form [type=submit]').click();await page.locator('#venue-manager-form').waitFor({state:'detached'});await card.filter({hasText:'Jana Nováková'}).waitFor();
  assert.equal(await page.locator('#motion-progress').count(),0);
  let releaseTeam;await page.route('**/api/owner/team',async route=>{await new Promise(resolve=>releaseTeam=resolve);await route.continue()});
  await page.evaluate(()=>{window.motionRequests=Promise.all([BarometrAuth.api('/api/owner/team'),BarometrAuth.api('/api/owner/activity')])});
  await page.waitForTimeout(200);assert.equal(await page.locator('#motion-progress').count(),0);assert(releaseTeam);
  releaseTeam();await page.evaluate(()=>window.motionRequests);assert.equal(await page.locator('#motion-progress').count(),0);
  await page.locator('#owner-menu').click();await page.waitForTimeout(280);assert.equal(await page.locator('.owner-content').evaluate(n=>Math.round(new DOMMatrixReadOnly(getComputedStyle(n).transform).m41)),90);
  await page.keyboard.press('Escape');await page.waitForTimeout(280);assert.equal(await page.locator('.owner-content').evaluate(n=>getComputedStyle(n).transform),'none');
  await page.emulateMedia({reducedMotion:'reduce'});await page.locator('#owner-menu').click();assert.equal(await page.locator('.owner-content').evaluate(n=>getComputedStyle(n).transitionDuration),'0s');await page.keyboard.press('Escape');
  await page.setViewportSize({width:320,height:800});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'no mobile overflow');
  await page.setViewportSize({width:1440,height:1000});assert.equal(await page.locator('.owner-content').evaluate(n=>getComputedStyle(n).transform),'none');
  await page.unroute('**/api/owner/venues');
  await page.unroute('**/api/owner/team');
  // The shared module is also loaded by the scoped work terminal.
  const terminalVenue=await page.evaluate(async()=>{
   const owner=(await BarometrAuth.api('/api/me')).user.id;
   const venue=(await BarometrAuth.send('/api/owner/venues',{name:'Motion terminal '+Date.now()})).venue;
   await BarometrAuth.send('/api/owner/venues/'+venue.id+'/enter');return {id:venue.id,owner};
  });
  const prefix='/v/'+terminalVenue.id,request=page.context().request;
  const me=await (await request.get(base+prefix+'/api/me')).json(),headers={'X-CSRF-Token':me.csrf};
  assert.equal((await request.put(base+prefix+'/api/admin/users/'+terminalVenue.owner+'/work-access',{headers,data:{pin:'9876',allowedStores:null}})).status(),200);
  assert.equal((await request.post(base+prefix+'/api/work/device',{headers,data:{}})).status(),200);
  await page.goto(base+prefix+'/work');await page.locator('#pin-form').waitFor();
  for(const digit of '9876')await page.locator('[data-digit="'+digit+'"]').click();
  await page.locator('#pin-form [type=submit]').click();await page.locator('.work-header').waitFor();
  assert.deepEqual(errors,[]);console.log('PASS: real pending saves, duplicate-submit guard, failure without false success, selected card, center reveal, no percentage loading overlay, push drawer, reduced motion, mobile, desktop and work-terminal PIN login.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
