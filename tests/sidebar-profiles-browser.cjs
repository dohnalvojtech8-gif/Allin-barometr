/* Run against an isolated test server with AdminOne / test-admin-one-password. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=process.env.NOIRA_TEST_URL||'http://127.0.0.1:8085';
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try {
 const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base);await page.locator('[name=username]').fill('AdminOne');await page.locator('[name=password]').fill('test-admin-one-password');await page.locator('#auth-form [type=submit]').click();
 await page.locator('#owner-nav a').first().waitFor({state:'attached'});
 async function drawer(p,owner){
  const side=p.locator(owner?'#owner-sidebar':'#sidebar'),menu=p.locator(owner?'#owner-menu':'#menu-toggle');
  await menu.click();await p.waitForTimeout(260);assert.equal(await side.evaluate(e=>Math.round(e.getBoundingClientRect().left)),0);
  await side.locator('.noira-language select').selectOption('en');assert.equal(await p.locator('html').getAttribute('lang'),'en');
  assert.equal(await p.locator('.app-header .noira-language,.owner-header .noira-language').count(),0);
  assert.match(await side.innerText(),/Vytvořeno 2026 ® CTS customsis/);
  await side.locator('[data-logout]').focus();await p.keyboard.press('Tab');assert.equal(await p.evaluate(()=>document.activeElement.id),owner?'owner-sidebar-close':'sidebar-close');
  await p.keyboard.press('Escape');assert.equal(await menu.getAttribute('aria-expanded'),'false');
  await menu.click();await p.waitForTimeout(260);await p.mouse.click(375,400);assert.equal(await menu.getAttribute('aria-expanded'),'false');
  await menu.click();await p.waitForTimeout(260);await side.locator('a').first().click();assert.equal(await menu.getAttribute('aria-expanded'),'false');
  await p.setViewportSize({width:1440,height:1000});await p.waitForTimeout(260);assert.equal(await side.evaluate(e=>e.inert),false);assert.equal(await side.getAttribute('aria-hidden'),'false');
  await side.locator('.noira-language select').selectOption('cs');await p.setViewportSize({width:390,height:844});
 }
 await drawer(page,true);
 await page.goto(base+'/#create');await page.locator('#create-venue [name=name]').fill('QA bar '+Date.now());await page.locator('[name=managerFirstName]').fill('Jana');await page.locator('[name=managerLastName]').fill('Nováková');await page.locator('#create-venue [type=submit]').click();
 const card=page.locator('.venue-card').last();await card.waitFor();assert.match(await card.locator('.venue-manager').innerText(),/Jana Nováková/);
 const venueId=await card.locator('[data-enter]').getAttribute('data-enter');
 await card.locator('[data-venue-manager]').click();await page.locator('#venue-manager-form [name=managerFirstName]').fill('Petr');await page.locator('#venue-manager-form [name=managerLastName]').fill('Dvořák');await page.locator('#venue-manager-form [type=submit]').click();await page.locator('#venue-manager-form').waitFor({state:'detached'});assert.match(await page.locator('.venue-card').last().innerText(),/Petr Dvořák/);
 await page.goto(base+'/#team');await page.locator('[data-hub-create-employee]').click();const f=page.locator('#employee-form');await f.locator('[name=venueId]').selectOption(venueId);
 const username='qa_'+Date.now();for(const [name,value] of Object.entries({firstName:'Tereza',lastName:'Nováková',phone:'+420 777 123 456',email:'tereza@example.cz',username,password:'employee-test-password',pin:'1234'}))await f.locator(`[name=${name}]`).fill(value);
 await f.locator('[type=submit]').click();await page.locator('#employee-form').waitFor({state:'detached'});await page.locator('#modal [data-auth-close]').last().click();
 const row=page.locator('.hub-table tbody tr').filter({hasText:username});await row.waitFor();assert.match(await row.innerText(),/tereza@example.cz/);assert.equal(await row.locator('td').nth(3).innerText().then(s=>s.includes(String(new Date().getFullYear()))),true);
 await row.locator('[data-hub-member]').click();assert.match(await page.locator('.employee-facts').innerText(),/\+420 777 123 456/);await page.locator('.modal-close').click();
 // Establish the venue's scoped owner session before opening its user directory.
 await page.goto(base+'/#venues');await page.locator(`[data-enter="${venueId}"]`).click();await page.waitForURL('**/v/'+venueId+'/');await page.goto(base+'/v/'+venueId+'/#users');
 const accountRow=page.locator('#users-body tr').filter({hasText:username});await accountRow.waitFor();assert.match(await accountRow.innerText(),new RegExp(String(new Date().getFullYear())));await accountRow.locator('[data-user-detail]').click();await page.locator('.employee-contacts').waitFor();assert.match(await page.locator('.employee-contacts').innerText(),/tereza@example.cz/);
 const staff=await browser.newPage({viewport:{width:390,height:844}});staff.on('pageerror',e=>errors.push(e.message));await staff.goto(base+'/v/'+venueId+'/');await staff.locator('[name=username]').fill(username);await staff.locator('[name=password]').fill('employee-test-password');await staff.locator('#auth-form [type=submit]').click();await staff.locator('#nav a').first().waitFor({state:'attached'});await drawer(staff,false);
 await staff.locator('#menu-toggle').click();await staff.locator('#sidebar [data-logout]').click();await staff.locator('#auth-form').waitFor();
 assert.deepEqual(errors,[]);console.log('PASS: owner and employee mobile/desktop navigation, language, logout, manager creation/edit, contacts and creation dates in lists/details.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
