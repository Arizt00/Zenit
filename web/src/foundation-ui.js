import {icon,escapeHTML as esc} from './icons.js';

const SECTIONS=[['languages','code','Lenguajes'],['project','folder','Proyecto'],['assembly','cpu','Assembly'],['containers','cube','Contenedores'],['machines','split','Máquinas']];
const NAMES={python:'Python',gcc:'C · GCC','g++':'C++ · GCC',clang:'LLVM · ASM',java:'Java',javac:'Compilador Java',bash:'Bash',ncc:'nC',node:'Node · extensiones',docker:'Docker CLI','qemu-system-x86_64':'QEMU',mvn:'Maven',gradle:'Gradle'};
const BRANDS={python:'python',gcc:'c','g++':'cplusplus',clang:'llvm',java:'openjdk',docker:'docker',mvn:'apachemaven',gradle:'gradle'};
const GROUPS={languages:['python','gcc','g++','clang','java','javac','ncc','node'],project:['mvn','gradle','bash'],containers:['docker'],machines:['qemu-system-x86_64']};
const action=(id,name,glyph='play')=>`<button class="secondary-button" data-lab-action="${id}">${icon(glyph)}<span>${name}</span></button>`;

/** One mounted sheet. Switching sections never replaces forms. */
export class FoundationUI{
  constructor(host){
    this.host=host;this.section='languages';this.generation=0;
    const button=document.createElement('button');button.className='foundation-toggle secondary-button';button.title='Lenguajes, dependencias, Docker y máquinas';button.innerHTML=icon('cpu')+'<span>Laboratorio</span>';button.onclick=()=>host.platform.safe(()=>this.open());document.querySelector('.top-actions').prepend(button);
    host.commands.push(['foundation','cpu','Zénit: abrir laboratorio y dependencias','']);
    const handle=host.desktop.handle.bind(host.desktop);host.desktop.handle=async command=>command==='foundation'?(await this.open(),true):handle(command);
  }
  async open(){
    const h=this.host;if(h.platform.page==='foundation'&&this.root?.isConnected)return;
    h.studio.enter();h.platform.openPage('foundation','<div class="foundation-page"><div class="lab-empty" role="status">Preparando tu laboratorio…</div></div>');
    const generation=++this.generation;
    try{
      const [sdk,machines,languages]=await Promise.all([h.platform.api('/foundation'),h.platform.api('/machines'),h.platform.api('/languages')]);
      if(h.platform.page!=='foundation'||generation!==this.generation)return;
      Object.assign(this,{sdk,machines,languages});this.paint();
    }catch(error){
      if(h.platform.page==='foundation'&&generation===this.generation){const node=document.querySelector('.lab-empty');node.textContent='No se pudo cargar el laboratorio. '+error.message;node.setAttribute('role','alert');}
      throw error;
    }
  }
  paint(){
    const h=this.host,{sdk,languages}=this;
    h.platform.openPage('foundation',`<div class="foundation-page">
      <header class="lab-heading"><div><span class="platform-eyebrow">ZÉNIT · LABORATORIO</span><h2>Tu entorno, en orden.</h2><p>Lenguajes y herramientas conectados a tu proyecto.</p></div><div class="lab-heading-actions"><span class="lab-inventory-summary"></span><button class="icon-button" data-lab-refresh aria-label="Actualizar herramientas" title="Actualizar herramientas">${icon('refresh')}</button><button class="icon-button" data-platform="close-page" aria-label="Cerrar laboratorio" title="Volver al editor">${icon('close')}</button></div></header>
      <nav class="lab-navigation" role="tablist" aria-label="Secciones del laboratorio">${SECTIONS.map(([id,glyph,name])=>`<button type="button" role="tab" id="lab-tab-${id}" data-lab-section="${id}" aria-controls="lab-section-${id}">${icon(glyph)}<span>${name}</span></button>`).join('')}</nav>
      <div class="lab-feedback" role="status" hidden></div><div class="lab-content">
      <section role="tabpanel" id="lab-section-languages" aria-labelledby="lab-tab-languages" data-lab-panel="languages"><header class="lab-section-heading"><div><h3>Lenguajes y compiladores</h3><p>Rutas detectadas; el estado de cada ejecución aparece en la terminal.</p></div><label class="lab-filter">${icon('search')}<input type="search" placeholder="Filtrar lenguajes…" aria-label="Filtrar lenguajes"></label><button class="icon-button" data-lab-docs aria-label="Configurar lenguajes" title="Configurar lenguajes">${icon('sliders')}</button></header><div class="lab-tools" data-lab-tools="languages"></div><div class="lab-filter-empty lab-empty" hidden>No hay herramientas que coincidan.</div><p class="lab-note">Una ruta local no certifica todas las funciones del compilador. Amplía una herramienta para ver su ubicación.</p></section>
      <section role="tabpanel" id="lab-section-project" aria-labelledby="lab-tab-project" data-lab-panel="project" hidden><header class="lab-section-heading"><div><h3>Dependencias del proyecto</h3><p>Entornos propios para tus paquetes y acciones en la terminal integrada.</p></div></header><div class="lab-project-grid"><article class="lab-workflow">${icon('code')}<h4>Python</h4><p>Crea .venv y resuelve requirements.txt dentro del proyecto.</p><div class="lab-actions">${action('venv','Crear .venv','plus')}${action('pip','Instalar requisitos','download')}</div></article><article class="lab-workflow">${icon('build')}<h4>Java</h4><p>Comprueba los gestores antes de ejecutar los objetivos de tu proyecto.</p><div class="lab-actions">${action('maven','Comprobar Maven')}${action('gradle','Comprobar Gradle')}</div></article><article class="lab-workflow">${icon('terminal')}<h4>Shell</h4><p>Abre Bash con el directorio de trabajo del proyecto actual.</p><div class="lab-actions">${action('bash','Abrir Bash','terminal')}</div></article></div><div class="lab-tools lab-tools-secondary" data-lab-tools="project"></div><details class="lab-advanced"><summary>Estándares de C y C++</summary><form id="lab-standards"><div class="lab-form-row">${['c','cpp'].map(key=>`<label>${key==='c'?'C':'C++'}<select name="${key}">${sdk.standards[key].map(s=>`<option ${s===(languages.config.languages[key]?.standard||(key==='c'?'c11':'c++17'))?'selected':''}>${s}</option>`).join('')}</select></label>`).join('')}<button class="secondary-button">Guardar estándares</button></div><small>El compilador determina las características disponibles. Los perfiles personalizados tienen prioridad.</small></form></details><p class="lab-note">${esc(sdk.dependencyPolicy)}</p></section>
      <section role="tabpanel" id="lab-section-assembly" aria-labelledby="lab-tab-assembly" data-lab-panel="assembly" hidden><div class="lab-assembly-intro"><span class="lab-workspace-symbol">${icon('cpu')}</span><span class="platform-eyebrow">EXPLORA CADA INSTRUCCIÓN</span><h3>El código, por dentro.</h3><p>Trabaja sobre el búfer ASM del editor. Sigue las instrucciones y observa registros, memoria y flags en el simulador.</p><div class="lab-architectures">${['x86','x86-64','ARM32','ARM64','RISC-V64'].map(a=>`<span>${a}</span>`).join('')}</div><button class="primary-button" id="lab-assembly">${icon('arrow-right')} Abrir espacio Assembly</button><small>El simulador ejecuta un subconjunto documentado. Las instrucciones no compatibles muestran un error.</small></div></section>
      <section role="tabpanel" id="lab-section-containers" aria-labelledby="lab-tab-containers" data-lab-panel="containers" hidden><header class="lab-section-heading"><div><h3>Contenedores</h3><p>Conecta con el motor Docker de tu equipo.</p></div></header><div class="lab-tools" data-lab-tools="containers"></div><article class="lab-workflow lab-container-actions"><h4>Comprueba tu conexión</h4><p>Estas acciones ejecutan Docker y muestran su respuesta real. El cliente instalado y el motor en ejecución son estados diferentes.</p><div class="lab-actions">${action('docker-info','Versión y motor')}${action('docker-ps','Ver contenedores')}${action('docker-compose','Comprobar Compose')}</div></article></section>
      <section role="tabpanel" id="lab-section-machines" aria-labelledby="lab-tab-machines" data-lab-panel="machines" hidden><header class="lab-section-heading"><div><h3>Máquinas · solo comandos</h3><p>Consolas conectadas al proyecto y discos persistentes para Arch.</p></div><button class="secondary-button" id="lab-create-arch" ${!this.machines.archImage?'disabled':''}>${icon('plus')} Preparar Arch</button></header><div class="lab-tools" data-lab-tools="machines"></div><div class="lab-machine-list"></div><details class="lab-advanced lab-ssh-details"><summary>Conectar macOS, Windows 7 o Arch por SSH</summary><p>Usa una máquina existente con SSH. macOS requiere hardware Apple; Windows 7 necesita una instalación con licencia. No se incluyen imágenes de esos sistemas.</p><form id="lab-ssh" class="lab-form-row"><label>Sistema<select name="type"><option value="macos">macOS</option><option value="windows7">Windows 7</option><option value="arch">Arch Linux</option></select></label><label>Dirección<input name="host" required placeholder="192.168.1.20" maxlength="253"></label><label>Usuario<input name="user" required placeholder="usuario" maxlength="64"></label><label>Puerto<input name="port" type="number" value="22" min="1" max="65535" required></label><button class="secondary-button">Añadir conexión</button></form></details></section>
      </div></div>`);
    this.root=document.querySelector('.foundation-page');const page=this.root;
    page.querySelector('[data-lab-docs]').onclick=()=>h.studio.configureLanguages();
    page.querySelector('[data-lab-refresh]').onclick=e=>this.operation(e.currentTarget,async()=>{this.sdk=await h.platform.api('/foundation');if(page.isConnected)this.updateTools();},'Herramientas actualizadas.');
    page.querySelectorAll('[data-lab-section]').forEach(button=>button.onclick=()=>this.selectSection(button.dataset.labSection));
    page.querySelector('.lab-navigation').onkeydown=e=>{const tabs=[...page.querySelectorAll('[role=tab]')],index=tabs.indexOf(document.activeElement);if(index<0)return;let next;if(e.key==='ArrowRight')next=(index+1)%tabs.length;if(e.key==='ArrowLeft')next=(index+tabs.length-1)%tabs.length;if(e.key==='Home')next=0;if(e.key==='End')next=tabs.length-1;if(next!==undefined){e.preventDefault();this.selectSection(tabs[next].dataset.labSection);tabs[next].focus();}};
    page.querySelector('.lab-filter input').oninput=()=>this.filterTools();
    page.querySelectorAll('[data-lab-action]').forEach(button=>button.onclick=()=>this.operation(button,async()=>{if(!await h.ensureTrust())return false;const data=await h.platform.api('/foundation/action',{action:button.dataset.labAction});h.platform.host.showConsole('terminal');if(data.profile)await h.platform.attachTerminal(data);else if(data.job)await h.watchJob(data.job);}));
    page.querySelector('#lab-standards').onsubmit=e=>{e.preventDefault();this.operation(e.submitter,async()=>{const form=new FormData(e.target),config=structuredClone(this.languages.config);for(const key of ['c','cpp'])config.languages[key]={...config.languages[key],standard:form.get(key)};await h.platform.api('/languages/config',config);this.languages.config=config;},'Estándares guardados.');};
    page.querySelector('#lab-assembly').onclick=()=>h.platform.safe(async()=>{await h.studio.save({workspaceStyle:'assembly'});h.platform.closePage();h.profiles.apply();});
    page.querySelector('#lab-create-arch').onclick=e=>this.operation(e.currentTarget,async()=>{if(!await h.ensureTrust())return false;this.machines=await h.platform.api('/machines/create',{type:'arch'});if(page.isConnected)this.updateMachines();},'Perfil Arch preparado.');
    page.querySelector('#lab-ssh').onsubmit=e=>{e.preventDefault();this.operation(e.submitter,async()=>{if(!await h.ensureTrust())return false;const body=Object.fromEntries(new FormData(e.target));body.port=Number(body.port);this.machines=await h.platform.api('/machines/create',body);if(page.isConnected)this.updateMachines();},'Conexión añadida.');};
    this.updateTools();this.updateMachines();this.selectSection(this.section);
  }
  selectSection(id){
    if(!SECTIONS.some(s=>s[0]===id))return;this.section=id;
    this.root.querySelectorAll('[data-lab-panel]').forEach(panel=>panel.hidden=panel.dataset.labPanel!==id);
    this.root.querySelectorAll('[data-lab-section]').forEach(button=>{const selected=button.dataset.labSection===id;button.setAttribute('aria-selected',String(selected));button.tabIndex=selected?0:-1;});
  }
  updateTools(){
    for(const container of this.root.querySelectorAll('[data-lab-tools]')){
      const ids=GROUPS[container.dataset.labTools];container.innerHTML=this.sdk.tools.filter(t=>ids.includes(t.id)).map(t=>`<article class="lab-tool ${t.path?'available':'missing'}" data-lab-tool="${esc(t.id)}"><span class="lab-tool-glyph">${BRANDS[t.id]?`<img src="/assets/languages/${BRANDS[t.id]}.svg" alt="">`:icon(({javac:'layout',bash:'terminal',ncc:'cpu',node:'code','qemu-system-x86_64':'split'})[t.id]||'cpu')}</span><div><strong>${NAMES[t.id]||esc(t.id)}</strong><span class="lab-tool-state">${t.path?(t.bundled?'Base de Zénit':'Ruta del sistema'):'No detectado'}</span><details><summary>${t.path?'Ver ubicación':'Configurar herramienta'}</summary>${t.path?`<code>${esc(t.path)}</code>`:'<p>Configura su ruta en Ajustes · Lenguajes y herramientas.</p>'}</details></div></article>`).join('');
    }
    const found=this.sdk.tools.filter(t=>t.path).length;this.root.querySelector('.lab-inventory-summary').textContent=`${found} de ${this.sdk.tools.length} rutas detectadas`;this.filterTools();
  }
  filterTools(){
    const query=this.root.querySelector('.lab-filter input').value.trim().toLocaleLowerCase();let count=0;
    this.root.querySelectorAll('[data-lab-tools=languages] [data-lab-tool]').forEach(node=>{node.hidden=!node.textContent.toLocaleLowerCase().includes(query);if(!node.hidden)count++;});
    this.root.querySelector('.lab-filter-empty').hidden=count>0;
  }
  updateMachines(){
    const h=this.host,container=this.root.querySelector('.lab-machine-list');
    container.innerHTML=this.machines.profiles.map(p=>`<article><span class="lab-machine-icon">${icon('terminal')}</span><div><strong>${esc(p.name)}</strong><small>${p.mode==='ssh'?esc(p.user+'@'+p.host+':'+p.port):`QEMU · ${Number(p.cpus)} núcleo(s) · ${Number(p.memory)/1024} GiB · disco 16 GiB`}</small></div><button class="secondary-button" data-machine-start="${esc(p.id)}">Abrir consola</button><button class="icon-button" data-machine-stop="${esc(p.id)}" ${this.machines.active?.[p.id]?'':'disabled'} title="Detener máquina" aria-label="Detener ${esc(p.name)}">${icon('stop')}</button></article>`).join('')||'<div class="lab-empty">Aún no hay máquinas conectadas.<small>Prepara Arch o añade una conexión SSH.</small></div>';
    container.querySelectorAll('[data-machine-start]').forEach(button=>button.onclick=()=>this.operation(button,async()=>{if(!await h.ensureTrust())return false;const terminal=await h.platform.api('/machines/start',{id:button.dataset.machineStart});h.platform.host.showConsole('terminal');if(!h.platform.terminals.has(terminal.id))await h.platform.attachTerminal(terminal);else h.platform.selectTerminal(terminal.id);this.machines=await h.platform.api('/machines');if(this.root.isConnected)this.updateMachines();}));
    container.querySelectorAll('[data-machine-stop]').forEach(button=>button.onclick=()=>this.operation(button,async()=>{this.machines=await h.platform.api('/machines/stop',{id:button.dataset.machineStop});if(this.root.isConnected)this.updateMachines();},'Máquina detenida.'));
  }
  async operation(button,fn,message){
    if(button?.disabled)return;const root=this.root,feedback=root.querySelector('.lab-feedback');if(button){button.disabled=true;button.setAttribute('aria-busy','true');}feedback.hidden=true;
    try{const result=await fn();if(result!==false&&message&&root.isConnected){feedback.textContent=message;feedback.dataset.kind='success';feedback.hidden=false;}}
    catch(error){if(root.isConnected){feedback.textContent=error.message;feedback.dataset.kind='error';feedback.hidden=false;}this.host.platform.report(error);}
    finally{if(button?.isConnected){button.disabled=false;button.removeAttribute('aria-busy');}}
  }
}
