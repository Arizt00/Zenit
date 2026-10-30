import {icon} from './icons.js';

/** Describe the selected process, independently of the file currently edited. */
export class ConsoleContext{
 constructor(host){
  this.h=host;this.p=host.platform;this.task=null;this.signature='';
  this.node=document.createElement('section');this.node.className='console-context';this.node.hidden=true;this.node.setAttribute('aria-label','Contexto de ejecución');
  this.node.innerHTML=`<span class="console-context-file">${icon('file')}<strong></strong></span><span class="console-context-target">${icon('cpu')}<span></span></span><span class="console-context-state" role="status"></span><button class="text-button" data-console-input>${icon('terminal')}<span></span></button><button class="icon-button" data-console-stop>${icon('stop')}</button>`;
  document.querySelector('#terminal-panel').append(this.node);
  this.node.querySelector('[data-console-input]').onclick=()=>{if(this.p.showingPTY)this.p.focusTerminal(this.p.activeTerminal);else document.querySelector('#terminal-input')?.focus();};
  this.node.querySelector('[data-console-stop]').onclick=()=>this.p.safe(async()=>{if(this.stopping)return;this.stopping=true;this.update();try{const t=this.p.showingPTY&&this.p.terminals.get(this.p.activeTerminal);if(t?.execution?.running)await this.p.api('/terminals/stop-run',{id:t.id});else if(t&&!t.closed&&t.profile.kind==='hacker')await this.p.api('/terminals/close',{id:t.id});else if(this.task?.running)await this.h.api('/stop',{id:this.task.id});}finally{this.stopping=false;this.update();}});
  const render=this.p.renderActiveTerminal.bind(this.p);this.p.renderActiveTerminal=(...args)=>{const result=render(...args);this.update();return result;};
  this.state=e=>{if(e.detail.running)this.task=e.detail;else if(this.task?.id===e.detail.id)this.task=null;this.update();};document.addEventListener('zenit:task-state',this.state);
  this.key=e=>{if(e.altKey&&!e.ctrlKey&&e.key.toLowerCase()==='i'&&document.querySelector('#terminal-panel').contains(e.target)&&!this.node.hidden){e.preventDefault();e.stopPropagation();this.node.querySelector('[data-console-input]:not(:disabled)')?.click();}};document.addEventListener('keydown',this.key);
  this.update();
 }
 update(){
  const t=this.p.showingPTY?this.p.terminals.get(this.p.activeTerminal):null,task=!t&&this.task,execution=t?.execution,context=t?.profile?.context||{},path=(execution?.running?execution.path:null)||context.path||task?.path||t?.profile?.label||'',target=(execution?.running?execution.target:null)||context.target?.label||context.target||(t?this.p.t('Este equipo','This device'):this.h.target?.())||'',running=t?!t.closed&&(t.profile.kind==='hacker'||execution?.running):!!task?.running;
  const input=t?!t.closed:!!task?.running&&!task.preparing,visible=!!t||!!task?.running;
  const state=task?.preparing?this.p.t('Preparando','Preparing'):running?this.p.t('En ejecución','Running'):t?.closed?this.p.t('Finalizada','Finished'):this.p.t('Terminal disponible','Terminal ready');
  const signature=JSON.stringify([path,target,state,input,visible,running,this.stopping]);if(signature===this.signature)return;this.signature=signature;this.node.hidden=!visible;this.node.dataset.state=running?'running':'idle';
  const file=this.node.querySelector('strong');file.textContent=path.split(/[\\/]/).at(-1);file.title=path;
  this.node.querySelector('.console-context-target>span').textContent=target;this.node.querySelector('.console-context-state').textContent=state;
  const button=this.node.querySelector('[data-console-input]');button.disabled=!input;button.querySelector('span').textContent=input?this.p.t('Escribir aquí','Type here'):this.p.t('Entrada no disponible','Input unavailable');button.title=this.p.t('Entrada para ','Input for ')+path+' · Alt+I';button.setAttribute('aria-label',button.title);
  const stop=this.node.querySelector('[data-console-stop]');stop.hidden=!running;stop.disabled=!!this.stopping;stop.title=this.p.t('Detener ','Stop ')+path;stop.setAttribute('aria-label',stop.title);
 }
 dispose(){document.removeEventListener('zenit:task-state',this.state);document.removeEventListener('keydown',this.key);this.node.remove();}
}
