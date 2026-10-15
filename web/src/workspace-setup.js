import {icon,escapeHTML as esc} from './icons.js';
import {glassArt} from './glass.js';
import {applyShellTheme} from './extension-theme.js';

/** First-run setup owns its screen; drafts survive navigation until completion. */
export class WorkspaceSetup {
  constructor(studio){
    this.studio=studio;this.host=studio.host;const p=this.host.platform.prefs;
    this.draft=studio.onboardDraft={locale:p['general.locale'],theme:p['appearance.theme'],layout:'studio',position:'right',style:studio.profile.workspaceStyle||'general',name:studio.profile.displayName||'',motion:p['appearance.motion'],autosave:p['files.autoSave']};
  }
  t(es,en){return this.draft.locale==='es'?es:en;}
  open(){
    const mount=()=>{
      document.getElementById('app').inert=true;
      document.getElementById('lumen-home').hidden=true;
      document.documentElement.dataset.screen='setup';
      this.root=document.createElement('section');this.root.id='onboarding';this.root.className='onboarding';
      this.root.setAttribute('role','dialog');this.root.setAttribute('aria-modal','true');this.root.setAttribute('aria-labelledby','onboarding-title');
      document.body.append(this.root);this.render(0,false);
    };
    if(this.studio.profile.onboarded)return this.host.motion.swapScreen(mount,document.querySelector('.avatar'),{direction:'setup',target:'setup'});
    mount();return Promise.resolve();
  }
  capture(){const root=this.root,d=this.draft;if(root.querySelector('#onboard-name')){d.name=root.querySelector('#onboard-name').value;d.motion=root.querySelector('#onboard-motion').checked;d.autosave=root.querySelector('#onboard-autosave').checked;}}
  preview(personal=false){
    const d=this.draft,t=this.t.bind(this),name=d.name.trim()||t('Tu espacio','Your workspace');
    const labels={studio:t('Equilibrada','Balanced'),code:t('Compacta','Compact'),focus:t('Concentración','Focus'),day:t('Día','Day'),dark:t('Oscuro','Dark'),forest:t('Bosque','Forest')};
    return `<aside class="setup-preview ${personal?'is-personal':''}" aria-label="${t('Vista previa de tu espacio','Your workspace preview')}">
      <div class="setup-preview-caption"><span>${icon('layout')}${t('TU ESPACIO','YOUR WORKSPACE')}</span><span class="setup-preview-live"><i></i>${t('Vista previa','Preview')}</span></div>
      ${personal?`<div class="setup-profile-preview"><span class="setup-profile-avatar">${esc([...name][0].toLocaleUpperCase())}</span><h2>${esc(name)}</h2><p>${t('Todo empieza con una idea.','Everything starts with an idea.')}</p></div>`:''}
      <div class="setup-mini" data-layout="${d.layout}" data-position="${d.position}" aria-hidden="true">
        <div class="setup-mini-top"><b>Z</b><span>${esc(personal?name:'Aurora')}</span><i></i>${icon('search')}<span class="setup-mini-avatar">${esc([...name][0].toLocaleUpperCase())}</span></div>
        <div class="setup-mini-body"><div class="setup-mini-rail">${icon('folder')}${icon('search')}${icon('git')}${icon('extensions')}</div>
        <div class="setup-mini-project"><strong>${t('Proyecto','Project')}</strong><span>${icon('chevron-down')}${icon('folder')} Aurora</span><span class="mini-file active">${icon('code')} main.py</span><span class="mini-file">${icon('file')} README.md</span></div>
        <div class="setup-mini-editor"><div class="setup-mini-tab">${icon('code')} main.py <i></i><span>×</span></div><pre><span class="mini-number">1</span> <b>def</b> greet(name):
<span class="mini-number">2</span>     <b>return</b> <em>f"Hello, {name}!"</em>
<span class="mini-number">3</span>
<span class="mini-number">4</span> print(greet(<em>"Aurora"</em>))
<span class="mini-number">5</span> <span class="mini-caret"></span></pre><div class="setup-mini-terminal"><span>${icon('terminal')} Terminal</span><code>› Hello, Aurora!</code></div></div>
        <div class="setup-mini-melody"><strong>${icon('sparkles')} Melody</strong>${glassArt('welcome')}<span>${t('Una idea. Un comienzo.','One idea. One beginning.')}</span><div>${t('Pregunta a Melody…','Ask Melody…')}${icon('arrow-right')}</div></div></div>
        <div class="setup-mini-status"><span>${icon('git')} main</span><span>Python · UTF-8</span></div>
      </div>
      <div class="setup-preview-detail"><span>${icon('check')}${labels[d.layout]}</span><span>${labels[d.theme]}</span></div>
      <div class="setup-preview-copy"><h3>${personal?t('A tu ritmo.','At your pace.'):t('Menos ruido. Más espacio.','Less noise. More room.')}</h3><p>${personal?t('Tu nombre, tu forma de trabajar. Podrás ajustar cada detalle más adelante.','Your name, your way of working. You can adjust every detail later.'):t('Prueba una distribución y mira cómo encaja. Melody estará donde tú prefieras.','Try a layout and see how it fits. Melody stays where you prefer.')}</p></div>
    </aside>`;
  }
  refreshPreview(){
    const preview=this.root.querySelector('.setup-preview');if(!preview)return;
    const d=this.draft,t=this.t.bind(this),name=d.name.trim()||t('Tu espacio','Your workspace'),mini=preview.querySelector('.setup-mini');
    mini.dataset.layout=d.layout;mini.dataset.position=d.position;
    preview.querySelectorAll('.setup-profile-avatar,.setup-mini-avatar').forEach(e=>e.textContent=[...name][0].toLocaleUpperCase());
    if(this.step===1){preview.querySelector('.setup-profile-preview h2').textContent=name;preview.querySelector('.setup-mini-top>span').textContent=name;}
    const labels={studio:t('Equilibrada','Balanced'),code:t('Compacta','Compact'),focus:t('Concentración','Focus'),day:t('Día','Day'),dark:t('Oscuro','Dark'),forest:t('Bosque','Forest')};
    preview.querySelector('.setup-preview-detail').innerHTML=`<span>${icon('check')}${labels[d.layout]}</span><span>${labels[d.theme]}</span>`;
  }
  choices(key,items){return `<div class="setup-choices">${items.map(([value,label,glyph])=>`<button type="button" data-choice="${key}" data-value="${value}" class="${this.draft[key]===value?'selected':''}" aria-pressed="${this.draft[key]===value}">${key==='theme'?`<span class="space-preview ${value}" aria-hidden="true"><i></i><i></i><i></i></span>`:icon(glyph||'layout')}<span>${label}</span></button>`).join('')}</div>`;}
  render(step,animate=true){
    this.capture();this.step=step;const d=this.draft,t=this.t.bind(this),root=this.root;
    const steps=[t('Tu espacio','Your workspace'),t('Personalización','Personalize'),t('Listo','Ready')];
    root.innerHTML=`<header class="setup-brand"><span class="setup-logo">Z</span><strong>ZÉNIT <span>IDE</span></strong><span class="setup-edition">${this.host.platform.state.version}</span><button class="text-button" id="skip-onboarding">${t('Omitir configuración','Skip setup')}${icon('arrow-right')}</button></header>
      <div class="setup-shell"><aside class="setup-sidebar"><span class="setup-nav-label">${t('BIENVENIDO A ZÉNIT','WELCOME TO ZÉNIT')}</span><nav aria-label="${t('Configuración inicial','Workspace setup')}">${steps.map((s,i)=>`<div class="setup-step ${i===step?'active':''} ${i<step?'complete':''}" ${i===step?'aria-current="step"':''}><span>${i<step?icon('check'):i+1}</span><div><strong>${s}</strong><small>${[t('Elige cómo trabajar','Choose how you work'),t('Dale tu toque','Make it yours'),t('Empieza a crear','Start creating')][i]}</small></div></div>`).join('')}</nav><div class="setup-signature">${glassArt('welcome')}<p>${t('Un espacio para<br>tus próximas ideas.','A space for<br>your next ideas.')}</p></div></aside>
      <div class="setup-main"><div class="setup-heading"><span class="eyebrow">${t('PASO','STEP')} ${step+1} / 3</span><h1 id="onboarding-title" tabindex="-1">${[t('Diseña tu espacio de trabajo','Design your workspace'),t('Haz que se sienta tuyo','Make yourself at home'),t('Todo listo para crear','Ready for your next idea')][step]}</h1><p>${[t('Elige un punto de partida. Podrás cambiarlo desde Ajustes.','Choose a starting point. You can change everything in Settings.'),t('Los detalles que hacen que trabajar sea más cómodo.','A few details to make your work feel more comfortable.'),t('Tu espacio está preparado. El siguiente paso es tuyo.','Your workspace is ready. The next step is yours.')][step]}</p></div>
      <div class="setup-content">${step===0?`<div class="setup-compose"><div class="setup-grid">
      <article class="setup-card"><h3>${icon('globe')}${t('Idioma','Language')}</h3><p>${t('El idioma de la interfaz.','The language of your interface.')}</p><label class="setup-language" for="onboard-locale"><select id="onboard-locale"><option value="es" ${d.locale==='es'?'selected':''}>Español</option><option value="en" ${d.locale==='en'?'selected':''}>English</option></select></label></article>
      <article class="setup-card"><h3>${icon('sun')}${t('Apariencia','Appearance')}</h3><p>${t('Una paleta para cada momento.','A palette for every moment.')}</p>${this.choices('theme',[['day',t('Día','Day')],['dark',t('Oscuro','Dark')],['forest',t('Bosque','Forest')]])}</article>
      <article class="setup-card"><h3>${icon('layout')}${t('Distribución','Layout')}</h3><p>${t('Dale espacio a tu forma de trabajar.','Make room for the way you work.')}</p>${this.choices('layout',[['studio',t('Equilibrada','Balanced'),'layout'],['code',t('Compacta','Compact'),'dock-left'],['focus',t('Concentración','Focus'),'focus']])}</article>
      <article class="setup-card"><h3>${icon('sparkles')}Melody</h3><p>${t('Tu asistente, donde prefieras.','Your assistant, where you prefer.')}</p>${this.choices('position',[['right',t('Derecha','Right'),'dock-right'],['left',t('Izquierda','Left'),'dock-left'],['bottom',t('Abajo','Bottom'),'dock-bottom']])}</article>
      <article class="setup-card setup-wide"><h3>${icon('code')}${t('Tu enfoque','Your focus')}</h3>${this.choices('style',[['general',t('General','General'),'code'],['web',t('Web','Web'),'globe'],['data',t('Datos','Data'),'cpu'],['design',t('Diseño','Design'),'palette']])}</article></div>${this.preview()}</div>`:step===1?`<div class="setup-compose setup-personal-compose"><article class="setup-card setup-personal"><div class="setup-personal-title"><span>${icon('palette')}</span><div><h3>${t('Tu firma en Zénit','Your signature in Zénit')}</h3><p>${t('Unos detalles para empezar a tu manera.','A few details to make a start, your way.')}</p></div></div><label for="onboard-name">${t('Cómo quieres que te llamemos','What should we call you?')}<input id="onboard-name" maxlength="40" autocomplete="nickname" placeholder="${t('Tu nombre','Your name')}" value="${esc(d.name)}"></label><div class="setup-preferences">${[['motion','sparkles',t('Animaciones suaves','Smooth motion'),t('Transiciones ligeras que siguen tu ritmo.','Light transitions that follow your pace.')],['autosave','save',t('Guardar automáticamente','Auto save'),t('Con control de conflictos y copia previa.','With conflict checks and a previous copy.')]].map(([id,glyph,label,note])=>`<div class="preference-row"><span class="setup-preference-icon">${icon(glyph)}</span><label for="onboard-${id}" class="preference-label"><strong>${label}</strong><small>${note}</small></label><label class="platform-switch"><input type="checkbox" id="onboard-${id}" ${d[id]?'checked':''}><span></span></label></div>`).join('')}</div><p class="setup-local">${icon('shield')}${t('Tu perfil y tus preferencias se guardan en este equipo.','Your profile and preferences stay on this device.')}</p></article>${this.preview(true)}</div>`:`<div class="setup-ready">${glassArt('welcome')}<h2>${t('Hola','Hello')}, ${esc(d.name)}.</h2><p>${t('Un lugar para lo que viene.','A place for what comes next.')}</p><span class="ready-badge">${icon('check')}${t('Tu espacio está preparado','Your workspace is ready')}</span></div>`}</div>
      <footer class="setup-footer"><button class="secondary-button" id="onboard-back" ${step===0?'disabled':''}>${icon('chevron-left')}${t('Atrás','Back')}</button><p role="status" class="setup-feedback"></p><button class="primary-button" id="onboard-next">${step===2?t('Ir al inicio','Go to home'):t('Continuar','Continue')}${icon('arrow-right')}</button></footer></div></div>`;
    root.querySelectorAll('[data-choice]').forEach(b=>b.onclick=()=>{d[b.dataset.choice]=b.dataset.value;if(b.dataset.choice==='theme'){applyShellTheme(null,document.documentElement,b.dataset.value,{persist:false});this.host.platform.appliedTheme=null;}for(const sibling of b.parentElement.children){const selected=sibling===b;sibling.classList.toggle('selected',selected);sibling.setAttribute('aria-pressed',String(selected));}this.refreshPreview();});
    root.querySelector('#onboard-name')?.addEventListener('input',()=>{this.capture();this.refreshPreview();});
    root.querySelector('#onboard-locale')?.addEventListener('change',e=>{d.locale=e.target.value;this.render(step,false);root.querySelector('#onboard-locale').focus();});
    root.querySelector('#onboard-back').onclick=()=>this.render(step-1);
    root.querySelector('#skip-onboarding').onclick=()=>this.finish(true);
    root.querySelector('#onboard-next').onclick=()=>{this.capture();d.name=d.name.trim();if(step===1&&!d.name){root.querySelector('#onboard-name').focus();return;}if(step===2)this.finish();else this.render(step+1);};
    root.onkeydown=e=>{if(e.key==='Tab'){const list=[...root.querySelectorAll('button:not(:disabled),input,select')];if(e.shiftKey&&document.activeElement===list[0]){e.preventDefault();list.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===list.at(-1)){e.preventDefault();list[0].focus();}}};
    if(animate&&d.motion)this.host.motion.play(root.querySelector('.setup-main'),[{opacity:0,translate:'0 6px'},{opacity:1,translate:'0 0'}],240);
    this.studio.hydrate(root);root.querySelector('.setup-content').scrollTop=0;root.querySelector('#onboarding-title').focus({preventScroll:true});
  }
  async finish(skip=false){
    if(this.busy)return;this.busy=true;this.capture();const buttons=[...this.root.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);
    try{await this.studio.finishOnboarding(skip);}catch(error){this.root.querySelector('.setup-feedback').textContent=error.message;buttons.forEach(b=>b.disabled=false);this.root.querySelector('#onboard-back').disabled=this.step===0;}finally{this.busy=false;}
  }
}
