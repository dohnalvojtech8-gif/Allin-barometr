const {chromium}=require('playwright'),assert=require('node:assert/strict');
const base=process.env.NOIRA_TEST_URL||'http://127.0.0.1:8085';
(async()=>{const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});try{
 const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(base);await page.locator('[name=username]').fill('AdminOne');await page.locator('[name=password]').fill('test-admin-one-password');await page.locator('#auth-form [type=submit]').click();await page.locator('#owner-nav a').first().waitFor({state:'attached'});
 const data=await page.evaluate(async()=>{const venue=(await BarometrAuth.send('/api/owner/venues',{name:'Return QA '+Date.now()})).venue;const username='return_'+Date.now();await BarometrAuth.send('/api/owner/venues/'+venue.id+'/members',{firstName:'Test',lastName:'Staff',username,password:'employee-test-password',pin:'1234'});return {id:venue.id,username}});
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:900});const url=await page.evaluate(async id=>(await BarometrAuth.send('/api/owner/venues/'+id+'/enter')).url,data.id);await page.goto(base+url+'#warehouse/main');await page.locator('.owner-return-header').waitFor();
  assert.equal(await page.locator('.owner-return-header').getAttribute('href'),'/#overview');assert.equal(await page.locator('.owner-return-sidebar').count(),1);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'no overflow at '+width);
  if(width<760){await page.locator('#menu-toggle').click();await page.locator('.owner-return-sidebar').click()}else await page.locator('.owner-return-header').click();
  await page.waitForURL(base+'/#overview');await page.locator('#owner-nav a').first().waitFor({state:'attached'});assert.equal(await page.locator('#auth-form').count(),0);
  assert.equal((await page.context().request.get(base+'/api/me')).status(),200);assert.equal((await page.context().request.get(base+'/v/'+data.id+'/api/me')).status(),200);
 }
 const employee=await browser.newPage({viewport:{width:390,height:844}});employee.on('pageerror',e=>errors.push(e.message));await employee.goto(base+'/v/'+data.id+'/');await employee.locator('[name=username]').fill(data.username);await employee.locator('[name=password]').fill('employee-test-password');await employee.locator('#auth-form [type=submit]').click();await employee.locator('#nav a').first().waitFor({state:'attached'});assert.equal(await employee.locator('.owner-return-header,.owner-return-sidebar').count(),0);
 const request=page.context().request,prefix='/v/'+data.id;const scopedMe=await (await request.get(base+prefix+'/api/me')).json(),vh={'X-CSRF-Token':scopedMe.csrf};
 assert.equal((await request.put(base+prefix+'/api/admin/users/'+scopedMe.user.id+'/work-access',{headers:vh,data:{pin:'9876',allowedStores:null}})).status(),200);
 assert.equal((await request.post(base+prefix+'/api/work/device',{headers:vh,data:{}})).status(),200);
 async function enterPin(pin){await page.goto(base+prefix+'/work');await page.locator('#pin-form').waitFor();for(const digit of pin)await page.locator('[data-digit="'+digit+'"]').click();await page.locator('#pin-form [type=submit]').click();await page.locator('.work-header').waitFor();await page.locator('[data-work=menu]').click()}
 await enterPin('9876');await page.locator('[data-work=owner-panel]').click();await page.waitForURL(base+'/#overview');await page.locator('#owner-nav a').first().waitFor({state:'attached'});assert.equal((await (await request.get(base+prefix+'/api/work/session')).json()).locked,true,'terminal must be locked before returning');
 await enterPin('1234');assert.equal(await page.locator('[data-work=owner-panel]').count(),0,'no owner return control in employee terminal menu');
 assert.deepEqual(errors,[]);console.log('PASS: header/sidebar return at desktop, 390px and 320px; central and venue sessions preserved; terminal return locks PIN session; no owner controls for employee.');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
