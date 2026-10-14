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
/** Each page reads at most 512 bytes; no model, edit action, or write endpoint. */
export class BinaryView{
  constructor(mount,item,load){
    this.item=item;this.load=load;this.epoch=0;this.node=document.createElement('section');this.node.className='binary-view';
    this.node.innerHTML=`<header><div>${icon('assembly')}<strong>${esc(item.format)}</strong><span>${item.size.toLocaleString()} bytes · Read only</span></div><form><label>Offset <input aria-label="Byte offset" value="0x0" size="12" autocomplete="off"></label><button class="secondary-button">Go</button></form></header><div class="binary-scroll"><table><thead><tr><th>Offset</th><th>Hexadecimal</th><th>ASCII</th></tr></thead><tbody></tbody></table></div><footer><span class="binary-value" role="status">Select a byte to inspect its value</span><label><input type="checkbox" checked> Little endian</label><button class="secondary-button" data-byte-prev>${icon('chevron-left')}Previous</button><button class="secondary-button" data-byte-next>Next${icon('chevron-right')}</button></footer><p class="binary-error" role="alert" hidden></p>`;
    mount.append(this.node);this.render(item);
    this.node.querySelector('form').onsubmit=e=>{e.preventDefault();const raw=this.node.querySelector('form input').value.trim();if(!/^(?:0x[\da-f]+|\d+)$/i.test(raw))return this.error('Enter a decimal or hexadecimal offset.');this.page(Number(raw));};
    this.node.querySelector('[data-byte-prev]').onclick=()=>this.page(Math.max(0,this.item.offset-512));
    this.node.querySelector('[data-byte-next]').onclick=()=>this.page(this.item.offset+512);
    this.node.querySelector('tbody').onclick=e=>{const button=e.target.closest('[data-byte]');if(!button)return;this.selected=+button.dataset.byte;this.node.querySelectorAll('[data-byte]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));this.value();};
    this.node.querySelector('footer input').onchange=()=>this.value();
  }
  error(message){const node=this.node.querySelector('.binary-error');node.textContent=message;node.hidden=!message;}
  async page(offset){const epoch=++this.epoch;this.error('');this.node.setAttribute('aria-busy','true');try{const item=await this.load(this.item.path,offset);if(epoch===this.epoch&&this.node.isConnected)this.render(item);}catch(e){if(epoch===this.epoch)this.error(e.message);}finally{if(epoch===this.epoch)this.node.removeAttribute('aria-busy');}}
  render(item){this.item=item;this.bytes=Uint8Array.from(atob(item.data),c=>c.charCodeAt(0));this.selected=null;this.node.querySelector('form input').value='0x'+item.offset.toString(16);this.node.querySelector('tbody').innerHTML=byteRows(this.bytes,item.offset).map(row=>`<tr><th>${row.offset.toString(16).padStart(8,'0')}</th><td>${row.hex.map((v,i)=>`<button type="button" data-byte="${row.offset-item.offset+i}" aria-label="Byte ${row.offset+i}: ${v}" aria-pressed="false">${v}</button>`).join('')}</td><td>${esc(row.ascii)}</td></tr>`).join('');this.node.querySelector('[data-byte-prev]').disabled=item.offset===0;this.node.querySelector('[data-byte-next]').disabled=item.offset+item.count>=item.size;this.value();}
  value(){this.node.querySelector('.binary-value').textContent=this.selected===null?'Select a byte to inspect its value':'0x'+(this.item.offset+this.selected).toString(16)+' · '+byteValue(this.bytes,this.selected,this.node.querySelector('footer input').checked);}
  dispose(){this.epoch++;this.node.remove();}
}
