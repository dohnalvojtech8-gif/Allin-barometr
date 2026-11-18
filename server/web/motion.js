'use strict';
/* Selected NOIRA motion: buttons 8, pages 1, menu 2, cards 5,
   dialogs 7, confirmation 8, forms 10; loading percentages removed. */
window.NoiraMotion=(()=>{
 const reduced=matchMedia('(prefers-reduced-motion: reduce)'),running=new WeakMap(),submissions=new WeakMap();
 let lastSubmission=null,selectedVenue='';
 const t=value=>window.NoiraI18n?.t(value)||value;
 function animate(node,frames,duration=240){
  if(!node?.isConnected||reduced.matches||!node.animate)return;
  running.get(node)?.cancel();
  const animation=node.animate(frames,{duration,easing:'cubic-bezier(.2,.7,.2,1)'});
  running.set(node,animation);animation.finished.then(()=>{if(running.get(node)===animation)running.delete(node)},()=>{});
 }
 function announce(message){let node=document.getElementById('motion-status');if(!node){node=document.createElement('div');node.id='motion-status';node.className='motion-sr-only';node.setAttribute('role','status');document.body.append(node)}node.textContent=t(message)}
 function beginSubmission(event){
  const form=event.target;if(!(form instanceof HTMLFormElement))return;
  const existing=submissions.get(form);
  if(existing?.pending){event.preventDefault();event.stopImmediatePropagation();return}
  const button=event.submitter||form.querySelector('button[type=submit],button:not([type])');
  lastSubmission={form,button,pending:0,failed:false,started:performance.now(),label:button?.textContent};submissions.set(form,lastSubmission);
 }
 function finishSubmission(state){
  if(state.pending||state.finished)return;state.finished=true;
  const button=state.button;if(button){button.removeAttribute('data-motion-busy');button.removeAttribute('aria-busy');
   if(state.busyLabel&&button.textContent===state.busyLabel)button.innerHTML=state.originalHTML;
   if(state.failed){button.removeAttribute('data-motion-success');return}
   if(button.isConnected){button.setAttribute('data-motion-success','');setTimeout(()=>button.removeAttribute('data-motion-success'),1800)}
  }
  if(!state.failed){
   announce('Změny byly uloženy.');
   if(!button?.isConnected){const heading=document.querySelector('#modal .modal-content h2');if(heading&&/vytvořen|uložen|změněn|created|saved|erstellt|gespeichert/i.test(heading.textContent)&&!heading.querySelector('.motion-success-icon')){const check=document.createElement('span');check.className='motion-success-icon';check.setAttribute('aria-hidden','true');heading.prepend(check)}}
  }
 }
 function request(path,method='GET'){
  if(/\/api\/(activity|work\/touch)(?:[/?]|$)/.test(path))return ()=>{};
  const writing=!['GET','HEAD'].includes(method.toUpperCase());
  const state=writing&&lastSubmission?.form.isConnected&&(lastSubmission.pending||performance.now()-lastSubmission.started<1200)?lastSubmission:null;
  if(state){state.pending++;state.finished=false;if(state.button){
   state.button.setAttribute('data-motion-busy','');state.button.setAttribute('aria-busy','true');state.button.removeAttribute('data-motion-success');
   if(!state.busyLabel&&!/\/(login|logout|enter|device)(?:[/?]|$)/.test(path)&&method.toUpperCase()!=='DELETE'){
    state.originalHTML=state.button.innerHTML;state.busyLabel=t('Ukládám…');state.button.textContent=state.busyLabel;
   }
  }}
  let done=false;
  return ok=>{if(done)return;done=true;
   if(state){state.failed ||= !ok;state.pending--;setTimeout(()=>finishSubmission(state),0)}
  };
 }
 function swap(node,html){if(!node)return;node.innerHTML=html;animate(node,[{opacity:0},{opacity:1}],200)}
 function highlight(card){if(!card)return;selectedVenue=card.dataset.venueId||'';
  document.querySelectorAll('.venue-card').forEach(c=>c.classList.toggle('motion-selected',c===card));
  animate(card,[{backgroundColor:'var(--panel, #1d2023)'},{backgroundColor:'#343025'},{backgroundColor:'#28261f'}],360);
 }
 function dialog(node){animate(node,[{opacity:0,clipPath:'inset(44% 44% round 14px)'},{opacity:1,clipPath:'inset(0% 0% round 14px)'}],260)}
 function reveal(node){
  if(!node?.isConnected)return;
  const targetHeight=node.getBoundingClientRect().height;
  animate(node,[{opacity:0,height:'0px',clipPath:'inset(0 0 100% 0)',transform:'translateY(-10px)'},{opacity:1,height:targetHeight+'px',clipPath:'inset(0 0 0% 0)',transform:'translateY(0)'}],240);
 }
 function optionalFields(container){
  if(!container||container.querySelector('[data-motion-add-field]'))return;
  const fields=[...container.querySelectorAll('label')].filter(label=>label.querySelector('input[name=phone],input[name=email]'));
  if(!fields.length)return;
  fields.forEach(field=>field.hidden=!field.querySelector('input').value);
  const button=document.createElement('button');button.type='button';button.dataset.motionAddField='';
  const update=()=>{button.hidden=fields.every(field=>!field.hidden);container.classList.toggle('motion-one-contact',fields.filter(field=>!field.hidden).length===1);button.textContent=t(fields[0].hidden?'Přidat telefon zaměstnance':'Přidat e-mail zaměstnance')};
  button.onclick=()=>{const field=fields.find(f=>f.hidden);if(!field)return;field.hidden=false;reveal(field);update();field.querySelector('input').focus({preventScroll:true})};
  container.append(button);update();
 }
 function inspect(root){
  if(!(root instanceof Element))return;
  const find=selector=>[...(root.matches(selector)?[root]:[]),...root.querySelectorAll(selector)];
  for(const node of find('.modal-content,.overlay .sheet,.overlay .work-sheet,dialog[open]'))dialog(node);
  for(const container of find('[data-motion-contacts]'))optionalFields(container);
  if(root.closest('form')&&!root.closest('[data-motion-contacts]')){if(root.matches('label,[data-login-venue]'))reveal(root)}
  for(const card of find('.venue-card'))if(card.dataset.venueId===selectedVenue&&selectedVenue)card.classList.add('motion-selected');
 }
 function start(){
  document.addEventListener('submit',beginSubmission,true);
  document.addEventListener('click',event=>highlight(event.target.closest('.venue-card')));
  document.addEventListener('focusin',event=>{const card=event.target.closest('.venue-card');if(card)highlight(card)});
  document.addEventListener('toggle',event=>{if(event.target.matches('dialog[open]'))dialog(event.target)},true);
  new MutationObserver(records=>{for(const record of records){
   if(record.target instanceof Element&&record.target.matches('#work-root')&&record.addedNodes.length)animate(record.target,[{opacity:0},{opacity:1}],200);
   for(const node of record.addedNodes)inspect(node);
  }}).observe(document.body,{childList:true,subtree:true});
  inspect(document.body);
  reduced.addEventListener('change',()=>{if(reduced.matches)for(const node of document.querySelectorAll('main,.modal-content,.venue-card')){running.get(node)?.cancel()}});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
 return {request,swap,reveal,dialog};
})();
