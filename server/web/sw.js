/* Network only: never cache authenticated pages, API responses or user data. */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  if (event.request.mode !== 'navigate' || event.request.method !== 'GET' || new URL(event.request.url).origin !== self.location.origin) return;
  event.respondWith(fetch(event.request).catch(() => new Response(`<!doctype html><html lang="cs"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bez připojení</title><style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#101b17;color:#edf7e8;font:17px/1.6 system-ui}main{max-width:420px;padding:32px}a{color:#dbf28b}</style><main><h1>Jste offline</h1><p>Pro přihlášení a práci s daty potřebujete připojení k internetu. Zkontrolujte Wi-Fi nebo mobilní data a zkuste aplikaci znovu otevřít.</p><a href="/">Zkusit znovu</a></main></html>`, {status:503,headers:{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'}})));
});

/* Web Push is delivered by the browser even while the installed PWA is closed. */
self.addEventListener('push', event => {
  let value={};try{value=event.data?.json()||{}}catch{}
  const url=new URL(value.url||'/',self.location.origin);
  event.waitUntil(self.registration.showNotification(String(value.title||'NOIRA'),{
    body:String(value.body||'Máte nové upozornění ve svém provozu.'),
    icon:'/icons/noira-logo.png',badge:'/icons/noira-logo.png',
    tag:String(value.tag||'noira'),data:{url:url.origin===self.location.origin?url.href:self.location.origin+'/'},
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const target=new URL(event.notification.data?.url||'/',self.location.origin);
  if(target.origin!==self.location.origin)return;
  event.waitUntil(self.clients.matchAll({type:'window',includeUncontrolled:true}).then(async windows=>{
    const exact=windows.find(client=>client.url===target.href);
    if(exact)return exact.focus();
    return self.clients.openWindow(target.href);
  }));
});
