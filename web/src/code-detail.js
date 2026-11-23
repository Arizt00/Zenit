import {icon} from './icons.js';

const ALLOWED=new Set(['P','DIV','SPAN','STRONG','B','EM','I','CODE','PRE','UL','OL','LI','BLOCKQUOTE','H1','H2','H3','H4','H5','H6','TABLE','THEAD','TBODY','TR','TH','TD','BR','HR']);
const CLASSES=['rendered-markdown','code-reference-fact','code-reference-source','code-reference-symbol-kind'];

/** Copy provider formatting without links, executable markup, IDs or event handlers. */
function safeContent(source){
  if(source.nodeType===Node.TEXT_NODE)return document.createTextNode(source.textContent);
  if(source.nodeType!==Node.ELEMENT_NODE)return document.createDocumentFragment();
  if(['SCRIPT','STYLE','IFRAME','IMG','OBJECT','SVG','INPUT','BUTTON'].includes(source.tagName))return document.createDocumentFragment();
  if(source.matches('.code,.monaco-tokenized-source')){const code=document.createElement('pre');code.textContent=source.innerText;return code;}
  const node=document.createElement(ALLOWED.has(source.tagName)?source.tagName.toLowerCase():'span');
  for(const name of CLASSES)if(source.classList.contains(name))node.classList.add(name);
  for(const child of source.childNodes)node.append(safeContent(child));return node;
}

export function showCodeDetail(detail){document.dispatchEvent(new CustomEvent('zenit:code-detail',{detail}));}

/** A local snapshot remains readable when the pointer, selection or active file moves. */
export class CodeDetailPanel{
  constructor(host){
    this.h=host;this.node=document.createElement('section');this.node.className='code-detail-panel';this.node.hidden=true;
    this.node.setAttribute('role','region');this.node.setAttribute('aria-labelledby','code-detail-title');
    this.node.innerHTML=`<header class="code-detail-heading"><span class="code-detail-mark"></span><div><small></small><strong id="code-detail-title"></strong></div><button type="button" class="icon-button" data-detail-copy>${icon('copy')}</button><button type="button" class="icon-button" data-detail-close>${icon('close')}</button></header><div class="code-detail-location">${icon('file')}<span></span><small></small></div><div class="code-detail-body" tabindex="0"></div><footer><span></span><button type="button" class="text-button" data-detail-editor>${icon('code')}<span></span></button></footer>`;
    document.getElementById('editor-panel').append(this.node);
    this.open=e=>this.show(e.detail);document.addEventListener('zenit:code-detail',this.open);
    this.node.querySelector('[data-detail-close]').onclick=()=>{this.node.hidden=true;this.focusEditor();};
    this.node.querySelector('[data-detail-editor]').onclick=()=>this.focusEditor();
    this.node.querySelector('[data-detail-copy]').onclick=()=>this.h.platform.safe(async()=>{await navigator.clipboard.writeText(this.text);this.h.notify(this.t('Detalle copiado.','Details copied.'));});
    this.node.onkeydown=e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();this.node.hidden=true;this.focusEditor();}};
  }
  t(es,en){return this.h.platform.t(es,en);}
  focusEditor(){const view=this.view?.getDomNode()?.isConnected?this.view:this.h.editor.view;view?.focus();}
  show(detail){
    const ctx=detail.context||{},kinds={diagnostic:['bug','Diagnóstico del código','Code diagnostic'],run:['terminal','Resultado de ejecución','Execution result'],test:['flask','Resultado de pruebas','Test result'],change:['git','Cambios revisados','Reviewed changes']},kind=kinds[detail.kind]?detail.kind:'documentation',presentation=kinds[kind]||['book','Documentación del código','Code documentation'];this.view=this.h.editor.view;
    const opening=this.node.hidden;if(this.h.platform.page)this.h.platform.closePage();this.node.hidden=false;this.node.dataset.kind=kind;
    this.node.querySelector('.code-detail-mark').innerHTML=icon(presentation[0]);
    this.node.querySelector('.code-detail-heading small').textContent=this.t(presentation[1],presentation[2]);
    this.node.querySelector('#code-detail-title').textContent=detail.title||ctx.word||this.t('Detalle','Details');
    this.node.querySelector('.code-detail-location>span').textContent=ctx.path||this.t('Editor','Editor');
    this.node.querySelector('.code-detail-location>small').textContent=ctx.line?`L${ctx.line} · C${ctx.column||1}`:'';
    const body=this.node.querySelector('.code-detail-body');body.replaceChildren();
    if(detail.content?.length)for(const node of detail.content)body.append(safeContent(node));
    else {const text=document.createElement(['run','test','change'].includes(kind)?'pre':'p');text.className='code-detail-message';text.textContent=detail.text||'';body.append(text);}
    this.text=(detail.title||ctx.word||'')+'\n'+(ctx.path||'')+'\n\n'+(detail.text||body.innerText);
    this.node.querySelector('footer>span').textContent=this.t('Contenido fijado al abrir el detalle.','Content captured when details were opened.');
    this.node.querySelector('[data-detail-editor]>span').textContent=this.t('Volver al editor','Return to editor');
    this.node.querySelectorAll('[data-detail-action]').forEach(n=>n.remove());
    for(const action of (detail.actions||[]).slice(0,3)){
      const button=document.createElement('button');button.type='button';button.className='text-button';button.dataset.detailAction='true';button.textContent=action.label;button.onclick=()=>this.h.platform.safe(action.run);this.node.querySelector('footer').insertBefore(button,this.node.querySelector('[data-detail-editor]'));
    }
    for(const [selector,es,en] of [['[data-detail-close]','Cerrar detalle','Close details'],['[data-detail-copy]','Copiar detalle','Copy details']]){
      const button=this.node.querySelector(selector);button.title=this.t(es,en);button.setAttribute('aria-label',button.title);
    }
    body.scrollTop=0;body.focus({preventScroll:true});if(opening)this.h.platform.host.motion.enter(this.node,4);
  }
  dispose(){document.removeEventListener('zenit:code-detail',this.open);this.node.remove();}
}
