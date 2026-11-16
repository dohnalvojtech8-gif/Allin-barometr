"""Check the rendered login surfaces and readable text at desktop and mobile widths.

Local server only. No accounts, cookies, or production data are used.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

STYLE_TARGETS=['.auth-card','.auth-card h1','.auth-card p','.auth-logo','.auth-tabs button','.auth-card label','.auth-card input','.auth-card button.primary','.auth-note','.auth-card .eyebrow']

MEASURE=r'''selectors=>{
 function rgb(value){const v=value.match(/[\d.]+/g);return v?v.slice(0,3).map(Number):[0,0,0]}
 function luminance(color){return rgb(color).map(v=>{v/=255;return v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4)}).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0)}
 function background(el){while(el){const bg=getComputedStyle(el).backgroundColor;if(bg!=='transparent'&&bg!=='rgba(0, 0, 0, 0)')return bg;el=el.parentElement}return 'rgb(17, 19, 21)'}
 return selectors.flatMap(selector=>[...document.querySelectorAll(selector)].map(el=>{const fg=getComputedStyle(el).color,bg=background(el),a=luminance(fg),b=luminance(bg);return {selector,foreground:fg,background:bg,contrast:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)}}))
}'''

def check(page,label):
 values=page.evaluate(MEASURE,STYLE_TARGETS)
 assert values,(label,'No login elements rendered')
 for item in values:assert item['contrast']>=4.5,(label,item)
 assert page.locator('.auth-card').evaluate('el=>getComputedStyle(el).backgroundColor')=='rgb(29, 32, 35)',label
 assert page.locator('#auth-root').evaluate('el=>getComputedStyle(el).backgroundImage')=='none',label
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),label
 return min(v['contrast'] for v in values)

with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(service_workers="block");errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
 results=[]
 # Use a simulated venue me response to exercise its real server-served shell without creating a venue.
 for width in (1440,390,320):
  page.set_viewport_size({'width':width,'height':844})
  page.goto('http://127.0.0.1:10000/');page.locator('#auth-form').wait_for()
  results.append({'screen':'owner login','width':width,'minimumContrast':round(check(page,'owner'),2)})
  if width==390:page.screenshot(path='/tmp/noira-login-fixed.png',full_page=True)
  # Serve the actual venue document at a venue URL, with an anonymous session.
  html=Path('server/web/index.html').read_text()
  venue_url='http://127.0.0.1:10000/v/00000000-0000-0000-0000-000000000001/'
  page.route(venue_url,lambda route:route.fulfill(status=200,content_type='text/html',body=html))
  page.route('**/api/me',lambda route:route.fulfill(status=401,content_type='application/json',body='{"error":"Přihlaste se prosím."}'))
  page.goto(venue_url)
  page.locator('#auth-form').wait_for()
  results.append({'screen':'venue login','width':width,'minimumContrast':round(check(page,'venue'),2)})
  page.locator('[data-auth-mode=register]').click()
  results.append({'screen':'registration','width':width,'minimumContrast':round(check(page,'register'),2)})
  page.unroute(venue_url)
  page.unroute('**/api/me')
 assert not errors,errors
 print(json.dumps(results))
 browser.close()
