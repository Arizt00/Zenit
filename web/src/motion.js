import {ModalMotion} from './modal-motion.js';

/** Short, interruptible motion. Grid tracks interpolate without scaling text. */
export class LumenMotion {
  constructor() {
    this.preference=matchMedia('(prefers-reduced-motion: reduce)');
    this.running=new Map();this.dialogs=new ModalMotion(this);this.surfaces=new ModalMotion(this);this.layoutAnimation=null;this.themeTimer=null;this.frame=0;this.epoch=0;
    this.onResize=()=>{this.dialogs.settle();this.surfaces.settle();this.syncBackground();this.screenTransition?.skipTransition();};window.addEventListener('resize',this.onResize);
    this.onPreference=()=>{if(!this.enabled)this.cancelAll();};
    this.preference.addEventListener('change',this.onPreference);
  }
  get enabled(){return document.documentElement.dataset.motion!=='off'&&!this.preference.matches;}
  cancelLayout(){this.layoutAnimation?.cancel();this.layoutAnimation=null;document.querySelector('.workspace')?.classList.remove('layout-animating');}
  cancelAll(){this.cancelLayout();this.dialogs.settle();this.surfaces.settle();this.syncBackground();this.screenTransition?.skipTransition();for(const animation of this.running.values())animation.cancel();this.running.clear();}
  play(element,frames,duration=180,easing='cubic-bezier(.2,.85,.2,1)') {
    if(!element)return;
    this.running.get(element)?.cancel();
    if(!this.enabled||!element.animate)return;
    const animation=element.animate(frames,{duration,easing,fill:'none'});
    this.running.set(element,animation);
    animation.finished.catch(()=>{}).finally(()=>{if(this.running.get(element)===animation)this.running.delete(element);});
    return animation;
  }
  enter(element,offset=5){return this.play(element,[{opacity:0,translate:`0 ${offset}px`},{opacity:1,translate:'0 0'}],180);}
  holdBackground(){
    const home=document.getElementById('lumen-home'),depth=home?.querySelector('.welcome-depth');
    if(this.homeFreeze||home?.hidden||!depth)return;
    this.homeFreeze={depth,transform:depth.style.transform,transition:depth.style.transition};
    const position=getComputedStyle(depth).transform;depth.style.transition='none';depth.style.transform=position;
    document.documentElement.dataset.modalMotion='active';
  }
  syncBackground(){
    if(this.dialogs.state||this.dialogs.dismissal||this.surfaces.state||this.surfaces.dismissal||!document.getElementById('modal-backdrop')?.classList.contains('hidden')||document.querySelector('.settings-overlay:not([hidden])'))return;
    const frozen=this.homeFreeze;if(frozen){frozen.depth.style.transition=frozen.transition;frozen.depth.style.transform=frozen.transform;this.homeFreeze=null;}
    delete document.documentElement.dataset.modalMotion;
  }
  openDialog(element,backdrop){this.holdBackground();this.surfaces.dismissal?.finish();this.dialogs.open(element,backdrop);}
  closeDialog(element,backdrop){const finished=this.dialogs.close(element,backdrop);finished.then(()=>this.syncBackground());return finished;}
  openSurface(element,backdrop){this.holdBackground();this.dialogs.dismissal?.finish();this.surfaces.open(element,backdrop);}
  closeSurface(element,backdrop){const finished=this.surfaces.close(element,backdrop);finished.then(()=>this.syncBackground());return finished;}
  revealFrom(element,origin){return this.dialogs.reveal(element,origin);}
  swapScreen(mutate,origin,{direction='enter',target}={}){
    if(this.enabled&&this.screenTransition&&this.screenTarget===target)return this.screenTransition.finished.catch(()=>{});
    const run=this.screenEpoch=(this.screenEpoch||0)+1;this.screenTransition?.skipTransition();
    const update=()=>{mutate();this.dialogs.dismissal?.finish();this.surfaces.dismissal?.finish();this.syncBackground();};
    if(!this.enabled||!document.startViewTransition){this.screenTransition=null;this.screenTarget=null;delete document.documentElement.dataset.screenMotion;document.documentElement.style.removeProperty('--screen-source');update();this.enter(document.getElementById('app'),4);return Promise.resolve();}
    const r=origin?.getBoundingClientRect(),root=document.documentElement;
    root.dataset.screenMotion=direction;this.screenTarget=target;
    root.style.setProperty('--screen-source',r?`inset(${Math.max(0,r.top)}px ${Math.max(0,innerWidth-r.right)}px ${Math.max(0,innerHeight-r.bottom)}px ${Math.max(0,r.left)}px round 18px)`:'inset(35% 30% round 24px)');
    const transition=document.startViewTransition(()=>{if(run===this.screenEpoch)update();});this.screenTransition=transition;
    transition.ready.catch(()=>{}); // A deliberately interrupted snapshot rejects ready.
    transition.updateCallbackDone.catch(error=>{if(error.name!=='AbortError')queueMicrotask(()=>{throw error;});});
    return transition.finished.catch(()=>{}).finally(()=>{if(this.screenTransition===transition){this.screenTransition=null;this.screenTarget=null;delete root.dataset.screenMotion;root.style.removeProperty('--screen-source');}});
  }
  changeLayout(elements,mutate) {
    const root=elements[0]?.closest('.workspace');
    if(!root){mutate();return;}
    // Read the current animated geometry before cancelling an interrupted change.
    const before=getComputedStyle(root);
    const from={gridTemplateColumns:before.gridTemplateColumns,gridTemplateRows:before.gridTemplateRows};
    this.cancelLayout();
    for(const el of elements)this.running.get(el)?.cancel();
    mutate();
    if(!this.enabled||!root.animate)return;
    const after=getComputedStyle(root);
    const to={gridTemplateColumns:after.gridTemplateColumns,gridTemplateRows:after.gridTemplateRows};
    if(from.gridTemplateColumns===to.gridTemplateColumns&&from.gridTemplateRows===to.gridTemplateRows)return;
    root.classList.add('layout-animating');
    const animation=root.animate([from,to],{duration:Math.max(80,Math.min(400,parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--motion-layout'))||240)),easing:'cubic-bezier(.2,.8,.2,1)',fill:'none'});
    this.layoutAnimation=animation;
    animation.finished.catch(()=>{}).finally(()=>{if(this.layoutAnimation===animation){this.layoutAnimation=null;root.classList.remove('layout-animating');}});
  }
  theme(){
    clearTimeout(this.themeTimer);
    document.documentElement.classList.toggle('theme-changing',this.enabled);
    this.themeTimer=setTimeout(()=>document.documentElement.classList.remove('theme-changing'),240);
  }
  dispose(){this.cancelAll();clearTimeout(this.themeTimer);cancelAnimationFrame(this.frame);this.preference.removeEventListener('change',this.onPreference);window.removeEventListener('resize',this.onResize);}
}
