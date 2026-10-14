/** Visual dismissal is separate from the synchronous dialog result/DOM lifecycle. */
export class ModalMotion {
  constructor(motion){this.motion=motion;this.state=null;this.dismissal=null;}
  frame(element){
    const style=getComputedStyle(element);
    return {opacity:style.opacity,translate:style.translate==='none'?'0px 0px':style.translate,scale:style.scale==='none'?'1':style.scale,transformOrigin:style.transformOrigin,clipPath:'none'};
  }
  full(){return 'none';}
  source(element,origin){
    if(!origin?.isConnected||!origin.getClientRects().length)return null;
    const r=element.getBoundingClientRect(),s=origin.getBoundingClientRect();
    if(!s.width||!s.height)return null;
    const x=Math.max(0,Math.min(100,(s.left+s.width/2-r.left)/r.width*100)),y=Math.max(0,Math.min(100,(s.top+s.height/2-r.top)/r.height*100));
    return {clipPath:'none',translate:'0px 8px',scale:'.965',transformOrigin:`${x}% ${y}%`,opacity:0};
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
    const from=continuation||{opacity:replacing?1:0,translate:replacing?'0px 0px':'0px 8px',scale:replacing?'1':'.975',clipPath:'none'};
    this.animateOpen(from,continuation?240:replacing?180:320);
    const animation=this.motion.play(backdrop,[{opacity:background??(replacing?1:0)},{opacity:1}],replacing?220:300);
    this.state.animations.push(animation);
  }
  animateOpen(from,duration){
    const state=this.state;if(!state)return;
    const animation=this.motion.play(state.element,[from,{opacity:1,translate:'0px 0px',scale:'1',clipPath:'none',transformOrigin:from.transformOrigin||'50% 50%'}],duration,'cubic-bezier(.16,1,.3,1)');
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
      this.animateOpen(from,380);
      for(const child of element.children){
        const animation=this.motion.play(child,[{opacity:.55},{opacity:1}],240);
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
      if(node.matches('input[type=checkbox],input[type=radio]'))clone.checked=node.checked;
      if(node.tagName==='OPTION')clone.selected=node.selected;
    });
    copy.removeAttribute('role');copy.removeAttribute('aria-modal');copy.removeAttribute('aria-labelledby');copy.inert=true;copy.setAttribute('aria-hidden','true');
    copy.style.width=element.offsetWidth+'px';copy.style.height=element.offsetHeight+'px';copy.style.maxHeight='none';
    const children=[...element.children].map(child=>this.frame(child));
    this.cancelOpening();this.state=null;
    const to={opacity:0,translate:'0px 5px',scale:'.98',clipPath:'none',transformOrigin:from.transformOrigin};
    this.dismissal?.finish();
    // A shadow tree isolates copied IDs, forms and selectors from the live application.
    const host=document.createElement('div');host.className='modal-motion-snapshot';host.inert=true;host.setAttribute('aria-hidden','true');
    const shadow=host.attachShadow({mode:'closed'});
    if(!this.snapshotStyles){
      const collect=sheet=>{try{return [...sheet.cssRules].map(rule=>rule.styleSheet?collect(rule.styleSheet):rule.cssText).join('\n');}catch{return '';}};
      this.snapshotStyles=new CSSStyleSheet();this.snapshotStyles.replaceSync(collect(document.querySelector('link[href="/design.css"]').sheet));
    }
    shadow.adoptedStyleSheets=[this.snapshotStyles];
    const container=document.createElement('div');container.className=backdrop.className;container.classList.remove('hidden');container.classList.add('modal-dismissal');container.inert=true;container.style.background='transparent';container.style.backdropFilter='none';
    const layer=document.createElement('div'),surface=getComputedStyle(backdrop);Object.assign(layer.style,{position:'absolute',inset:'0',background:surface.backgroundColor,backdropFilter:surface.backdropFilter,zIndex:'0'});Object.assign(copy.style,{position:'relative',zIndex:'1'});container.append(layer,copy);shadow.append(container);document.body.append(host);
    originals.forEach((node,index)=>{copies[index].scrollTop=node.scrollTop;copies[index].scrollLeft=node.scrollLeft;});
    layer.style.opacity='0';copy.style.opacity='0';
    const animations=[],duration=220;
    let resolve;const finished=new Promise(done=>resolve=done);
    const dismissal={element:copy,layer,key:state?.key||'',finished,finish:()=>{
      for(const animation of animations)animation?.cancel();host.remove();if(this.dismissal===dismissal)this.dismissal=null;resolve();
    }};
    this.dismissal=dismissal;
    const easing='cubic-bezier(.4,0,.6,1)';
    const animation=this.motion.play(copy,[from,to],duration,easing);animations.push(animation);
    animations.push(this.motion.play(layer,[{opacity:background,offset:0},{opacity:background,offset:.55},{opacity:0,offset:1}],duration,easing));
    [...copy.children].forEach((child,index)=>Object.assign(child.style,children[index]));
    animation?.finished.catch(()=>{}).then(dismissal.finish);
    return finished;
  }
  settle(){this.cancelOpening();this.state=null;this.dismissal?.finish();}
}
