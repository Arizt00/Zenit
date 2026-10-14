import {icon} from './icons.js';
const MODES=['list','cards','compact'];
export class ExtensionView {
  constructor(p){this.p=p;try{this.mode=localStorage.getItem('zenit.extensions.view');}catch{}if(!MODES.includes(this.mode))this.mode='list';this.animations=[];}
  mount(){
    const toolbar=this.p.workbench.querySelector('.extension-toolbar');if(!toolbar)return;
    const control=document.createElement('div');control.className='extension-view-switch';control.setAttribute('role','group');control.setAttribute('aria-label',this.p.t('Vista de extensiones','Extension view'));
    const titles=[this.p.t('Lista','List'),this.p.t('Tarjetas','Cards'),this.p.t('Compacta','Compact')];
    control.innerHTML=MODES.map((mode,i)=>`<button class="icon-button" data-extension-view="${mode}" title="${titles[i]}" aria-label="${titles[i]}">${i===0?icon('rail-compact'):i===1?icon('extensions'):'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M9 4v16M15 4v16M4 9h16M4 15h16"/></svg>'}</button>`).join('');toolbar.append(control);control.onclick=e=>{const b=e.target.closest('[data-extension-view]');if(b)this.set(b.dataset.extensionView,true);};this.set(this.mode);
  }
  set(mode,animate=false){
    if(!MODES.includes(mode))return;const container=this.p.workbench.querySelector('#extension-results');if(!container)return;
    // Read the current visual positions before cancelling an interrupted transition.
    const cards=[...container.querySelectorAll('.extension-card')],before=cards.map(x=>x.getBoundingClientRect());this.animations.forEach(a=>a.cancel());this.animations=[];
    this.mode=mode;container.dataset.view=mode;try{localStorage.setItem('zenit.extensions.view',mode);}catch{}
    this.p.workbench.querySelectorAll('[data-extension-view]').forEach(b=>{const active=b.dataset.extensionView===mode;b.setAttribute('aria-pressed',String(active));b.classList.toggle('active',active);});
    if(!animate||document.documentElement.dataset.motion==='off'||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
    cards.forEach((card,i)=>{const next=card.getBoundingClientRect(),old=before[i];if(next.bottom<0||next.top>innerHeight)return;
      const animation=card.animate([{translate:`${old.left-next.left}px ${old.top-next.top}px`,opacity:.65},{translate:'0 0',opacity:1}],{duration:300,easing:'cubic-bezier(.2,.8,.2,1)'});this.animations.push(animation);
    });
  }
}
