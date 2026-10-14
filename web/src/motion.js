/** Short, interruptible motion. Grid tracks interpolate without scaling text. */
export class LumenMotion {
  constructor() {
    this.preference=matchMedia('(prefers-reduced-motion: reduce)');
    this.running=new Map();this.layoutAnimation=null;this.themeTimer=null;this.frame=0;this.epoch=0;
    this.onPreference=()=>{if(!this.enabled)this.cancelAll();};
    this.preference.addEventListener('change',this.onPreference);
  }
  get enabled(){return document.documentElement.dataset.motion!=='off'&&!this.preference.matches;}
  cancelLayout(){this.layoutAnimation?.cancel();this.layoutAnimation=null;document.querySelector('.workspace')?.classList.remove('layout-animating');}
  cancelAll(){this.cancelLayout();for(const animation of this.running.values())animation.cancel();this.running.clear();}
  play(element,frames,duration=180) {
    if(!element)return;
    this.running.get(element)?.cancel();
    if(!this.enabled||!element.animate)return;
    const animation=element.animate(frames,{duration,easing:'cubic-bezier(.22,1,.36,1)',fill:'none'});
    this.running.set(element,animation);
    animation.finished.catch(()=>{}).finally(()=>{if(this.running.get(element)===animation)this.running.delete(element);});
    return animation;
  }
  enter(element,offset=5){return this.play(element,[{opacity:0,translate:`0 ${offset}px`},{opacity:1,translate:'0 0'}],180);}
  revealFrom(element,origin){
    if(!element||!origin?.getClientRects().length)return this.enter(element);
    const rect=element.getBoundingClientRect(),source=origin.getBoundingClientRect();
    // Clip the final surface from its source avatar. Text retains its own scale.
    const dx=source.left+source.width/2-rect.left-rect.width/2,dy=source.top+source.height/2-rect.top-rect.height/2;
    const inset=`inset(${(rect.height-source.height)/2}px ${(rect.width-source.width)/2}px round 18px)`;
    this.play(element,[{clipPath:inset,translate:`${dx}px ${dy}px`,opacity:.65},{clipPath:'inset(0px 0px 0px 0px round 24px)',translate:'0 0',opacity:1}],380);
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
  dispose(){this.cancelAll();clearTimeout(this.themeTimer);cancelAnimationFrame(this.frame);this.preference.removeEventListener('change',this.onPreference);}
}
