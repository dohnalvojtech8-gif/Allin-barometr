'use strict';
window.NoiraAppearance=(()=>{
 const options=[[1,'Essential','Čistá modrá'],[2,'Obsidian','Tmavá a zlatá'],[3,'Ivory','Teplá a elegantní'],[4,'Studio','Profesionální modrá'],[6,'Dashboard','Světlá analytická'],[8,'Cards','Jemná písková']];
 let selected=1;
 const apply=value=>{if(!options.some(x=>x[0]===value))value=1;selected=value;document.documentElement.dataset.noiraAppearance=String(value)};
 const refresh=async()=>{try{const response=await fetch('/api/appearance',{credentials:'same-origin'});if(response.ok)apply((await response.json()).theme)}catch{}};
 document.addEventListener('DOMContentLoaded',refresh);
 const settings=()=>`<section class="hub-panel appearance-panel"><h2>Vzhled aplikace</h2><p>Vyberte vzhled pro všechny své provozy, sklady a inventury.</p><div class="appearance-options">${options.map(([id,name,desc])=>`<button type="button" data-appearance="${id}" aria-pressed="${id===selected}" class="appearance-choice"><span class="appearance-swatch swatch-${id}"><i></i><i></i><i></i></span><strong>${id} · ${name}</strong><small>${desc}</small><span class="appearance-check">${id===selected?'✓ Vybráno':'Vybrat'}</span></button>`).join('')}</div><p class="appearance-message" role="status"></p></section>`;
 const choose=async(value,auth)=>{const host=document.querySelector('.appearance-panel');const status=host?.querySelector('.appearance-message');if(!options.some(x=>x[0]===value))return;host?.querySelectorAll('button').forEach(x=>x.disabled=true);try{const result=await auth.send('/api/appearance',{theme:value},'PUT');apply(result.theme);host.outerHTML=settings();document.querySelector('.appearance-message').textContent='Vzhled byl uložen pro všechny vaše provozy.'}catch(e){if(status)status.textContent=e.message;host?.querySelectorAll('button').forEach(x=>x.disabled=false)}};
 return {settings,choose,refresh,apply};
})();
