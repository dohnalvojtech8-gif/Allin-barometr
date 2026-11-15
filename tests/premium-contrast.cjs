// Run with Playwright installed: node tests/premium-contrast.cjs
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const web=path.join(__dirname,'../server/web');
const cases=[
 ['Form labels','<form><label data-check>Jméno zaměstnance</label></form>'],
 ['Form error','<div class="form-error" data-check>Vyplňte jméno</div>'],
 ['Auth error','<div id="auth-error" data-check>Nesprávné heslo</div>'],
 ['Dialog','<div class="modal-content"><h3 data-check>Nový zaměstnanec</h3><p data-check>Nastavení přístupu</p><form><label data-check>Pozice</label></form></div>'],
 ['Destructive action','<button class="danger" data-check>Smazat sklad</button>'],
 ['Link button','<a class="button" data-check>Otevřít sklad</a>'],
 ['Primary link','<a class="button primary" data-check>Pokračovat</a>'],
 ['Photo label','<div class="photo-action"><label class="button" data-check>Nahrát fotografii</label></div>'],
 ['Volume active','<div class="volumes"><button class="active" data-check>0,04 l</button></div>'],
 ['Shop active','<div class="shop-view-tabs"><button class="selected" data-check>Balíčky</button></div>'],
 ['Step','<span class="step-number" data-check>1</span>'],
 ['Locked notice','<div class="locked-notice" data-check>Odemknout funkci</div>'],
 ['Bundle','<div class="bundle-card bundle-featured"><span class="bundle-card-top" data-check>Výhodná sada</span><div class="bundle-price"><del data-check>200 Kč</del><strong data-check>150 Kč</strong></div><details open data-check>Obsah balíčku</details></div>'],
 ['Warehouse menu','<details class="warehouse-options" open><summary data-check>Možnosti skladu</summary></details>'],
 ['Dashboard caption','<div class="dashboard-receipts"><small data-check>Poslední příjem</small></div>'],
 ['Chart legend','<span class="chart-last" data-check>Aktuální období</span><span class="chart-previous" data-check>Minulé období</span>'],
 ['Section hover','<div class="section-rail"><nav id="section-tabs"><a href="#" data-hover data-check>Inventura</a></nav></div>'],
 ['Warehouse fill','<div class="store-colored" data-store-style="fill" style="--store-color:#000000"><small data-check>Stav zásob</small><strong data-check>Hlavní bar</strong></div>'],
 ['Scanner','<div class="scanner"><p data-check>Vyberte láhev</p><form><label data-check>Množství</label></form><div class="info"><div><span data-check>Objem</span></div></div><div class="shotbox"><strong data-check>12 panáků</strong></div><button class="primary" data-check>Uložit</button></div>'],
 ['Live camera','<div class="scanner camera-active"><div class="scan-header"><h3 data-check>Skenování</h3></div><div class="scan-button-row"><button data-check>Vybrat láhev</button></div><div class="scan-live-hint" data-check>Zaměřte hladinu</div></div>'],
 ['Sidebar','<aside id="sidebar"><nav id="nav"><a class="active"><span data-check>Sklady</span></a></nav><small data-check>Váš podnik</small></aside>'],
 ['Hero','<div class="overview-hero"><p data-check>Přehled podniku</p><a class="button primary" data-check>Nová inventura</a></div>']
];
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']});
 try {
 const page=await browser.newPage();
 let checks=0;
 for(const width of [390,768,1440]) for(const [name,html] of cases){
  await page.setViewportSize({width,height:1000});
  await page.setContent('<body>'+html+'</body>');
  for(const file of ['style.css','pwa.css','premium-theme.css']) await page.addStyleTag({content:fs.readFileSync(path.join(web,file),'utf8')});
  if(await page.locator('[data-hover]').isVisible()) await page.locator('[data-hover]').hover();
  const results=await page.locator('[data-check]').evaluateAll(nodes=>{
   const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');
   function rgba(value){ctx.clearRect(0,0,1,1);ctx.fillStyle=value;ctx.fillRect(0,0,1,1);return [...ctx.getImageData(0,0,1,1).data].map((x,i)=>i===3?x/255:x);}
   function over(f,b){return [0,1,2].map(i=>f[i]*f[3]+b[i]*(1-f[3])).concat(1);}
   function luminance(c){const s=c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4});return s[0]*.2126+s[1]*.7152+s[2]*.0722;}
   return nodes.map(el=>{
    const ancestors=[];for(let p=el;p;p=p.parentElement)ancestors.unshift(p);
    let bg=[255,255,255,1];for(const p of ancestors)bg=over(rgba(getComputedStyle(p).backgroundColor),bg);
    const fg=over(rgba(getComputedStyle(el).color),bg),a=luminance(fg),b=luminance(bg);
    return {text:el.textContent,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
   });
  });
  for(const r of results){assert(r.ratio>=4.5,`${width}px ${name}: ${r.text} contrast ${r.ratio.toFixed(2)} < 4.5`);checks++;}
 }
 console.log(`PASS: ${checks} text contrast checks at 390, 768 and 1440 px, including selected, open, hover and camera states.`);
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
