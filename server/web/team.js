'use strict';
window.NoiraTeam=(()=>{
 const auth=window.BarometrAuth,esc=auth.esc;
 const endpoint=venue=>venue?'/api/owner/venues/'+venue+'/positions':'/api/admin/positions';
 const load=venue=>auth.api(endpoint(venue));
 function checks(values,labels){return Object.entries(labels).filter(([key])=>key!=='inventory.adjust').map(([key,label])=>`<label class="permission-line"><input type="checkbox" data-staff-permission="${key}" ${values[key]?'checked':''}><span>${esc(label)}</span></label>`).join('')}
 function values(form){return Object.fromEntries([...form.querySelectorAll('[data-staff-permission]')].map(input=>[input.dataset.staffPermission,input.checked]))}
 async function controls(host,venue,selected=null,individual=null){
  const generation=Symbol();host.staffGeneration=generation;
  const data=await load(venue);if(!host.isConnected||host.staffGeneration!==generation)return;
  host.innerHTML=`<label>Pozice<select data-position>${data.positions.map(p=>`<option value="${esc(p.id)}" translate="no" ${p.id===(selected||'zamestnanec')?'selected':''}>${esc(p.name)}</option>`).join('')}</select></label><details class="staff-permission-options"><summary>Oprávnění zaměstnance</summary><p class="subtle">Pozice přednastaví oprávnění. Jednotlivé výjimky můžete upravit pro tohoto zaměstnance.</p><div data-position-permissions></div><p class="subtle">Historii může upravovat nebo mazat pouze majitel.</p></details>`;
  const select=host.querySelector('[data-position]'),target=host.querySelector('[data-position-permissions]');
  const paint=permissions=>target.innerHTML=checks(permissions,data.permissions);
  select.onchange=()=>paint(data.positions.find(p=>p.id===select.value)?.permissions||data.defaults);
  paint(individual||data.positions.find(p=>p.id===select.value)?.permissions||data.defaults);
 }
 function modal(html){document.querySelector('#modal').innerHTML=`<div class="modal-backdrop"><section class="modal-content" role="dialog" aria-modal="true"><button class="modal-close" data-auth-close aria-label="Zavřít">×</button>${html}<div class="form-error" role="alert"></div></section></div>`}
 function panel(venues=null){setTimeout(()=>mount(venues),0);return '<section class="hub-panel panel" id="staff-positions"><h2>Pozice a přednastavená oprávnění</h2><p>Připravte pozice pro zaměstnance jednotlivých provozů.</p><div data-positions-body></div></section>'}
 async function mount(venues){const root=document.querySelector('#staff-positions');if(!root)return;let venue=Array.isArray(venues)?venues[0]?.id:null;
  root.querySelector('[data-positions-body]').innerHTML=`${venues?`<label>Provoz<select data-position-venue>${venues.map(v=>`<option value="${v.id}" translate="no">${esc(v.name)}</option>`).join('')}</select></label>`:''}<div data-position-list></div>`;
  async function paint(){const target=root.querySelector('[data-position-list]'),selectedVenue=venue;try{const data=await load(selectedVenue);if(!root.isConnected||selectedVenue!==venue)return;target.innerHTML=`<div class="staff-positions-list">${data.positions.map(p=>`<div><strong translate="no">${esc(p.name)}</strong><button data-edit-position="${esc(p.id)}">Upravit pozici</button></div>`).join('')}</div><button data-new-position>＋ Nová pozice</button><p class="subtle">Změny oprávnění pozice se promítnou zaměstnancům. Jejich individuální výjimky zůstávají zachované.</p>`;
   target.querySelectorAll('[data-edit-position],[data-new-position]').forEach(button=>button.onclick=()=>editor(data.positions.find(p=>p.id===button.dataset.editPosition),data));
  }catch(error){target.textContent=error.message}}
  async function editor(position,data){const selectedVenue=venue;modal(`<h2>${position?'Upravit pozici':'Nová pozice'}</h2><form id="position-form"><label>Název pozice<input name="name" maxlength="80" value="${esc(position?.name||'')}" required></label>${checks(position?.permissions||data.defaults,data.permissions)}<p class="subtle">Historii může upravovat nebo mazat pouze majitel.</p><button class="primary full" type="submit">Uložit pozici</button></form>`);
   const form=document.querySelector('#position-form');form.onsubmit=async event=>{event.preventDefault();const button=form.querySelector('[type=submit]');button.disabled=true;try{await auth.send(endpoint(selectedVenue)+(position?'/'+position.id:''),{name:form.elements.name.value,permissions:values(form)},position?'PUT':'POST');document.querySelector('#modal').innerHTML='';await paint()}catch(error){document.querySelector('#modal .form-error').textContent=error.message;button.disabled=false}}
  }
  root.querySelector('[data-position-venue]')?.addEventListener('change',event=>{venue=event.target.value;paint()});await paint();
 }
 return {load,controls,values,checks,panel};
})();
