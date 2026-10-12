import {DebugWorkspace} from './debug-workspace.js';
import {LanternView} from './lantern.js';
import {icon,escapeHTML as esc,fileIcon} from './icons.js';
import {glassArt,createLumenScene} from './glass.js';
import {normalizeLayout} from './layout-state.js';

const $=s=>document.querySelector(s);
export class LenonStudio {
  constructor(host){this.host=host;this.scenes=new Map();this.profile={};this.searchSequence=0;this.disposed=false;this.queue=Promise.resolve();this.lastBounce=0;this.visibility=()=>{document.documentElement.dataset.appVisible=String(!document.hidden);};this.visibility();document.addEventListener('visibilitychange',this.visibility);}
  t(es,en){return this.host.platform.t(es,en);}
  safe(fn){return this.host.platform.safe(fn);}
  async init(){
    this.profile=await this.host.api('/platform/studio');
    if(this.profile.layout&&this.host.platform.prefs['general.restoreLayout']){this.host.dock.state=normalizeLayout(this.profile.layout);this.host.dock.render();}
    this.host.dock.onChange=()=>{clearTimeout(this.layoutTimer);this.layoutTimer=setTimeout(()=>this.safe(()=>this.save({layout:this.host.dock.snapshot()})),250);};
    this.decorate();this.installMotion();this.renderHome();
    if(!this.profile.onboarded)this.onboarding();else if(this.host.platform.prefs['general.showWelcome']===false)this.enter();
    this.host.platform.onAppearance=()=>{this.updateProfile();this.lantern?.render();for(const scene of this.scenes.values())scene.setMotion(this.host.platform.prefs['appearance.motion']);};
  }
  async save(changes){
    Object.assign(this.profile,changes);
    this.queue=this.queue.catch(()=>{}).then(()=>this.host.api('/platform/studio',changes));
    await this.queue;return this.profile;
  }
  decorate(){
    $('.brand').dataset.action='home';$('.brand-name').innerHTML='ZÉNIT <span>IDE</span>';
    const {version,revision}=this.host.platform.state;
    $('.brand-tagline').textContent=version+' · R'+revision;
    $('.assistant-heading-title h2').textContent='Melody';$('#assistant-panel').setAttribute('aria-label','Melody');
    $('#assistant-hero').innerHTML=glassArt('orb','melody-art')+`<div class="melody-copy"><h3>${this.t('Hola, soy Melody.','Hello, I’m Melody.')}</h3><h4>${this.t('¿En qué puedo ayudarte?','How can I help you?')}</h4><p id="assistant-subtitle">${this.t('Te ayudo a construir, entender y mejorar tu código.<br>¿En qué puedo ayudarte hoy?','Turn ideas into reality.<br>Simpler. Further.')}</p></div><span class="handwritten">${this.t('Ideas<br>en movimiento.','Ideas<br>in motion.')}</span>`;
    const actions=$('#ai-actions');actions.append(actions.querySelector('[data-ai-action="refactor"]'),actions.querySelector('[data-ai-action="fix"]'));
    actions.querySelectorAll('button').forEach(b=>b.insertAdjacentHTML('beforeend',icon('chevron-right')));
    $('#ai-form').insertAdjacentHTML('beforeend',`<div class="composer-context"><button type="button" data-action="ai-settings">${icon('plus')} ${this.t('Contexto','Context')}</button><span>${this.t('Tú eliges el modelo','Choose your model')}</span></div>`);
    $('#assistant-body').insertAdjacentHTML('beforeend',`<small class="melody-disclaimer">${this.t('Melody puede cometer errores. Verifica sus respuestas.','Melody can make mistakes. Check its responses.')}</small>`);
    this.lantern=new LanternView(this);this.lantern.init();
    $('.avatar').dataset.action='profile';this.updateProfile();
    $('.debug-button').dataset.action='debug-view';$('.debug-button').innerHTML=icon('cube')+this.t('Depurar','Debug');
    $('.run-button').title=this.t('Ejecutar archivo activo (F5)','Run active file (F5)');
    const identity=$('.assistant-heading-title');identity.querySelector('h2').hidden=true;
    identity.insertAdjacentHTML('beforeend','<select id="assistant-identity" aria-label="Asistente"><option value="melody">Melody</option><option value="emma">Emma</option></select>');
    $('#assistant-identity').onchange=e=>this.safe(()=>this.host.platform.switchIdentity(e.target.value));this.host.platform.updateIdentity();
    actions.insertAdjacentHTML('afterend',`<button class="assistant-lantern text-button" data-lantern="analyze">${icon('sparkles')}Analizar sesión Lantern</button>`);
    this.hydrate(document);
  }
  updateProfile(){
    const initial=esc((this.profile.displayName||'L').slice(0,1).toUpperCase());
    const avatar=$('.avatar'),markup=this.profile.avatar?`<img src="${esc(this.profile.avatar)}" alt="${esc(this.profile.displayName)}">`:initial;if(avatar&&avatar.innerHTML!==markup)avatar.innerHTML=markup;const welcomeAvatar=$('.welcome-profile-avatar');if(welcomeAvatar&&welcomeAvatar.innerHTML!==markup)welcomeAvatar.innerHTML=markup;
    const name=$('#home-name');if(name&&name.textContent!==this.profile.displayName)name.textContent=this.profile.displayName;
    const photo=$('.profile-photo>button');if(photo){const picture=this.profile.avatar?`<img src="${esc(this.profile.avatar)}" alt="">`:`<span class="profile-initial">${initial}</span>`,html=picture+`<span class="photo-badge">${icon('camera')}</span>`;if(photo.innerHTML!==html)photo.innerHTML=html;}
  }
  async hydrate(root){
    for(const [canvas,scene] of this.scenes)if(!canvas.isConnected){scene.dispose();this.scenes.delete(canvas);}
    for(const canvas of root.querySelectorAll('canvas[data-glass]')){
      if(canvas.dataset.initialized)continue;canvas.dataset.initialized='true';
      const scene=await createLumenScene(canvas,this.host.service().babylon);
      if(this.disposed||!canvas.isConnected)scene.dispose();else this.scenes.set(canvas,scene);
    }
  }
  enter(){
    $('#lumen-home')?.setAttribute('hidden','');$('#workspace').inert=false;$('.statusbar').hidden=false;
    document.documentElement.dataset.screen='studio';
  }
  home(){this.host.platform.closePage();this.renderHome();}
  renderHome(){
    let home=$('#lumen-home');if(!home){home=document.createElement('section');home.id='lumen-home';home.setAttribute('aria-label','Inicio de Zénit');$('#app').append(home);}
    home.hidden=false;$('#workspace').inert=true;$('.statusbar').hidden=true;document.documentElement.dataset.screen='home';
    if(home.dataset.built==='true'){this.refreshHome();return;}
    home.innerHTML=`<section class="welcome-sheet"><div class="welcome-depth" aria-hidden="true"><div class="welcome-landscape"></div></div><header class="welcome-wordmark"><span class="welcome-z">Z</span><span>ZÉNIT</span></header><button class="welcome-profile" data-studio="activity" aria-label="${this.t('Perfil y archivos recientes','Profile and recent files')}"><span class="welcome-profile-avatar"></span><span>${this.t('Mi actividad','My activity')}</span></button><div class="welcome-scene">${glassArt('welcome')}</div><div class="welcome-copy"><h1>${this.t('Un lugar para lo que viene.','A place for what comes next.')}</h1><p>${this.t('Crea. Explora. Construye. Sin límites.','Create. Explore. Build. Without limits.')}</p><div class="welcome-actions"><button class="primary-button home-enter" data-action="open-workspace">${this.t('Abrir proyecto','Open project')}</button><button class="welcome-new" data-action="new-project"><span>${this.t('Nuevo proyecto','New project')}</span>${icon('arrow-right')}</button></div></div><footer class="welcome-footer"><span>“ &nbsp; ${this.t('Ideas en movimiento.','Ideas in motion.')}</span><span>— Zénit</span></footer></section>`;
    home.dataset.built='true';this.homePointer=e=>{if(!this.host.motion.enabled||document.hidden||matchMedia('(prefers-reduced-motion: reduce)').matches)return;this.pointerTarget=[Math.round((e.clientX/innerWidth-.5)*8),Math.round((e.clientY/innerHeight-.5)*6)];if(this.pointerFrame)return;this.pointerFrame=requestAnimationFrame(()=>{this.pointerFrame=0;home.style.setProperty('--welcome-x',this.pointerTarget[0]+'px');home.style.setProperty('--welcome-y',this.pointerTarget[1]+'px');});};home.onpointermove=this.homePointer;home.onpointerleave=()=>{cancelAnimationFrame(this.pointerFrame);this.pointerFrame=0;home.style.removeProperty('--welcome-x');home.style.removeProperty('--welcome-y');};home.onclick=e=>{const b=e.target.closest('[data-studio]');if(b)this.safe(()=>this.action(b.dataset.studio));};this.hydrate(home);this.homeLocale=this.host.platform.prefs['general.locale'];this.updateProfile();
  }
  refreshHome(){
    this.updateProfile();const locale=this.host.platform.prefs['general.locale'];if(this.homeLocale===locale)return;this.homeLocale=locale;
    const set=(selector,text)=>{const node=document.querySelector(selector);if(node&&node.textContent!==text)node.textContent=text;};
    set('.welcome-copy h1',this.t('Un lugar para lo que viene.','A place for what comes next.'));
    set('.welcome-copy p',this.t('Crea. Explora. Construye. Sin límites.','Create. Explore. Build. Without limits.'));
    set('.home-enter',this.t('Abrir proyecto','Open project'));set('.welcome-new span',this.t('Nuevo proyecto','New project'));
    set('.welcome-profile>span:last-child',this.t('Mi actividad','My activity'));$('.welcome-profile')?.setAttribute('aria-label',this.t('Perfil y archivos recientes','Profile and recent files'));
    set('.welcome-footer span',this.t('“  Ideas en movimiento.','“  Ideas in motion.'));
    // The canvas stays mounted; its visibility observer handles pause/resume.
  }
  action(action){if(action==='activity')return this.showActivity();if(action==='recent')return this.showRecent();if(action==='enter')return this.enter();if(action==='profile')return this.editProfile();if(action==='onboard'){if(window.pywebview?.api?.lock_session)return window.pywebview.api.lock_session();return this.onboarding();}if(action==='files'){this.host.palette();}}
  showActivity(){
    const recent=[...this.profile.recent].sort((a,b)=>new Date(b.openedAt)-new Date(a.openedAt)).slice(0,20),initial=esc((this.profile.displayName||'Z').slice(0,1).toUpperCase());
    this.host.modal(this.t('Mi actividad','My activity'),`<section class="profile-activity"><div class="profile-activity-identity"><span class="activity-avatar">${this.profile.avatar?`<img src="${esc(this.profile.avatar)}" alt="">`:initial}</span><div><strong>${esc(this.profile.displayName)}</strong><small>${this.t('Perfil local · Zénit','Local profile · Zénit')}</small></div></div><button class="secondary-button" id="activity-edit-profile">${icon('sliders')}${this.t('Editar perfil','Edit profile')}</button><h3>${this.t('Archivos abiertos recientemente','Recently opened files')}</h3><div class="profile-activity-list">${recent.length?recent.map((r,i)=>`<button class="profile-activity-file" data-activity-file="${i}">${fileIcon(r.path)}<span><strong>${esc(r.path.split(/[\\/]/).pop())}</strong><small>${esc(r.workspace)} · ${esc(r.path)}</small></span><time datetime="${esc(r.openedAt)}">${esc(new Date(r.openedAt).toLocaleString(this.host.platform.prefs['general.locale'],{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}))}</time>${icon('arrow-right')}</button>`).join(''):`<p>${this.t('Todavía no has abierto ningún archivo.','You have not opened any files yet.')}</p>`}</div></section>`);
    $('#activity-edit-profile').onclick=()=>{this.host.closeModal();this.editProfile();};
    document.querySelectorAll('[data-activity-file]').forEach(b=>b.onclick=()=>this.safe(async()=>{const item=recent[Number(b.dataset.activityFile)];this.host.closeModal();if(item.workspace!==this.host.service().workspace&&!await this.host.changeWorkspace(item.workspace))return;await this.host.openFile(item.path);}));
  }
  showRecent(){
    const recent=this.profile.recent.filter(x=>x.workspace===this.host.service().workspace);
    this.host.modal(this.t('Lo último que abriste','Recently opened'),`<div class="recent-browser">${recent.length?recent.map((r,i)=>`<button class="recent-file" data-recent-index="${i}">${fileIcon(r.path)}<strong>${esc(r.path.split('/').pop())}</strong><small>${esc(r.path)}</small></button>`).join(''):`<p>${this.t('Todavía no has abierto ningún archivo.','You have not opened any files yet.')}</p>`}</div>`);
    document.querySelectorAll('[data-recent-index]').forEach(b=>b.onclick=()=>this.safe(async()=>{const item=recent[Number(b.dataset.recentIndex)];this.host.closeModal();await this.host.openFile(item.path);}));
  }
  remember(path){
    if(!this.profile.recent)return;
    const workspace=this.host.service().workspace;
    const recent=[{path,workspace,openedAt:new Date().toISOString()},...this.profile.recent.filter(x=>x.path!==path||x.workspace!==workspace)].slice(0,30);
    this.safe(()=>this.save({recent}));
  }
  editProfile(){
    this.host.modal(this.t('Tu perfil','Your profile'),`<form id="profile-form" class="profile-form"><div class="profile-preview"><canvas id="profile-crop" width="512" height="512" aria-label="Vista previa del perfil"></canvas></div><div class="profile-crop-controls"><label for="profile-zoom">${this.t('Encuadre · arrastra la imagen para centrarla','Crop · drag the image to position it')}</label><input type="range" id="profile-zoom" min="1" max="3" step=".01" value="1" aria-label="Zoom de la imagen"></div><label>${this.t('Cómo te llamas','Your name')}<input id="profile-name" maxlength="40" required value="${esc(this.profile.displayName)}"></label><label class="avatar-upload">${icon('upload')}${this.t('Elegir una imagen','Choose a picture')}<input id="profile-picture" type="file" accept="image/png,image/jpeg,image/webp"></label><p class="profile-file-state">PNG, JPEG o WebP · ${this.t('se guarda en este equipo','stored on this device')}</p><button type="button" class="text-button" id="profile-workspace">${this.t('Diseñar mi espacio de trabajo','Design my workspace')} →</button><div class="modal-actions"><button type="button" class="secondary-button" id="remove-avatar">${this.t('Quitar imagen','Remove image')}</button><button class="primary-button">${this.t('Guardar perfil','Save profile')}</button></div></form>`);
    const canvas=$('#profile-crop'),form=$('#profile-form'),ctx=canvas.getContext('2d'),zoom=$('#profile-zoom');let bitmap=null,scale=1,centerX=.5,centerY=.5,sequence=0,drag=null,avatar=this.profile.avatar;
    const draw=()=>{ctx.clearRect(0,0,512,512);if(bitmap){const side=Math.min(bitmap.width,bitmap.height)/scale;centerX=Math.max(side/2/bitmap.width,Math.min(1-side/2/bitmap.width,centerX));centerY=Math.max(side/2/bitmap.height,Math.min(1-side/2/bitmap.height,centerY));ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(bitmap,centerX*bitmap.width-side/2,centerY*bitmap.height-side/2,side,side,0,0,512,512);}else{ctx.fillStyle='#bca9ef';ctx.fillRect(0,0,512,512);ctx.font='220px Segoe UI';ctx.fillStyle='#fff';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(($('#profile-name')?.value||'L').slice(0,1).toUpperCase(),256,276);}zoom.disabled=!bitmap;};
    const load=async(blob)=>{const id=++sequence;const next=await createImageBitmap(blob);if(id!==sequence||!canvas.isConnected){next.close();return;}bitmap?.close();bitmap=next;scale=1;centerX=centerY=.5;zoom.value='1';draw();};
    draw();if(avatar)this.safe(async()=>{const image=new Image();image.src=avatar;await image.decode();await load(image);});
    $('#profile-name').addEventListener('input',()=>{if(!bitmap){this.profilePreviewName=$('#profile-name').value;draw();}});
    const cleanup=new MutationObserver(()=>{if(!canvas.isConnected){sequence++;bitmap?.close();bitmap=null;cleanup.disconnect();}});cleanup.observe(form.parentElement,{childList:true,subtree:true});
    zoom.oninput=()=>{scale=Number(zoom.value);draw();};
    canvas.onpointerdown=e=>{if(!bitmap)return;canvas.setPointerCapture(e.pointerId);drag={x:e.clientX,y:e.clientY,cx:centerX,cy:centerY};};
    canvas.onpointermove=e=>{if(!drag||!bitmap)return;const side=Math.min(bitmap.width,bitmap.height)/scale,r=canvas.getBoundingClientRect();centerX=drag.cx-(e.clientX-drag.x)/r.width*side/bitmap.width;centerY=drag.cy-(e.clientY-drag.y)/r.height*side/bitmap.height;draw();};canvas.onpointerup=canvas.onpointercancel=()=>{drag=null;};
    $('#profile-workspace').onclick=()=>{this.host.closeModal();this.onboarding();};
    $('#remove-avatar').onclick=()=>{sequence++;bitmap?.close();bitmap=null;avatar='';draw();$('.profile-file-state').textContent=this.t('Imagen eliminada al guardar.','Picture will be removed on save.');};
    $('#profile-picture').onchange=()=>this.safe(async()=>{const file=$('#profile-picture').files[0];if(!file)return;if(file.size>10_000_000)throw new Error('La imagen no puede superar 10 MB.');if(!['image/png','image/jpeg','image/webp'].includes(file.type))throw new Error('Elige una imagen PNG, JPEG o WebP.');await load(file);if(canvas.isConnected)$('.profile-file-state').textContent=file.name;});
    form.onsubmit=e=>{e.preventDefault();this.safe(async()=>{if(bitmap)avatar=canvas.toDataURL('image/webp',.94);await this.save({displayName:$('#profile-name').value,avatar});this.updateProfile();this.host.closeModal();if(document.documentElement.dataset.screen==='home')this.renderHome();});};
  }
  onboarding(step=0){
    let shell=$('#onboarding');if(!shell){shell=document.createElement('section');shell.id='onboarding';shell.className='onboarding';shell.setAttribute('role','dialog');shell.setAttribute('aria-modal','true');shell.setAttribute('aria-labelledby','onboarding-title');document.body.append(shell);this.onboardDraft={locale:this.host.platform.prefs['general.locale'],theme:this.host.platform.prefs['appearance.theme'],layout:'studio',position:'right',style:this.profile.workspaceStyle,name:this.profile.displayName};}
    $('#app').inert=true;const draft=this.onboardDraft;
    const choices=(key,items)=>`<div class="setup-choices">${items.map(([value,label,glyph])=>`<button type="button" data-choice="${key}" data-value="${value}" class="${draft[key]===value?'selected':''}" aria-pressed="${draft[key]===value}">${key==='theme'?`<span class="space-preview ${value}"><i></i><i></i><i></i></span>`:icon(glyph||'layout')}<span>${label}</span></button>`).join('')}</div>`;
    shell.innerHTML=`<header class="setup-brand">${$('.brand').innerHTML}<span>Primer inicio</span><button class="text-button" id="skip-onboarding">${this.t('Omitir configuración','Skip setup')} ${icon('arrow-right')}</button></header><div class="setup-shell"><aside class="setup-sidebar"><nav>${['Tu espacio','Personalización','Listo'].map((s,i)=>`<div class="setup-step ${i===step?'active':''}"><span>${i<step?'✓':i+1}</span>${s}</div>`).join('')}</nav>${glassArt('orb')}<div class="setup-motto"><strong>ZÉNIT<br>IDE</strong><p>Crea hoy,<br>un mejor mañana.</p><div class="step-dots">${[0,1,2].map(i=>`<i class="${i===step?'active':''}"></i>`).join('')}</div></div></aside><div class="setup-main"><div class="setup-heading"><span class="eyebrow">PASO ${step+1} DE 3</span><h1 id="onboarding-title">${['Diseña tu espacio de trabajo','Haz que se sienta tuyo','Todo listo para crear.'][step]}</h1><p>${['Elige cómo quieres que se vea y se sienta Zénit.<br>Puedes cambiarlo en cualquier momento.','Un espacio tranquilo para concentrarte en lo que importa.','Tu espacio, tus ideas. El siguiente paso es tuyo.'][step]}</p></div><div class="setup-content">${step===0?`<div class="setup-grid"><article class="setup-card"><h3>${icon('globe')}Idioma de la interfaz</h3><p>Selecciona el idioma de la aplicación.</p><select id="onboard-locale"><option value="es" ${draft.locale==='es'?'selected':''}>Español</option><option value="en" ${draft.locale==='en'?'selected':''}>English</option></select></article><article class="setup-card"><h3>${icon('sun')}Tema visual</h3><p>Elige el aspecto que prefieras.</p>${choices('theme',[['day','Claro'],['dark','Oscuro'],['forest','Bosque']])}</article><article class="setup-card"><h3>${icon('layout')}Diseño de paneles</h3><p>Selecciona la distribución inicial.</p>${choices('layout',[['studio','Predeterminado','layout'],['code','Compacto','dock-left'],['focus','Minimalista','focus']])}</article><article class="setup-card"><h3>${icon('sparkles')}Posición de Melody</h3><p>Tu asistente, donde tú prefieras.</p>${choices('position',[['right','Lateral derecha','dock-right'],['left','Lateral izquierda','dock-left'],['bottom','Panel inferior','dock-bottom']])}</article><article class="setup-card setup-wide"><h3>${icon('code')}Estilo de espacio de trabajo</h3><p>Elige un punto de partida para tu entorno.</p>${choices('style',[['general','Desarrollo general','code'],['web','Desarrollo web','globe'],['data','Ciencia de datos','cpu'],['design','Diseño y UI','palette']])}</article></div>`:step===1?`<article class="setup-card setup-personal"><h3>${icon('palette')}Tu firma en Zénit</h3><label>Nombre del perfil<input id="onboard-name" maxlength="40" value="${esc(draft.name)}"></label><div class="preference-row"><label>Animaciones suaves<small>Cristales y colores en movimiento.</small></label><label class="platform-switch"><input type="checkbox" id="onboard-motion" ${this.host.platform.prefs['appearance.motion']?'checked':''}><span></span></label></div><div class="preference-row"><label>Guardar automáticamente<small>Con control de conflictos y copia previa.</small></label><label class="platform-switch"><input type="checkbox" id="onboard-autosave" ${this.host.platform.prefs['files.autoSave']?'checked':''}><span></span></label></div><p>Tu perfil y tus preferencias se guardan en este equipo.</p></article>`:`<div class="setup-ready">${glassArt('orb')}<h2>Hola, ${esc(draft.name)}.</h2><p>Bienvenido a Zénit 0.5.3.<br>Un lugar para lo que viene.</p><span class="ready-badge">${icon('check')}Tu espacio está preparado</span></div>`}</div><footer class="setup-footer"><button class="secondary-button" id="onboard-back" ${step===0?'disabled':''}>${icon('chevron-left')} Atrás</button><button class="primary-button" id="onboard-next">${step===2?'Empezar a crear':'Continuar'} ${icon('arrow-right')}</button></footer></div></div>`;
    shell.querySelectorAll('[data-choice]').forEach(b=>b.onclick=()=>{draft[b.dataset.choice]=b.dataset.value;if(b.dataset.choice==='theme')document.documentElement.dataset.theme=b.dataset.value;this.onboarding(step);});
    $('#onboard-locale')?.addEventListener('change',e=>draft.locale=e.target.value);
    $('#onboard-back').onclick=()=>this.onboarding(step-1);
    $('#skip-onboarding').onclick=()=>this.safe(()=>this.finishOnboarding(true));
    $('#onboard-next').onclick=()=>this.safe(async()=>{if(step===1){draft.name=$('#onboard-name').value.trim();if(!draft.name){$('#onboard-name').focus();return;}draft.motion=$('#onboard-motion').checked;draft.autosave=$('#onboard-autosave').checked;}if(step===2)await this.finishOnboarding();else this.onboarding(step+1);});
    shell.onkeydown=e=>{if(e.key==='Tab'){const list=[...shell.querySelectorAll('button:not(:disabled),input,select')];if(e.shiftKey&&document.activeElement===list[0]){e.preventDefault();list.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===list.at(-1)){e.preventDefault();list[0].focus();}}};
    this.hydrate(shell);$('#onboard-next').focus({preventScroll:true});
  }
  async finishOnboarding(skip=false){
    const d=this.onboardDraft;if(!skip){const p=this.host.platform;const settings={'general.locale':d.locale,'appearance.theme':d.theme,'appearance.motion':d.motion??true,'files.autoSave':d.autosave??false,'editor.wordWrap':d.style==='web'||d.style==='design','editor.fontSize':d.style==='design'?15:14};await this.host.api('/platform/settings',{settings});Object.assign(p.prefs,settings);p.applyPreferences();this.host.dock.preset(d.layout);if(d.layout==='studio')this.host.dock.move('assistant',d.position);await this.save({displayName:d.name,workspaceStyle:d.style,layout:this.host.dock.snapshot(),onboarded:true});}else{this.host.platform.applyPreferences();await this.save({onboarded:true});}
    $('#onboarding').remove();$('#app').inert=false;this.workspaces?.apply();this.renderHome();$('.home-enter').focus();
  }
  search(folder=""){
    this.enter();const p=this.host.platform;
    const empty=()=>`<div class="search-empty"><span class="search-visual">${icon('folder')}${icon('search')}</span><h3>${this.t('Cada idea tiene un comienzo.','Every idea has a beginning.')}</h3><p>${this.t('Escribe una palabra, un símbolo o el nombre de un archivo.','Type a word, symbol or filename.')}</p></div>`;
    const folders=[...new Set(this.host.files().flatMap(path=>{const parts=path.split('/');return parts.slice(0,-1).map((_,i)=>parts.slice(0,i+1).join('/'));}))].sort();
    p.openPage('search',`<div class="search-page"><div class="search-intro"><h2>${this.t('Encuentra el <em>siguiente paso.</em>','Find your <em>next step.</em>')}</h2><p>${this.t('Busca en tu código y archivos para avanzar más rápido.','Search your code and files to move forward faster.')}</p></div><form id="studio-search-form" class="studio-search-field">${icon('search')}<input id="studio-search" placeholder="${this.t('Buscar en el proyecto...','Search project...')}" autocomplete="off" aria-label="${this.t('Buscar en el proyecto','Search project')}"><kbd>Ctrl K</kbd><button class="primary-button" aria-label="Buscar">${icon('arrow-right')}</button></form><div class="search-filters"><button data-search-mode="content" class="active" aria-pressed="true">${this.t('Contenido','Content')} ${icon('chevron-down')}</button><button data-search-mode="files" aria-pressed="false">${this.t('Archivos','Files')} ${icon('chevron-down')}</button><select id="search-type" aria-label="${this.t('Tipo de archivo','File type')}"><option value="">${this.t('Tipo','Type')}</option><option value="code">${this.t('Código','Code')}</option><option value="document">${this.t('Documentos','Documents')}</option></select><select id="search-folder" aria-label="${this.t('Carpeta','Folder')}"><option value="">${this.t('Carpeta','Folder')}</option>${folders.map(path=>`<option value="${esc(path)}" ${path===folder?'selected':''}>${esc(path)}</option>`).join('')}</select><input id="search-extension" aria-label="Filtrar extensión" placeholder="*.cs, *.py..."></div><div class="search-result-heading" hidden><span id="search-result-count" role="status"></span><span>${esc(this.host.service().name)}</span></div><div id="studio-search-results" class="studio-search-results">${empty()}</div></div>`);
    let mode='content',timer;
    const search=async()=>{
      const seq=++this.searchSequence,q=$('#studio-search')?.value.trim()||'',filter=($('#search-extension')?.value||'').replaceAll('*','').trim().toLowerCase();
      if(!q){$('#studio-search-results').innerHTML=empty();p.workbench.querySelector('.search-result-heading').hidden=true;return;}
      p.workbench.querySelector('.search-result-heading').hidden=false;$('#search-result-count').textContent=this.t('Buscando…','Searching…');
      const selectedFolder=$('#search-folder').value,type=$('#search-type').value;
      const data=await this.host.api('/search?q='+encodeURIComponent(q)+'&folder='+encodeURIComponent(selectedFolder)+(mode==='content'?'&content=1':''));
      if(seq!==this.searchSequence||p.page!=='search')return;
      const code=/\.(py|pyw|js|mjs|cjs|ts|tsx|jsx|c|cpp|h|hpp|java|cs|go|rs|kt|nc|n|asm|s|sh|bash|html|css|sql)$/i;
      const results=data.results.filter(r=>(!filter||filter.split(',').some(f=>r.path.toLowerCase().endsWith(f.trim())))&&(!type||(type==='code'?code.test(r.path):!code.test(r.path))));
      results.sort((a,b)=>Number(b.path.split('/').pop().toLowerCase().includes(q.toLowerCase()))-Number(a.path.split('/').pop().toLowerCase().includes(q.toLowerCase()))||a.path.localeCompare(b.path)||(a.line||0)-(b.line||0));
      $('#search-result-count').textContent=results.length+' '+this.t('resultados','results');const groups=new Map();for(const r of results){if(!groups.has(r.path))groups.set(r.path,[]);groups.get(r.path).push(r);}
      $('#studio-search-results').innerHTML=[...groups].map(([path,hits])=>`<button class="search-hit" data-file="${esc(path)}" data-line="${hits[0].line||1}"><header>${fileIcon(path)}<span><strong>${esc(path.split('/').pop())}</strong><small>${esc(path)}</small></span>${icon('arrow-up-right')}</header>${hits.slice(0,4).map(h=>h.text!==undefined?`<div class="search-code"><span>${h.line}</span><code>${esc(h.text)}</code></div>`:'').join('')}</button>`).join('')||`<div class="search-empty">${icon('search')}<h3>${this.t('Sin coincidencias','No matches')}</h3><p>${this.t('Prueba con otra palabra o cambia el filtro.','Try another word or change the filter.')}</p></div>`;
    };
    const delayed=()=>{++this.searchSequence;clearTimeout(timer);timer=setTimeout(()=>this.safe(search),180);};
    $('#studio-search').oninput=delayed;$('#search-extension').oninput=delayed;$('#search-type').onchange=()=>this.safe(search);$('#search-folder').onchange=()=>this.safe(search);$('#studio-search-form').onsubmit=e=>{e.preventDefault();clearTimeout(timer);this.safe(search);};
    p.workbench.querySelectorAll('[data-search-mode]').forEach(b=>b.onclick=()=>{mode=b.dataset.searchMode;p.workbench.querySelectorAll('[data-search-mode]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});this.safe(search);});$('#studio-search').focus();
  }
  async debug(){this.debugWorkspace ||= new DebugWorkspace(this);return this.debugWorkspace.open();}
  async configureLanguages(){
    const data=await this.host.api('/platform/languages');
    this.host.modal('Lenguajes y depuradores',`<p>Rutas y argumentos de tu equipo. Los comandos se ejecutan solo al iniciar una tarea en un proyecto de confianza.</p><div class="language-status">${data.languages.map(l=>`<span><strong>${esc(l.name)}</strong><small>${l.available?'Herramienta detectada':'Necesita SDK/configuración'} · ${esc(l.debugger)}</small></span>`).join('')}</div><form id="languages-form"><label class="field-label" for="languages-json">languages.json</label><textarea id="languages-json" class="configuration-json" spellcheck="false">${esc(JSON.stringify(data.config,null,2))}</textarea><p class="form-hint">Variables: <code>\${file}</code>, <code>\${workspaceFolder}</code>, <code>\${target}</code>, <code>\${port}</code>. Consulta docs/LENGUAJES.md para los perfiles DAP.</p><div class="modal-actions"><button type="button" class="secondary-button" id="language-dap-template">Ejemplo DAP</button><button class="primary-button">Validar y guardar</button></div></form>`,{wide:true});
    $('#language-dap-template').onclick=()=>{const data=JSON.parse($('#languages-json').value);data.languages??={};data.languages.cpp={debug:{adapter:['lldb-dap'],launch:{program:'${target}',cwd:'${workspaceFolder}',stopOnEntry:true,console:'internalConsole'}}};$('#languages-json').value=JSON.stringify(data,null,2);};
    $('#languages-form').onsubmit=e=>{e.preventDefault();this.safe(async()=>{await this.host.api('/platform/languages/config',JSON.parse($('#languages-json').value));this.host.closeModal();this.host.notify('Configuración de lenguajes guardada.');});};
  }
  async pollDebug(){return this.debugWorkspace?.poll();}
  installMotion(){
    this.wheel=e=>{if(!this.host.motion.enabled||Math.abs(e.deltaY)<1||performance.now()-this.lastBounce<420)return;let el=e.target instanceof Element?e.target:null;while(el&&el!==document.body){const style=getComputedStyle(el);if(/auto|scroll/.test(style.overflowY)&&el.scrollHeight>el.clientHeight+2){const edge=e.deltaY<0&&el.scrollTop<=0||e.deltaY>0&&el.scrollTop+el.clientHeight>=el.scrollHeight-1;if(edge&&!el.closest('.monaco-editor,.xterm')){this.lastBounce=performance.now();this.host.motion.play(el,[{translate:'0 0'},{translate:'0 '+(e.deltaY<0?7:-7)+'px'},{translate:'0 0'}],380);}return;}el=el.parentElement;}};
    document.addEventListener('wheel',this.wheel,{passive:true});
  }
  dispose(){this.debugWorkspace?.dispose();cancelAnimationFrame(this.pointerFrame);this.lantern?.dispose();this.disposed=true;clearTimeout(this.layoutTimer);clearTimeout(this.debugTimer);document.removeEventListener('wheel',this.wheel);document.removeEventListener('visibilitychange',this.visibility);for(const scene of this.scenes.values())scene.dispose();this.scenes.clear();}
}
