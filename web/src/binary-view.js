import {escapeHTML as esc,icon} from './icons.js';

export function byteRows(bytes,offset=0){
  const rows=[];
  for(let start=0;start<bytes.length;start+=16){const chunk=bytes.slice(start,start+16);rows.push({offset:offset+start,hex:[...chunk].map(b=>b.toString(16).padStart(2,'0')),ascii:[...chunk].map(b=>b>=32&&b<=126?String.fromCharCode(b):'·').join('')});}
  return rows;
}
export function byteValue(bytes,index,little=true){
  if(index<0||index>=bytes.length)return '';
  const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),values=['u8: '+bytes[index]];
  if(index+2<=bytes.length)values.push('u16: '+view.getUint16(index,little));
  if(index+4<=bytes.length)values.push('u32: '+view.getUint32(index,little),'f32: '+view.getFloat32(index,little));
  return values.join('  ·  ');
}
export function binaryState(item){return item.binaryState ||= {revision:item.revision,patches:new Map(),undo:[],redo:[],saving:false};}
export function binaryPatches(state){const groups=[];for(const [offset,p] of [...state.patches].sort((a,b)=>a[0]-b[0])){let group=groups.at(-1);if(!group||group.offset+group.before.length!==offset||group.before.length>=4096){group={offset,before:[],after:[]};groups.push(group);}group.before.push(p.before);group.after.push(p.after);}const encode=bytes=>btoa(bytes.map(x=>String.fromCharCode(x)).join(''));return groups.map(g=>({offset:g.offset,before:encode(g.before),after:encode(g.after)}));}
/** Page data stays small; edits survive tab changes and never decode bytes as text. */
export class BinaryView{
  constructor(mount,item,load,actions={}){
    this.record=item;this.item=item;this.state=binaryState(item);this.load=load;this.actions=actions;this.epoch=0;this.node=document.createElement('section');this.node.className='binary-view';
    this.node.innerHTML=`<header><div>${icon('assembly')}<strong>${esc(item.format)}</strong><span>${item.size.toLocaleString()} bytes</span></div><form data-binary-offset><label>Posición <input aria-label="Byte offset" value="0x0" size="12" autocomplete="off"></label><button class="secondary-button">Ir</button></form></header><div class="binary-tools"><div class="binary-edit-tools"><button class="secondary-button" data-binary-edit>${icon('code')}Editar bytes</button><form data-binary-edit-form><label>Hex <input aria-label="Valor hexadecimal" maxlength="2" placeholder="00" spellcheck="false" autocomplete="off" disabled></label><button class="secondary-button" disabled>Aplicar</button></form><button class="icon-button" data-binary-undo aria-label="Deshacer byte">${icon('undo')}</button><button class="icon-button" data-binary-redo aria-label="Rehacer byte">${icon('redo')}</button><span class="binary-modified" role="status"></span></div><div class="binary-action-tools"><button class="icon-button" data-binary-export title="Exportar cambios hexadecimales" aria-label="Exportar cambios hexadecimales">${icon('download')}</button><button class="secondary-button" data-binary-save>${icon('check')}Guardar</button><button class="secondary-button" data-binary-build>${icon('build')}Recompilar</button><button class="primary-button" data-binary-run>${icon('play')}Ejecutar</button></div></div><div class="binary-scroll"><table><thead><tr><th>Offset</th><th>Hexadecimal</th><th>ASCII</th></tr></thead><tbody></tbody></table></div><footer><span class="binary-value" role="status">Selecciona un byte</span><label><input type="checkbox" checked> Little endian</label><button class="secondary-button" data-byte-prev>${icon('chevron-left')}Anterior</button><button class="secondary-button" data-byte-next>Siguiente${icon('chevron-right')}</button></footer><details class="binary-arguments"><summary>Argumentos de ejecución</summary><label>Un argumento por línea<textarea rows="2" aria-label="Argumentos de ejecución" placeholder="argumento"></textarea></label></details><p class="binary-error" role="alert" hidden></p>`;
    mount.append(this.node);this.render(item);this.editing=false;
    const safe=fn=>async()=>{try{this.error('');await fn();}catch(error){this.error(error.message);}};
    this.node.querySelector('[data-binary-offset]').onsubmit=e=>{e.preventDefault();const raw=this.node.querySelector('[data-binary-offset] input').value.trim();if(!/^(?:0x[\da-f]+|\d+)$/i.test(raw))return this.error('Introduce una posición decimal o hexadecimal.');this.page(Number(raw));};
    this.node.querySelector('[data-byte-prev]').onclick=()=>this.page(Math.max(0,this.item.offset-512));this.node.querySelector('[data-byte-next]').onclick=()=>this.page(this.item.offset+512);
    this.node.querySelector('tbody').onclick=e=>{const button=e.target.closest('[data-byte]');if(!button)return;this.selected=+button.dataset.byte;this.paintSelection();};
    this.node.querySelector('tbody').ondblclick=e=>{if(!e.target.closest('[data-byte]'))return;this.editing=!item.readOnly;this.paintControls();this.node.querySelector('[data-binary-edit-form] input').focus();this.node.querySelector('[data-binary-edit-form] input').select();};
    this.node.querySelector('[data-binary-edit]').onclick=()=>{this.editing=!this.editing;this.paintControls();};
    this.node.querySelector('[data-binary-edit-form]').onsubmit=e=>{e.preventDefault();this.edit(this.node.querySelector('[data-binary-edit-form] input').value);};
    this.node.querySelector('[data-binary-undo]').onclick=()=>this.undo();this.node.querySelector('[data-binary-redo]').onclick=()=>this.undo(true);
    this.node.querySelector('[data-binary-export]').onclick=()=>{const data={format:'zenit-hexpatch-1',path:item.path,revision:this.state.revision,patches:binaryPatches(this.state)},url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=item.path.split(/[\\/]/).at(-1)+'.hexpatch.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);};
    this.node.querySelector('[data-binary-save]').onclick=safe(()=>this.actions.save?.());this.node.querySelector('[data-binary-build]').onclick=safe(()=>this.actions.build?.());this.node.querySelector('[data-binary-run]').onclick=safe(()=>this.actions.run?.());
    const args=this.node.querySelector('textarea');args.value=(item.binaryArguments||[]).join('\n');args.oninput=()=>{item.binaryArguments=args.value.split(/\r?\n/).filter(x=>x.length);};
    this.node.querySelector('footer input').onchange=()=>this.value();
    this.node.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&!e.altKey&&['z','y'].includes(e.key.toLowerCase())){e.preventDefault();e.stopImmediatePropagation();this.undo(e.shiftKey||e.key.toLowerCase()==='y');}};
    this.actions.info?.().then(info=>{if(!this.node.isConnected)return;this.node.querySelector('[data-binary-run]').disabled=!info.canRun;this.node.querySelector('[data-binary-run]').title=info.runReason||'Ejecutar en la terminal seleccionada';}).catch(error=>this.error(error.message));
    this.paintControls();
  }
  error(message){const node=this.node.querySelector('.binary-error');node.classList.remove('binary-save-result');node.textContent=message;node.hidden=!message;}
  async page(offset){if(this.state.saving)return;const epoch=++this.epoch;this.error('');this.node.setAttribute('aria-busy','true');try{const item=await this.load(this.item.path,offset);if(epoch===this.epoch&&this.node.isConnected){if(item.revision!==this.state.revision&&this.state.patches.size)throw Error('El archivo cambió en disco. Tus cambios permanecen aquí; expórtalos antes de volver a abrirlo. No se mezclan revisiones.');this.state.revision=item.revision;this.render(item);}}catch(e){if(epoch===this.epoch)this.error(e.message);}finally{if(epoch===this.epoch)this.node.removeAttribute('aria-busy');}}
  render(item){Object.assign(this.record,item);this.item=item;this.original=Uint8Array.from(atob(item.data),c=>c.charCodeAt(0));this.selected=null;this.node.querySelector('[data-binary-offset] input').value='0x'+item.offset.toString(16);this.paintBytes();}
  paintBytes(){
    this.bytes=this.original.slice();for(let i=0;i<this.bytes.length;i++){const patch=this.state.patches.get(this.item.offset+i);if(patch)this.bytes[i]=patch.after;}
    this.node.querySelector('tbody').innerHTML=byteRows(this.bytes,this.item.offset).map(row=>`<tr><th>${row.offset.toString(16).padStart(8,'0')}</th><td>${row.hex.map((v,i)=>`<button type="button" class="${this.state.patches.has(row.offset+i)?'byte-modified':''}" data-byte="${row.offset-this.item.offset+i}" aria-label="Byte ${row.offset+i}: ${v}" aria-pressed="false">${v}</button>`).join('')}</td><td>${esc(row.ascii)}</td></tr>`).join('');this.paintSelection();
  }
  paintSelection(){this.node.querySelectorAll('[data-byte]').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.byte===this.selected)));this.value();this.paintControls();}
  paintControls(){
    const selected=this.selected!==null,editable=this.editing&&!this.item.readOnly&&!this.state.saving;
    this.node.querySelector('[data-binary-edit]').setAttribute('aria-pressed',String(this.editing));this.node.querySelector('[data-binary-edit]').disabled=this.item.readOnly||this.state.saving;
    const input=this.node.querySelector('[data-binary-edit-form] input');input.disabled=!editable||!selected;if(selected&&document.activeElement!==input)input.value=this.bytes[this.selected].toString(16).padStart(2,'0');this.node.querySelector('[data-binary-edit-form] button').disabled=input.disabled;
    this.node.querySelector('[data-binary-undo]').disabled=!this.state.undo.length||this.state.saving;this.node.querySelector('[data-binary-redo]').disabled=!this.state.redo.length||this.state.saving;
    this.node.querySelector('[data-binary-save]').disabled=!this.state.patches.size||this.state.saving;this.node.querySelector('[data-binary-build]').disabled=this.state.saving;
    this.node.querySelector('.binary-modified').textContent=this.state.saving?'Guardando…':this.state.patches.size?this.state.patches.size+' bytes modificados':'Sin cambios';
    this.node.querySelector('[data-byte-prev]').disabled=this.item.offset===0||this.state.saving;this.node.querySelector('[data-byte-next]').disabled=this.item.offset+this.item.count>=this.item.size||this.state.saving;
  }
  edit(hex){
    if(!this.editing||this.state.saving||this.item.readOnly||this.selected===null)return;
    if(!/^[\da-f]{2}$/i.test(hex))return this.error('Escribe exactamente dos dígitos hexadecimales.');
    const offset=this.item.offset+this.selected,after=parseInt(hex,16),before=this.bytes[this.selected];if(after===before)return;
    if(!this.state.patches.has(offset)&&this.state.patches.size>=65536)return this.error('Guarda antes de modificar más de 64 KiB.');
    const operation={offset,before,after,original:this.original[this.selected]};this.state.undo.push(operation);if(this.state.undo.length>65536)this.state.undo.shift();this.state.redo=[];this.apply(operation,after);this.error('');
  }
  apply(op,value){if(value===op.original)this.state.patches.delete(op.offset);else this.state.patches.set(op.offset,{before:op.original,after:value});this.paintBytes();this.actions.changed?.();}
  undo(redo=false){if(this.state.saving)return;const from=redo?this.state.redo:this.state.undo,to=redo?this.state.undo:this.state.redo,op=from.pop();if(op){to.push(op);this.apply(op,redo?op.after:op.before);}}
  value(){this.node.querySelector('.binary-value').textContent=this.selected===null?'Selecciona un byte para inspeccionarlo':'0x'+(this.item.offset+this.selected).toString(16)+' · '+byteValue(this.bytes,this.selected,this.node.querySelector('footer input').checked);}
  saved(item){this.state.revision=item.revision;this.state.patches.clear();this.state.undo=[];this.state.redo=[];Object.assign(this.record,item);this.render(item);this.error(item.backup?'Guardado. Copia previa: '+item.backup:'');this.node.querySelector('.binary-error').classList.add('binary-save-result');}
  dispose(){this.epoch++;this.node.remove();}
}
