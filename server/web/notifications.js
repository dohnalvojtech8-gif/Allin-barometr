'use strict';
window.NoiraNotifications=(()=>{
 const auth=window.BarometrAuth;
 const labels={inventory:'Uložené inventury a měření',low_stock:'Zásoby pod nastaveným minimem',stock_movements:'Příjmy, výdeje a přesuny'};
 let settings=null,subscription=null,generation=0;
 const supports=()=>window.isSecureContext&&'serviceWorker'in navigator&&'PushManager'in window&&'Notification'in window;
 const standalone=()=>matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;
 const isIOS=()=>/iPhone|iPad|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
 const permission=()=>('Notification'in window?Notification.permission:'unsupported');
 const root=()=>document.querySelector('#noira-notifications');
 const message=text=>{const node=root()?.querySelector('[data-push-status]');if(node)node.textContent=text};
 async function registration(){return navigator.serviceWorker.register('/sw.js').then(()=>navigator.serviceWorker.ready)}
 function panel(){setTimeout(load,0);return '<section class="hub-panel panel noira-notification-panel" id="noira-notifications"><h2>Oznámení</h2><p>Vyberte si, co chcete vědět o svých zásobách.</p><div data-push-content>Načítání nastavení…</div><p data-push-status role="status" aria-live="polite"></p></section>'}
 function paint(){const node=root()?.querySelector('[data-push-content]');if(!node||!settings)return;const supported=supports(),installed=!isIOS()||standalone();
  node.innerHTML=`<p class="hub-note">${window.BarometrVenuePrefix?'Upozornění pro tento provoz.':'Upozornění napříč vašimi provozy.'} Na jiném telefonu si oznámení zapněte zvlášť.</p>${!supported||!installed?'<p class="notice">Na iPhonu otevřete NOIRU v Safari, zvolte Sdílet → Přidat na plochu a potom ji spusťte z plochy. Oznámení vyžadují podporovaný prohlížeč a iOS 16.4 nebo novější.</p><button type="button" class="noira-install-help" data-push-install>Přidat NOIRU na plochu</button>':''}<form data-push-preferences>${Object.entries(labels).map(([key,label])=>`<label class="permission-line"><input type="checkbox" name="${key}" ${settings.preferences[key]?'checked':''}> <span>${label}</span></label>`).join('')}<button type="submit">Uložit výběr oznámení</button></form><div class="noira-push-actions"><button type="button" class="primary" data-push-enable ${!supported||!installed||permission()==='denied'?'disabled':''}>${subscription?'Obnovit připojení tohoto zařízení':'Zapnout na tomto zařízení'}</button><button type="button" data-push-test ${subscription&&permission()==='granted'?'':'disabled'}>Zkušební oznámení</button><button type="button" data-push-disable ${subscription?'':'disabled'}>Vypnout na tomto zařízení</button></div><p class="hub-note">${permission()==='denied'?'Oznámení jsou zablokovaná v nastavení telefonu nebo prohlížeče. Povolte je tam a pak se vraťte do NOIRY.':subscription?'Toto zařízení je připojené.':'Na tomto zařízení jsou oznámení vypnutá.'}</p>`;
  node.querySelector('form').onsubmit=async e=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;try{const preferences=Object.fromEntries(Object.keys(labels).map(k=>[k,e.target.elements[k].checked]));settings=await auth.send('/api/notifications',{preferences},'PUT');message('Výběr oznámení je uložený.')}catch(err){message(err.message)}finally{button.disabled=false}};
 }
 async function load(){const ticket=++generation;if(!root())return;try{settings=await auth.api('/api/notifications');if(ticket!==generation||!root())return;subscription=null;if(supports()){const reg=await registration();subscription=await reg.pushManager.getSubscription()}
  // A browser subscription can belong to another signed-in account or venue. The server is authoritative.
  if(subscription){const data=await auth.api('/api/notifications/device?endpoint='+encodeURIComponent(subscription.endpoint));if(!data.subscribed)subscription=null}
  paint();}catch(error){message(error.message)}}
 function keyBytes(value){const raw=atob(value.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-value.length%4)%4));return Uint8Array.from(raw,c=>c.charCodeAt(0))}
 document.addEventListener('click',async e=>{const button=e.target.closest('[data-push-enable],[data-push-test],[data-push-disable],[data-push-install]');if(!button||!root())return;if(button.hasAttribute('data-push-install')){document.querySelector('.pwa-launcher')?.click();return}button.disabled=true;try{
  if(button.hasAttribute('data-push-enable')){
   // Ask inside the user's tap handler (required on installed iPhone PWAs).
   const result=await Notification.requestPermission();if(result!=='granted'){paint();message('Oznámení nebyla povolena.');return}
   const reg=await registration();subscription=await reg.pushManager.getSubscription()||await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:keyBytes(settings.publicKey)});
   await auth.send('/api/notifications/subscription',{subscription:subscription.toJSON()});paint();message('Oznámení jsou na tomto zařízení zapnutá.');
  }else if(button.hasAttribute('data-push-disable')){
   if(subscription){await auth.send('/api/notifications/subscription',{endpoint:subscription.endpoint},'DELETE');subscription=null}paint();message('Oznámení pro tento účet a provoz jsou na tomto zařízení vypnutá.');
  }else{await auth.send('/api/notifications/test',{endpoint:subscription.endpoint});message('Zkušební oznámení bylo odesláno.');}
 }catch(error){message(error.message||'Oznámení se nepodařilo nastavit.')}finally{if(button.isConnected)button.disabled=false}});
 async function disconnect(){if(!supports())return;const reg=await registration(),sub=await reg.pushManager.getSubscription();if(sub)await auth.send('/api/notifications/subscription',{endpoint:sub.endpoint},'DELETE')}
 return {panel,disconnect};
})();
