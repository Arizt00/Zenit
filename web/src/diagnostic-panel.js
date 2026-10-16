import {icon} from './icons.js';

/** One bounded, scroll-free diagnostic card per editor window. No polling. */
export function installDiagnosticPanels(editor){return new DiagnosticPanel(editor);}
class DiagnosticPanel{
  constructor(editor){
    this.editor=editor;this.bindings=new Map();this.cache=new Map();this.sequence=0;
    this.node=document.createElement('section');this.node.className='zenit-diagnostic-panel';this.node.hidden=true;this.node.tabIndex=-1;this.node.setAttribute('role','dialog');this.node.setAttribute('aria-label',this.t('Diagnóstico del código','Code diagnostic'));
    this.node.innerHTML='<header class="diagnostic-heading"><span class="diagnostic-mark"></span><div><small></small><strong></strong></div><button type="button" class="diagnostic-close">'+icon('close')+'</button></header><div class="diagnostic-file">'+icon('file')+'<span></span><small></small></div><div class="diagnostic-body"><p class="diagnostic-message"></p></div><footer><span class="diagnostic-origin"></span><div class="diagnostic-navigation"><button type="button" data-diagnostic-prev>'+icon('chevron-left')+'</button><span aria-live="polite"></span><button type="button" data-diagnostic-next>'+icon('chevron-right')+'</button></div><button type="button" data-diagnostic-copy>'+icon('copy')+'</button></footer>';
    document.body.append(this.node);
    const button=(selector,es,en,run)=>{const b=this.node.querySelector(selector);b.title=this.t(es,en);b.setAttribute('aria-label',b.title);b.onclick=()=>{this.node.focus({preventScroll:true});run();};};
    button('.diagnostic-close','Cerrar diagnóstico','Close diagnostic',()=>this.hide(true));
    button('[data-diagnostic-prev]','Diagnóstico anterior','Previous diagnostic',()=>this.turn(-1));
    button('[data-diagnostic-next]','Siguiente diagnóstico','Next diagnostic',()=>this.turn(1));
    button('[data-diagnostic-copy]','Copiar diagnóstico','Copy diagnostic',()=>navigator.clipboard.writeText(this.text()));
    this.node.onpointerenter=()=>{this.pointerInside=true;clearTimeout(this.closeTimer);};this.node.onpointerleave=()=>{this.pointerInside=false;this.scheduleHide();};
    this.node.onfocusout=()=>queueMicrotask(()=>{if(!this.node.contains(document.activeElement))this.scheduleHide();});
    this.node.onkeydown=e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();this.hide(true);}else if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();this.turn(e.key==='ArrowLeft'?-1:1);}};
    this.outside=e=>{if(!this.node.contains(e.target))this.hide();};this.resize=()=>this.hide();
    document.addEventListener('pointerdown',this.outside,true);window.addEventListener('resize',this.resize);
    this.markers=monaco.editor.onDidChangeMarkers(resources=>{
      for(const uri of resources)this.cache.delete(uri.toString());
      // An analyzer may publish after the pointer has stopped. Reconcile that
      // stationary hover too, rather than waiting for another mouse movement.
      if(this.hovered&&resources.some(uri=>uri.toString()===this.hovered.view.getModel()?.uri.toString()))this.queueOpen(this.hovered.view,this.hovered.position);
      if(!this.node.hidden&&this.view?.getModel()&&resources.some(uri=>uri.toString()===this.view.getModel().uri.toString())){
        const current=this.items[this.item],items=this.at(this.view,this.position);
        if(!items.length){clearTimeout(this.markerTimer);this.markerTimer=setTimeout(()=>{if(!this.node.hidden&&!this.at(this.view,this.position).length)this.hide(false,true);},180);return;}
        clearTimeout(this.markerTimer);const index=items.findIndex(m=>m.message===current.message&&m.source===current.source&&m.severity===current.severity);
        this.items=items;this.item=Math.max(0,index);this.part=0;this.pages.clear();this.render();this.place();
      }
    });
  }
  t(es,en){return document.documentElement.lang.startsWith('en')?en:es;}
  reduced(){return document.documentElement.dataset.motion==='off'||matchMedia('(prefers-reduced-motion: reduce)').matches;}
  bind(view){
    if(this.bindings.has(view))return;
    // Monaco can emit its synthetic mouse-leave while repainting a hovered
    // marker. Only a real exit from the editor DOM should cancel the hover.
    const root=view.getDomNode(),leave=()=>{if(this.hovered?.view===view)this.hovered=null;this.scheduleHide();};
    root.addEventListener('pointerleave',leave);
    const list=[view.onMouseMove(e=>{
      const position=e.target.position;
      if(!position||e.target.type!==monaco.editor.MouseTargetType.CONTENT_TEXT){this.hovered=null;this.scheduleHide();return;}
      this.hovered={view,position};this.queueOpen(view,position);
    }),{dispose:()=>root.removeEventListener('pointerleave',leave)},view.onDidScrollChange(e=>{if(this.view===view&&(e.scrollTopChanged||e.scrollLeftChanged))this.hide();}),view.onDidChangeModel(()=>{if(this.hovered?.view===view)this.hovered=null;if(this.view===view)this.hide();}),view.onDidChangeModelContent(()=>{if(view.getModel())this.cache.delete(view.getModel().uri.toString());if(this.hovered?.view===view)this.hovered=null;if(this.view===view)this.hide();}),view.onKeyDown(e=>{if(e.keyCode===monaco.KeyCode.Escape)this.hide();}),view.onDidDispose(()=>{if(this.hovered?.view===view)this.hovered=null;if(this.view===view)this.hide();this.bindings.delete(view);for(const item of list)item.dispose();})];
    list.push(view.addAction({id:'zenit.diagnostic.show',label:this.t('Mostrar diagnóstico','Show diagnostic'),keybindings:[monaco.KeyMod.chord(monaco.KeyMod.CtrlCmd|monaco.KeyCode.KeyK,monaco.KeyMod.CtrlCmd|monaco.KeyCode.KeyI)],run:()=>{const pos=view.getPosition(),items=pos?this.at(view,pos):[];if(items.length){this.open(view,pos,items,view.getId()+':keyboard');this.node.querySelector('.diagnostic-close').focus({preventScroll:true});}else view.getAction('editor.action.showHover')?.run();}}));
    this.bindings.set(view,list);
  }
  queueOpen(view,position){
    const items=this.at(view,position);if(!items.length){this.scheduleHide();return;}
    clearTimeout(this.closeTimer);const key=view.getId()+':'+JSON.stringify(items);
    if(this.key===key&&!this.node.hidden||this.pendingKey===key)return;
    clearTimeout(this.openTimer);this.pendingKey=key;
    this.openTimer=setTimeout(()=>{this.pendingKey=null;const fresh=this.at(view,position);if(fresh.length)this.open(view,position,fresh,view.getId()+':'+JSON.stringify(fresh));},this.node.hidden?180:70);
  }
  at(view,pos){
    if(this.editor.settings.diagnostics===false)return [];
    const model=view.getModel();if(!model)return [];
    const uri=model.uri.toString();if(!this.cache.has(uri))this.cache.set(uri,monaco.editor.getModelMarkers({resource:model.uri}).slice(0,500));
    const unique=new Map();for(const m of this.cache.get(uri)){
      if(pos.lineNumber<m.startLineNumber||pos.lineNumber>m.endLineNumber||pos.lineNumber===m.startLineNumber&&pos.column<m.startColumn||pos.lineNumber===m.endLineNumber&&pos.column>m.endColumn)continue;
      const key=JSON.stringify([m.severity,m.message,m.source,m.startLineNumber,m.startColumn]);if(!unique.has(key))unique.set(key,m);
    }
    return [...unique.values()].sort((a,b)=>b.severity-a.severity);
  }
  open(view,position,items,key){
    clearTimeout(this.openTimer);clearTimeout(this.closeTimer);const previous=this.node.hidden?null:this.node.getBoundingClientRect();this.sequence++;this.animation?.cancel();
    this.view=view;this.position=position;this.items=items;this.item=0;this.part=0;this.pages=new Map();this.key=key;this.node.hidden=false;
    this.render();this.place();
    if(!this.reduced()){
      const rect=this.node.getBoundingClientRect(),from=previous?{opacity:1,transform:`translate(${previous.x-rect.x}px,${previous.y-rect.y}px)`}:{opacity:0,transform:'translateY(-6px) scale(.985)'};
      this.animation=this.node.animate([from,{opacity:1,transform:'translate(0,0) scale(1)'}],{duration:220,easing:'cubic-bezier(.22,1,.36,1)'});
      if(previous)this.animateBody();
    }
  }
  text(){const m=this.items[this.item];return m.message+(m.relatedInformation?.length?'\n\n'+m.relatedInformation.map(x=>(x.resource?.path?.split('/').at(-1)||'')+':'+x.startLineNumber+' · '+x.message).join('\n'):'');}
  room(){
    const root=this.view.getDomNode().getBoundingClientRect(),p=this.view.getScrolledVisiblePosition(this.position);if(!p)return null;
    const anchor={left:root.left+p.left,top:root.top+p.top,bottom:root.top+p.top+p.height};const below=innerHeight-anchor.bottom-24,above=anchor.top-24;
    const down=below>=225||below>=above;return {anchor,down,space:Math.max(150,Math.min(360,down?below:above))};
  }
  render(){
    const m=this.items[this.item],kind=m.severity>=8?'error':m.severity>=4?'warning':'info',code=typeof m.code==='object'?m.code.value:m.code;
    this.node.dataset.severity=kind;this.node.querySelector('.diagnostic-mark').innerHTML=icon(kind==='error'?'error-circle':kind==='warning'?'warning':'info');
    this.node.querySelector('.diagnostic-heading small').textContent=this.t('ZÉNIT · DIAGNÓSTICO','ZÉNIT · DIAGNOSTIC');this.node.querySelector('.diagnostic-heading strong').textContent=kind==='error'?this.t('Revisa este punto','Review this issue'):kind==='warning'?this.t('Algo que revisar','Something to review'):this.t('Una observación','An observation');
    const path=this.editor.pathFor(this.view.getModel())||'';this.node.querySelector('.diagnostic-file>span').textContent=path.split(/[\\/]/).at(-1);this.node.querySelector('.diagnostic-file>span').title=path;
    this.node.querySelector('.diagnostic-file>small').textContent=this.t('Línea ','Line ')+m.startLineNumber+' · '+this.t('Col. ','Col. ')+m.startColumn;
    const origin=this.node.querySelector('.diagnostic-origin');origin.textContent=(m.source||this.t('Analizador','Analyzer'))+(code?' · '+code:'');origin.title=origin.textContent;
    this.roomInfo=this.room();const budget=Math.max(36,(this.roomInfo?.space||300)-166),message=this.node.querySelector('.diagnostic-message'),text=this.text();
    if(!this.pages.has(this.item))this.pages.set(this.item,[]);
    const pages=this.pages.get(this.item);while(pages.length<=this.part){
      const start=pages.at(-1)?.end||0;let lo=start+1,hi=Math.min(text.length,start+2400),best=lo;
      while(lo<=hi){const end=Math.floor((lo+hi)/2);message.textContent=text.slice(start,end);if(message.getBoundingClientRect().height<=budget){best=end;lo=end+1;}else hi=end-1;}
      let end=best;const split=text.lastIndexOf(' ',end);if(end<text.length&&split>start+(end-start)*.6)end=split+1;
      if(end<text.length&&/[\uD800-\uDBFF]/.test(text[end-1])&&/[\uDC00-\uDFFF]/.test(text[end]))end--;
      pages.push({start,end});if(end>=text.length)break;
    }
    const page=pages[this.part]||pages.at(-1)||{start:0,end:0};message.textContent=text.slice(page.start,page.end);
    this.node.querySelector('.diagnostic-navigation>span').textContent=(this.item+1)+' / '+this.items.length+(this.part||page.end<text.length?' · '+this.t('parte ','part ')+(this.part+1):'');
    this.node.querySelector('[data-diagnostic-prev]').disabled=this.item===0&&this.part===0;
    this.node.querySelector('[data-diagnostic-next]').disabled=this.item===this.items.length-1&&page.end>=text.length;
    this.node.querySelector('.diagnostic-navigation').hidden=this.items.length===1&&page.end>=text.length&&!this.part;
  }
  place(){
    const r=this.roomInfo;if(!r){this.hide();return;}const rect=this.node.getBoundingClientRect();this.node.style.left=Math.max(12,Math.min(innerWidth-rect.width-12,r.anchor.left-10))+'px';
    this.node.style.top=Math.max(12,Math.min(innerHeight-rect.height-12,r.down?r.anchor.bottom+10:r.anchor.top-rect.height-10))+'px';this.node.style.transformOrigin=r.down?'24px top':'24px bottom';
  }
  turn(direction){
    const hadFocus=this.node.contains(document.activeElement);
    const pages=this.pages.get(this.item),current=pages[this.part];if(direction>0){if(current.end<this.text().length)this.part++;else if(this.item<this.items.length-1){this.item++;this.part=0;}else return;}
    else if(this.part)this.part--;else if(this.item){this.item--;this.part=Math.max(0,(this.pages.get(this.item)?.length||1)-1);}else return;
    this.render();this.place();this.animateBody();if(hadFocus&&!this.node.contains(document.activeElement))this.node.querySelector('.diagnostic-navigation button:not(:disabled),.diagnostic-close')?.focus({preventScroll:true});
  }
  animateBody(){this.bodyAnimation?.cancel();if(!this.reduced())this.bodyAnimation=this.node.querySelector('.diagnostic-body').animate([{opacity:.25,transform:'translateY(3px)'},{opacity:1,transform:'translateY(0)'}],{duration:160,easing:'cubic-bezier(.22,1,.36,1)'});}
  scheduleHide(){clearTimeout(this.openTimer);this.pendingKey=null;clearTimeout(this.closeTimer);if(!this.pointerInside&&!this.node.contains(document.activeElement))this.closeTimer=setTimeout(()=>{if(!this.pointerInside&&!this.node.contains(document.activeElement))this.hide(false,!!this.hovered);},220);}
  hide(focus=false,keepHover=false){
    clearTimeout(this.openTimer);clearTimeout(this.closeTimer);clearTimeout(this.markerTimer);this.pendingKey=null;if(!keepHover)this.hovered=null;if(this.node.hidden)return;
    const sequence=++this.sequence;this.key=null;this.animation?.cancel();if(focus)this.view?.focus();
    if(this.reduced()){this.node.hidden=true;return;}
    this.animation=this.node.animate([{opacity:1,transform:'translateY(0)'},{opacity:0,transform:'translateY(-3px)'}],{duration:140,easing:'cubic-bezier(.4,0,1,1)'});
    this.animation.finished.then(()=>{if(sequence===this.sequence)this.node.hidden=true;}).catch(()=>{});
  }
  dispose(){this.hide();this.sequence++;this.animation?.cancel();this.bodyAnimation?.cancel();this.markers.dispose();for(const list of this.bindings.values())for(const item of list)item.dispose();this.bindings.clear();document.removeEventListener('pointerdown',this.outside,true);window.removeEventListener('resize',this.resize);this.node.remove();}
}
