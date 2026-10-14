/** Visual dismissal is separate from the synchronous dialog result/DOM lifecycle. */
export class ModalMotion {
  constructor(motion){this.motion=motion;this.state=null;this.dismissal=null;}
  frame(element){
    const style=getComputedStyle(element);
    return {opacity:style.opacity,translate:style.translate==='none'?'0px 0px':style.translate,clipPath:style.clipPath==='none'?this.full(element):style.clipPath};
  }
  full(element){return `inset(0px 0px 0px 0px round ${getComputedStyle(element).borderRadius||'24px'})`;}
  source(element,origin){
    if(!origin?.isConnected||!origin.getClientRects().length)return null;
    const r=element.getBoundingClientRect(),s=origin.getBoundingClientRect();
    if(!s.width||!s.height)return null;
    const x=Math.max(0,(r.width-s.width)/2),y=Math.max(0,(r.height-s.height)/2),radius=Math.min(s.width,s.height)*.32;
    return {clipPath:`inset(${y}px ${x}px ${y}px ${x}px round ${radius}px)`,translate:`${s.left+s.width/2-r.left-r.width/2}px ${s.top+s.height/2-r.top-r.height/2}px`,opacity:0};
  }
  cancelOpening(){
    if(!this.state)return;
    cancelAnimationFrame(this.state.revealFrame);
    for(const animation of this.state.animations)animation?.cancel();
    this.state.animations=[];
    delete this.state.backdrop.dataset.modalPhase;
  }
  open(element,backdrop){
    const key=element.querySelector('#modal-title')?.textContent||element.dataset.page||'',closing=this.dismissal;
    const continuation=closing?.key===key?this.frame(closing.element):null;
    const background=closing?getComputedStyle(closing.layer).opacity:null;
    const replacing=!!this.state||!!closing;
    this.cancelOpening();closing?.finish();
    this.state={element,backdrop,key,origin:null,animations:[],continuation,transferred:replacing&&!continuation};
    if(!this.motion.enabled)return;
    backdrop.dataset.modalPhase='opening';
    const from=continuation||{opacity:replacing?1:0,translate:replacing?'0px 4px':'0px 14px',clipPath:this.full(element)};
    this.animateOpen(from,continuation?300:replacing?240:340);
    const animation=this.motion.play(backdrop,[{opacity:background??(replacing?1:0)},{opacity:1}],replacing?220:300);
    this.state.animations.push(animation);
  }
  animateOpen(from,duration){
    const state=this.state;if(!state)return;
    const animation=this.motion.play(state.element,[from,{opacity:1,translate:'0px 0px',clipPath:this.full(state.element)}],duration);
    state.animations.push(animation);
    animation?.finished.catch(()=>{}).then(()=>{if(this.state===state)delete state.backdrop.dataset.modalPhase;});
  }
  reveal(element,origin){
    const state=this.state;
    if(!state||state.element!==element)return this.motion.enter(element);
    state.origin=origin;
    if(!this.motion.enabled||state.transferred||state.continuation)return;
    // Activity finishes arranging its content in this turn. Measure that final layout.
    state.revealFrame=requestAnimationFrame(()=>{
      if(this.state!==state)return;
      this.motion.running.get(element)?.cancel();
      const from=this.source(element,origin);if(!from)return;
      this.animateOpen(from,460);
      for(const child of element.children){
        const animation=this.motion.play(child,[{opacity:0,translate:'0px 6px',offset:0},{opacity:0,translate:'0px 6px',offset:.12},{opacity:1,translate:'0px 0px',offset:1}],370);
        state.animations.push(animation);
      }
    });
  }
  close(element,backdrop){
    if(backdrop.hidden||backdrop.classList.contains('hidden'))return this.dismissal?.finished||Promise.resolve();
    if(!this.motion.enabled){this.cancelOpening();this.state=null;this.dismissal?.finish();return Promise.resolve();}
    const state=this.state,from=this.frame(element),background=getComputedStyle(backdrop).opacity;
    // A visual-only snapshot lets confirmation results and replacement dialogs stay synchronous.
    const copy=element.cloneNode(true),originals=[element,...element.querySelectorAll('*')],copies=[copy,...copy.querySelectorAll('*')];
    originals.forEach((node,index)=>{
      const clone=copies[index];
      if(node.tagName==='CANVAS'){try{clone.getContext('2d')?.drawImage(node,0,0);}catch{/* WebGL surfaces may not be readable. */}}
      if(node.matches('input:not([type=file]),textarea,select'))clone.value=node.value;
    });
    copy.removeAttribute('role');copy.removeAttribute('aria-modal');copy.removeAttribute('aria-labelledby');copy.inert=true;copy.setAttribute('aria-hidden','true');
    copy.style.width=element.offsetWidth+'px';copy.style.height=element.offsetHeight+'px';copy.style.maxHeight='none';
    const children=[...element.children].map(child=>this.frame(child));
    this.cancelOpening();this.state=null;
    const to=this.source(element,state?.origin)||{opacity:0,translate:'0px 10px',clipPath:this.full(element)};
    this.dismissal?.finish();
    // A shadow tree isolates copied IDs, forms and selectors from the live application.
    const host=document.createElement('div');host.className='modal-motion-snapshot';host.inert=true;host.setAttribute('aria-hidden','true');
    const shadow=host.attachShadow({mode:'closed'});
    if(!this.snapshotStyles){
      const collect=sheet=>{try{return [...sheet.cssRules].map(rule=>rule.styleSheet?collect(rule.styleSheet):rule.cssText).join('\n');}catch{return '';}};
      this.snapshotStyles=new CSSStyleSheet();this.snapshotStyles.replaceSync(collect(document.querySelector('link[href="/design.css"]').sheet));
    }
    shadow.adoptedStyleSheets=[this.snapshotStyles];
    const layer=document.createElement('div');layer.className=backdrop.className;layer.classList.remove('hidden');layer.classList.add('modal-dismissal');layer.inert=true;layer.setAttribute('aria-hidden','true');layer.append(copy);shadow.append(layer);document.body.append(host);copy.scrollTop=element.scrollTop;
    layer.style.opacity='0';copy.style.opacity='0';
    const animations=[],duration=state?.origin?340:220;
    let resolve;const finished=new Promise(done=>resolve=done);
    const dismissal={element:copy,layer,key:state?.key||'',finished,finish:()=>{
      for(const animation of animations)animation?.cancel();host.remove();if(this.dismissal===dismissal)this.dismissal=null;resolve();
    }};
    this.dismissal=dismissal;
    const easing='cubic-bezier(.4,0,.2,1)';
    const animation=this.motion.play(copy,[{...from,offset:0},{opacity:from.opacity,offset:.7},{...to,opacity:0,offset:1}],duration,easing);animations.push(animation);
    animations.push(this.motion.play(layer,[{opacity:background},{opacity:0}],duration,easing));
    [...copy.children].forEach((child,index)=>{child.style.opacity='0';animations.push(this.motion.play(child,[{...children[index],offset:0},{opacity:children[index].opacity,offset:.3},{opacity:0,translate:'0px -3px',offset:1}],duration,easing));});
    animation?.finished.catch(()=>{}).then(dismissal.finish);
    return finished;
  }
  settle(){this.cancelOpening();this.state=null;this.dismissal?.finish();}
}
