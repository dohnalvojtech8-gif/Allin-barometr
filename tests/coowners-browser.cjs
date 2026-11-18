const {chromium}=require('playwright'),assert=require('node:assert/strict');
const base=process.env.NOIRA_TEST_URL||'http://127.0.0.1:8085';
(async()=>{const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});try{
 const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 async function login(p,username,password){await p.goto(base);await p.locator('#auth-form [name=username]').fill(username);await p.locator('#auth-form [name=password]').fill(password);await p.locator('#auth-form [type=submit]').click();await p.locator('#owner-nav a').first().waitFor({state:'attached'});}
 await login(page,'AdminOne','test-admin-one-password');await page.goto(base+'/#team');await page.locator('[data-create-coowner]').waitFor();
 // Available before the first venue as well as in the mobile drawer flow.
 await page.setViewportSize({width:390,height:844});await page.locator('[data-create-coowner]').click();
 const form=page.locator('#coowner-form'),username='coowner_'+Date.now();
 for(const [key,value] of Object.entries({firstName:'Jana',lastName:'Společná',username,password:'coowner-browser-password',phone:'+420 777 111 222',email:'qa@example.cz'}))await form.locator('[name='+key+']').fill(value);
 await form.locator('[type=submit]').click();await form.waitFor({state:'detached'});await page.locator('tr').filter({hasText:username}).waitFor();
 const venue=await page.evaluate(async()=>{return (await BarometrAuth.send('/api/owner/venues',{name:'Co-owner browser '+Date.now()})).venue});
 const context=await browser.newContext({viewport:{width:390,height:844}}),other=await context.newPage();other.on('pageerror',e=>errors.push(e.message));
 await login(other,username,'coowner-browser-password');const card=other.locator('[data-venue-id="'+venue.id+'"]');await card.waitFor();await card.locator('[data-enter]').click();await other.waitForURL('**/v/'+venue.id+'/**');await other.locator('.owner-return-header').waitFor();
 await other.locator('.owner-return-header').click();await other.waitForURL(base+'/#overview');await other.locator('#owner-menu').click();await other.locator('#owner-nav a[href="#team"]').click();await other.locator('[data-create-coowner]').waitFor();
 assert.equal(await other.locator('[data-coowner-status]').count(),0,'only the primary owner manages suspension');
 const future=await other.evaluate(async()=>(await BarometrAuth.send('/api/owner/venues',{name:'Co-owner future '+Date.now()})).venue);
 await page.reload();await page.locator('[data-create-coowner]').waitFor();
 assert((await page.evaluate(async()=>(await BarometrAuth.api('/api/owner/venues')).venues.map(v=>v.id))).includes(future.id));
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'owner page overflow at '+width);await page.locator('[data-create-coowner]').click();assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'modal overflow at '+width);await page.keyboard.press('Escape');}
 await page.locator('tr').filter({hasText:username}).locator('[data-coowner-status]').click();await page.locator('#confirm-coowner-status').click();await page.locator('#confirm-coowner-status').waitFor({state:'detached'});
 assert.equal(await other.evaluate(async()=>{const r=await fetch('/api/me');return r.status}),401);
 assert.deepEqual(errors,[]);console.log('PASS: mobile co-owner creation, separate login, shared existing/future venues, return to owner panel, primary-only suspension, 320/390/1440px layout, no browser errors.');
 }finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
