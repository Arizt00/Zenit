import {icon} from './icons.js';
const LEVELS=[[0,'Desactivado'],[1,'Trace'],[2,'Debug'],[3,'Info'],[4,'Warning'],[5,'Error']];
const id=item=>item.extension+':'+item.key;

/** Output channel controls dispatch back to their owning Node extension. */
export class ExtensionOutputUI{
  constructor(host){
    this.host=host;this.items=new Map();this.visible=false;this.text='';
    this.root=document.createElement('div');this.root.className='extension-output-toolbar';this.root.hidden=true;this.root.innerHTML=`<button class="secondary-button" data-output-channel aria-label="Elegir canal de salida">${icon('terminal')}<span></span>${icon('chevron-down')}</button><button class="secondary-button" data-output-level aria-label="Nivel de registro"><span></span>${icon('chevron-down')}</button><button class="icon-button" data-output-clear title="Limpiar canal" aria-label="Limpiar canal">${icon('trash')}</button><button class="icon-button" data-output-copy title="Copiar salida" aria-label="Copiar salida">${icon('copy')}</button>`;document.getElementById('terminal-content').before(this.root);
    this.root.querySelector('[data-output-channel]').onclick=e=>host.platform.host.showMenu(e.currentTarget,[...this.items.values()].map(item=>({label:item.name,shortcut:item.extension,icon:'terminal',run:()=>this.select(id(item))})),'Canales de salida');
    this.root.querySelector('[data-output-level]').onclick=e=>host.platform.host.showMenu(e.currentTarget,LEVELS.map(([level,label])=>({label,icon:this.current()?.logLevel===level?'check':undefined,run:()=>this.control('logLevel',level)})),'Nivel de registro');
    this.root.querySelector('[data-output-clear]').onclick=()=>this.control('clear');this.root.querySelector('[data-output-copy]').onclick=()=>host.platform.safe(async()=>{await navigator.clipboard.writeText(this.text||'');host.notify('Salida copiada.');});
  }
  current(){return this.items.get(this.selected);}
  select(key){this.selected=key;this.revision=null;this.text='';this.labels();this.render();return this.host.platform.safe(()=>this.refresh());}
  sync(items){
    this.items=new Map(items.map(item=>[id(item),item]));if(!this.items.has(this.selected)){this.selected=this.items.keys().next().value;this.revision=null;this.text='';if(this.visible)document.getElementById('terminal-content').textContent='';}
    this.labels();if(this.visible)this.host.platform.safe(()=>this.refresh());
  }
  event(event){
    this.dismissals ||= new Map();const dismissed=id(event);if(event.dismiss&&event.dismiss!==this.dismissals.get(dismissed)){this.dismissals.set(dismissed,event.dismiss);if(this.selected===dismissed&&this.visible)this.host.platform.host.dock.hide('console');}
    const key=id(event);this.reveals ||= new Map();if(event.disposed){this.items.delete(key);this.reveals.delete(key);if(this.selected===key){this.selected=this.items.keys().next().value;this.revision=null;this.text='';if(this.visible)document.getElementById('terminal-content').textContent='';}this.labels();return;}
    this.items.set(key,event);if(event.visible&&event.reveal!==this.reveals.get(key)){this.reveals.set(key,event.reveal);this.selected=key;const previous=document.activeElement;this.host.showConsole('output');if(event.preserveFocus&&previous?.isConnected)previous.focus({preventScroll:true});}
    if(this.selected===key){this.text=event.text||'';this.revision=event.revision;this.labels();this.render();}
  }
  labels(){
    const current=this.current(),hidden=!this.visible||!current;if(this.root.hidden!==hidden)this.root.hidden=hidden;if(!current)return;
    const title=this.root.querySelector('[data-output-channel] span');if(title.textContent!==current.name)title.textContent=current.name;
    const level=this.root.querySelector('[data-output-level]'),name=LEVELS.find(x=>x[0]===current.logLevel)?.[1]||'Info';if(level.hidden!==!current.log)level.hidden=!current.log;if(level.querySelector('span').textContent!==name)level.querySelector('span').textContent=name;
  }
  setVisible(value){this.visible=value;this.labels();if(value)this.host.platform.safe(()=>this.refresh());}
  async refresh(){
    const current=this.current();if(!current||!this.visible||this.disposed)return false;const selected=this.selected;
    if(this.revision!==current.revision){
      if(this.fetching){this.refreshAgain=true;return true;}this.fetching=true;
      try{const item=await this.host.platform.api('/extensions/output?'+new URLSearchParams({extension:current.extension,key:current.key}));if(this.disposed||selected!==this.selected)return true;this.items.set(selected,item);this.text=item.text||'';this.revision=item.revision;this.labels();}
      finally{this.fetching=false;if(this.refreshAgain){this.refreshAgain=false;queueMicrotask(()=>this.host.platform.safe(()=>this.refresh()));}}
    }
    return this.render();
  }
  render(){
    const current=this.current();if(!current||!this.visible)return false;
    const pane=document.getElementById('terminal-content');if(pane.textContent!==this.text){const bottom=pane.scrollHeight-pane.scrollTop-pane.clientHeight<40;pane.textContent=this.text||'';if(bottom)pane.scrollTop=pane.scrollHeight;}if(pane.dataset.extensionOutput!==this.selected)pane.dataset.extensionOutput=this.selected;const label='Salida · '+current.name;if(pane.getAttribute('aria-label')!==label)pane.setAttribute('aria-label',label);return true;
  }
  control(action,level){return this.host.platform.safe(async()=>{const current=this.current();if(!current)return;await this.host.platform.api('/extensions/output/control',{extension:current.extension,key:current.key,action,level});});}
  dispose(){this.disposed=true;this.root.remove();}
}
