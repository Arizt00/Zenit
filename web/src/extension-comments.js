import {icon,escapeHTML as esc} from './icons.js';

export class ExtensionCommentsUI{
 constructor(host){this.h=host;}
 sync(controllers){
  const root=this.h.service().workspace.replaceAll('\\','/').replace(/\/$/,''),current=root+'/'+this.h.editor.current;
  const same=uri=>{try{return decodeURIComponent(new URL(uri).pathname).replace(/^\/(?=[A-Za-z]:)/,'').toLowerCase()===current.toLowerCase();}catch{return false;}};
  const rows=controllers.flatMap(c=>c.threads.filter(t=>t.collapsibleState!==0&&same(t.uri)).map(t=>({controller:c,thread:t}))),key=JSON.stringify(rows);
  if(this.key===key)return;this.key=key;this.node?.remove();this.node=null;if(!rows.length)return;
  const node=document.createElement('aside');node.className='extension-comments';node.setAttribute('aria-label','Comentarios de la extensión');
  node.innerHTML=rows.map(({controller:c,thread:t},i)=>`<section><header>${icon('coco')}<div><strong>${esc(t.label||c.label)}</strong><small>${esc(c.extension)} · línea ${(t.range?.start?.line??0)+1}</small></div><button class="icon-button" data-comment-close="${i}" aria-label="Contraer conversación">${icon('close')}</button></header>${t.comments.map(m=>`<article><strong>${esc(m.author)}</strong><p>${esc(m.body)}</p></article>`).join('')||'<p class="extension-comment-empty">Conversación preparada por la extensión.</p>'}</section>`).join('');
  for(const button of node.querySelectorAll('[data-comment-close]'))button.onclick=()=>this.h.platform.safe(async()=>{const {controller:c,thread:t}=rows[Number(button.dataset.commentClose)];await this.h.platform.api('/extensions/comments/control',{extension:c.extension,controller:c.id,thread:t.id,action:'collapse'});});
  document.querySelector('#editor-panel').append(node);this.node=node;
 }
 dispose(){this.node?.remove();}
}
