import {icon,escapeHTML as esc} from './icons.js';

/** Results belong to a specific buffer and architecture. Editing invalidates them. */
export class AssemblyWorkbench{
  constructor(profiles){this.profiles=profiles;this.host=profiles.host;this.architecture='x86_64';this.engine='llvm';this.system='linux';this.engines=new Map();this.systems=new Map();this.architectures=new Map();this.resultTab=null;this.stdin='';this.steps=0;this.sequence=0;this.exampleIndex=0;this.decimal=false;}
  async load(){if(this.catalog)return;this.catalog=await this.host.platform.api('/simulation');this.paint();}
  paint(){
    const container=this.profiles.tools,text=this.host.editor.getValue?.()||'',path=this.host.editor.current||'';
    if(this.enginePath!==path){this.enginePath=path;this.engine=this.engines.get(path)||(/\becall\b/.test(text)?'rars':/\$(?:a[0-3]|v[01]|t[0-9])\b/.test(text)?'mars':/\.asm$/i.test(path)&&!/^\s*\.intel_syntax/m.test(text)?'nasm':'llvm');this.architecture=this.architectures.get(path)||(this.engine==='nasm'&&/^\s*\[?bits\s+32\b/im.test(text)?'x86':'x86_64');}
    this.system=this.systems.get(path)||text.match(/^\s*;\s*(?:sistema|system|os|target)\s*:\s*(linux|windows)\b/im)?.[1].toLowerCase()||(this.catalog?.nativeSystem==='windows'?'windows':'linux');
    const supported=this.catalog?.engines.find(x=>x.id===this.engine);if(supported&&!supported.architectures.includes(this.architecture))this.architecture=supported.architectures[0];
    const fingerprint=path+'\0'+text+'\0'+this.architecture+'\0'+this.engine+'\0'+this.system;
    if(this.fingerprint!==fingerprint){this.fingerprint=fingerprint;this.result=null;this.resultTab=null;this.previousRegisters={};this.steps=0;this.sequence++;}
    this.host.editor.assemblyArchitecture=this.architecture;
    const engine=this.catalog?.engines?.find(x=>x.id===this.engine),available=this.catalog?.architectures.filter(a=>!engine||engine.architectures.includes(a.id));
    const architecture=this.catalog?.architectures.find(x=>x.id===this.architecture);
    const examples=(this.engine==='nasm'?engine?.examples?.[this.system]?.[this.architecture]:engine?.examples?.[this.architecture])||architecture?.examples||[];
    container.innerHTML=`<header class="profile-tool-heading asm-heading"><div class="asm-title"><strong>${icon('cpu')} Laboratorio ASM</strong><small>${esc(engine?.label||'LLVM + Unicorn')} · CPU simulada · búfer sin guardar</small></div><div class="asm-controls"><select aria-label="Motor ASM">${(this.catalog?.engines||[{id:'llvm',label:'LLVM + Unicorn'}]).map(e=>`<option value="${e.id}" ${e.id===this.engine?'selected':''}>${esc(e.label)}</option>`).join('')}</select><select aria-label="Arquitectura ASM">${(available||[{id:'x86_64',label:'Detectando herramientas…'}]).map(a=>`<option value="${a.id}" ${a.id===this.architecture?'selected':''}>${esc(a.label)}</option>`).join('')}</select>${this.engine==='nasm'?`<select aria-label="Sistema NASM"><option value="linux" ${this.system==='linux'?'selected':''}>Linux · ELF</option><option value="windows" ${this.system==='windows'?'selected':''}>Windows · PE/COFF</option></select>`:''}<button class="secondary-button" data-asm="step" ${!path||this.busy||engine?.step===false?'disabled':''}>${icon('arrow-right')} Paso</button><button class="primary-button" data-asm="run" ${!path||this.busy?'disabled':''}>${icon('play')} Simular</button><button class="icon-button" data-asm="reset" title="Reiniciar simulación">${icon('refresh')}</button>${this.profiles.placement('profile-assembly')}</div><details class="asm-configuration"><summary>Ejemplos, entrada y destino</summary><div class="asm-destinations"><button class="secondary-button" data-asm="native" ${!path||this.catalog?.nativeArchitecture!==this.architecture?'disabled':''} title="Requiere la arquitectura y el ABI de este equipo">${icon('play')}Ejecutar en este equipo</button><button class="secondary-button" data-asm="vm">${icon('cube')}Máquinas de Lantern</button><small>Simular usa la CPU del motor. Ejecutar usa la arquitectura y el ABI del equipo; una VM tiene su propio sistema.</small></div><div class="asm-example-row"><select aria-label="Ejemplo ASM">${examples.map((x,i)=>`<option value="${i}" ${i===this.exampleIndex?'selected':''}>${esc(x.label)}</option>`).join('')}</select><button class="secondary-button" data-asm="example" ${!path||!architecture?'disabled':''}>Cargar ejemplo</button><small>El archivo original se guarda cuando tú lo decides.</small></div>${['rars','mars'].includes(this.engine)?`<label class="asm-input-label">Entrada del programa<textarea aria-label="Entrada simulada" rows="2" maxlength="65536">${esc(this.stdin)}</textarea></label>`:''}</details></header><div class="asm-result" role="status">${this.resultMarkup()}</div>`;
    this.profiles.bindPlacement();
    container.querySelector('[aria-label="Motor ASM"]').onchange=e=>{this.engine=e.target.value;this.engines.set(path,this.engine);const selected=this.catalog.engines.find(x=>x.id===this.engine);if(!selected.architectures.includes(this.architecture))this.architecture=selected.architectures[0];this.exampleIndex=0;this.paint();};
    const system=container.querySelector('[aria-label="Sistema NASM"]');if(system)system.onchange=e=>{this.systems.set(path,e.target.value);this.paint();};
    const input=container.querySelector('[aria-label="Entrada simulada"]');if(input)input.oninput=e=>{this.stdin=e.target.value;this.result=null;this.resultTab=null;this.previousRegisters={};this.steps=0;this.sequence++;container.querySelector('.asm-result').innerHTML=this.resultMarkup();};
    container.querySelector('[aria-label="Arquitectura ASM"]').onchange=e=>{this.architecture=e.target.value;this.architectures.set(path,this.architecture);this.exampleIndex=0;this.paint();};
    container.querySelector('[aria-label="Ejemplo ASM"]').onchange=e=>{this.exampleIndex=Number(e.target.value);};
    container.querySelectorAll('[data-asm]').forEach(button=>button.onclick=()=>this.profiles.safe(async()=>{
      const action=button.dataset.asm;
      if(action==='vm')return this.host.desktop.handle('lantern-environments');
      if(action==='native'){const info=await this.host.platform.api('/simulation');if(this.engine==='nasm'&&info.nativeSystem!==this.system)throw Error('El destino NASM seleccionado es '+this.system+'. Simúlalo aquí o utiliza una estación o VM con ese sistema.');if(info.nativeArchitecture!==this.architecture)throw Error('La arquitectura seleccionada no es la del equipo. Usa el motor simulado o prepara una VM y su toolchain.');return this.host.perform('run');}
      if(action==='reset'){this.result=null;this.previousRegisters={};this.steps=0;this.paint();return;}
      if(action==='format'){this.decimal=!this.decimal;this.paint();return;}
      if(action==='example'){if(text.trim()&&!await this.host.platform.host.confirmDialog('Cargar ejemplo ASM','Sustituir el búfer actual por el ejemplo de '+architecture.label+'. Puedes deshacerlo con Ctrl+Z.','Cargar ejemplo'))return;this.host.editor.insertText(examples[this.exampleIndex]?.source||architecture.example,true);this.paint();return;}
      if(!await this.host.ensureTrust())return;
      const seq=++this.sequence;this.busy=true;this.paint();
      try{const result=await this.host.platform.api('/simulation/run',{engine:this.engine,system:this.system,path,stdin:this.stdin,architecture:this.architecture,source:this.host.editor.getValue(),steps:action==='step'?Math.min(++this.steps,10000):10000});if(seq===this.sequence){this.previousRegisters=this.result?.registers||{};this.result=result;this.steps=result.executed||0;}}
      finally{this.busy=false;this.paint();if(this.result)container.scrollTop=Math.max(0,container.querySelector('.asm-result').offsetTop-container.offsetTop-container.querySelector('.asm-heading').offsetHeight);}
    }));
    for(const tab of container.querySelectorAll('[data-asm-result]'))tab.onclick=()=>{this.resultTab=tab.dataset.asmResult;this.paint();};
    if(!this.catalog)this.profiles.safe(()=>this.load());
  }
  resultMarkup(){
    if(this.busy)return '<div class="asm-waiting" role="status">Ensamblando y ejecutando el búfer…</div>';
    const r=this.result;if(!r)return '<div class="asm-idle"><span>'+icon('cpu')+'</span><div><strong>Del código a cada instrucción.</strong><p>Elige el motor y la arquitectura. Simula el búfer sin modificar tu archivo.</p></div></div>';
    if(r.status==='error')return '<pre class="lab-error">'+esc(r.error)+'</pre>';
    const tabs=[...(r.output!==undefined?[['output','Salida']]:[]),['registers','Registros'],...(r.instructions?.length?[['instructions','Instrucciones']]:[]),...(r.memory?[['memory','Memoria']]:[])];
    const active=tabs.some(([id])=>id===this.resultTab)?this.resultTab:tabs[0][0];
    let content='';
    if(active==='output')content='<pre class="asm-program-output" aria-label="Salida del programa">'+esc(r.output||'El programa no ha escrito salida.')+'</pre>';
    if(active==='registers')content='<dl class="asm-registers">'+Object.entries(r.registers||{}).map(([key,value])=>`<div class="${key in this.previousRegisters&&this.previousRegisters[key]!==value?'changed':''}"><dt>${key}</dt><dd title="${esc(value)}">${esc(this.decimal?BigInt(value).toString():value)}</dd></div>`).join('')+'</dl>';
    if(active==='instructions')content='<div class="asm-instructions">'+r.instructions.map(i=>`<div class="${i.address===r.pc?'current':''}"><code>${esc(i.address)}</code><code>${esc(i.bytes)}</code><code>${esc(i.text)}</code></div>`).join('')+'</div>';
    if(active==='memory')content='<pre class="asm-memory">'+esc(r.memory)+'</pre>';
    return `<header class="asm-status"><span class="asm-state-dot"></span><strong>${esc({complete:'Finalizada',paused:'En pausa',fault:'Error de CPU'}[r.status]||r.status)}</strong><span>${r.executed??'—'} instrucciones${r.exitCode!==undefined&&r.exitCode!==null?' · salida '+esc(r.exitCode):''}${r.format?' · '+esc(r.format):''}${r.pc?' · '+esc(r.pc):''}</span><button class="text-button" data-asm="format">${this.decimal?'Decimal':'Hexadecimal'}</button></header><nav class="asm-result-tabs" aria-label="Resultados ASM">${tabs.map(([id,label])=>`<button type="button" data-asm-result="${id}" aria-pressed="${id===active}">${label}</button>`).join('')}</nav><div class="asm-result-content">${r.error?'<pre class="lab-error">'+esc(r.error)+'</pre>':''}${content}</div><p class="asm-adapter-note">${esc(r.note)}</p>`;
  }
}
