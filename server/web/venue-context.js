'use strict';
(()=>{
 const prefix=location.pathname.match(/^\/v\/[a-f0-9-]{36}(?=\/|$)/)?.[0];
 if(!prefix)return;
 window.BarometrVenuePrefix=prefix;
 const scoped=url=>{const u=new URL(url,location.origin);if(u.origin===location.origin&&(u.pathname.startsWith('/api/')||u.pathname==='/work'||u.pathname==='/manifest.webmanifest'))u.pathname=prefix+u.pathname;return u.href};
 const originalFetch=window.fetch.bind(window);
 window.fetch=(input,options)=>originalFetch(input instanceof Request?new Request(scoped(input.url),input):scoped(String(input)),options);
 const rewrite=node=>{if(node.nodeType!==1)return;for(const el of [node,...node.querySelectorAll('[href],[src]')])for(const attr of ['href','src']){const value=el.getAttribute(attr);if(value&&(value.startsWith('/api/')||value==='/work'||value==='/manifest.webmanifest'))el.setAttribute(attr,scoped(value))}};
 new MutationObserver(records=>records.forEach(record=>{if(record.type==='attributes')rewrite(record.target);else record.addedNodes.forEach(rewrite)})).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['href','src']});
 document.addEventListener('DOMContentLoaded',async()=>{
  rewrite(document.documentElement);
  try{
   const response=await fetch('/api/venue');if(!response.ok)return;
   const {venue}=await response.json();
   document.querySelectorAll('.workspace>div,.header-identity>span:last-child').forEach(el=>{el.replaceChildren(document.createTextNode(venue.name));const sub=document.createElement('small');sub.textContent=venue.address||'Samostatný provoz';el.append(sub)});
   const bottom=document.querySelector('.aside-bottom');if(bottom){const link=document.createElement('a');link.href='/';link.textContent='← Centrální panel majitele';bottom.prepend(link)}
   document.title=venue.name+' · NOIRA';
  }catch{}
 });
})();
