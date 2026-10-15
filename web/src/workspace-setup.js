import {icon,escapeHTML as esc} from './icons.js';
import {glassArt} from './glass.js';

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
  choices(key,items){return `<div class="setup-choices">${items.map(([value,label,glyph])=>`<button type="button" data-choice="${key}" data-value="${value}" class="${this.draft[key]===value?'selected':''}" aria-pressed="${this.draft[key]===value}">${key==='theme'?`<span class="space-preview ${value}" aria-hidden="true"><i></i><i></i><i></i></span>`:icon(glyph||'layout')}<span>${label}</span></button>`).join('')}</div>`;}
  render(step,animate=true){
    this.capture();this.step=step;const d=this.draft,t=this.t.bind(this),root=this.root;
    const steps=[t('Tu espacio','Your workspace'),t('Personalización','Personalize'),t('Listo','Ready')];
    root.innerHTML=`<header class="setup-brand"><span class="setup-logo">Z</span><strong>ZÉNIT <span>IDE</span></strong><span class="setup-edition">${this.host.platform.state.version}</span><button class="text-button" id="skip-onboarding">${t('Omitir configuración','Skip setup')}${icon('arrow-right')}</button></header>
      <div class="setup-shell"><aside class="setup-sidebar"><nav aria-label="${t('Configuración inicial','Workspace setup')}">${steps.map((s,i)=>`<div class="setup-step ${i===step?'active':''}" ${i===step?'aria-current="step"':''}><span>${i<step?icon('check'):i+1}</span>${s}</div>`).join('')}</nav><div class="setup-signature">${glassArt('welcome')}<p>${t('Un espacio para<br>tus próximas ideas.','A space for<br>your next ideas.')}</p></div></aside>
      <div class="setup-main"><div class="setup-heading"><span class="eyebrow">${t('PASO','STEP')} ${step+1} / 3</span><h1 id="onboarding-title" tabindex="-1">${[t('Diseña tu espacio de trabajo','Design your workspace'),t('Haz que se sienta tuyo','Make yourself at home'),t('Todo listo para crear','Ready for your next idea')][step]}</h1><p>${[t('Elige un punto de partida. Podrás cambiarlo desde Ajustes.','Choose a starting point. You can change everything in Settings.'),t('Los detalles que hacen que trabajar sea más cómodo.','A few details to make your work feel more comfortable.'),t('Tu espacio está preparado. El siguiente paso es tuyo.','Your workspace is ready. The next step is yours.')][step]}</p></div>
      <div class="setup-content">${step===0?`<div class="setup-grid">
      <article class="setup-card"><h3>${icon('globe')}${t('Idioma','Language')}</h3><p>${t('El idioma de la interfaz.','The language of your interface.')}</p><label class="setup-language" for="onboard-locale"><select id="onboard-locale"><option value="es" ${d.locale==='es'?'selected':''}>Español</option><option value="en" ${d.locale==='en'?'selected':''}>English</option></select></label></article>
      <article class="setup-card"><h3>${icon('sun')}${t('Apariencia','Appearance')}</h3><p>${t('Una paleta para cada momento.','A palette for every moment.')}</p>${this.choices('theme',[['day',t('Día','Day')],['dark',t('Oscuro','Dark')],['forest',t('Bosque','Forest')]])}</article>
      <article class="setup-card"><h3>${icon('layout')}${t('Distribución','Layout')}</h3><p>${t('Dale espacio a tu forma de trabajar.','Make room for the way you work.')}</p>${this.choices('layout',[['studio',t('Equilibrada','Balanced'),'layout'],['code',t('Compacta','Compact'),'dock-left'],['focus',t('Concentración','Focus'),'focus']])}</article>
      <article class="setup-card"><h3>${icon('sparkles')}Melody</h3><p>${t('Tu asistente, donde prefieras.','Your assistant, where you prefer.')}</p>${this.choices('position',[['right',t('Derecha','Right'),'dock-right'],['left',t('Izquierda','Left'),'dock-left'],['bottom',t('Abajo','Bottom'),'dock-bottom']])}</article>
      <article class="setup-card setup-wide"><h3>${icon('code')}${t('Tu enfoque','Your focus')}</h3>${this.choices('style',[['general',t('General','General'),'code'],['web',t('Web','Web'),'globe'],['data',t('Datos','Data'),'cpu'],['design',t('Diseño','Design'),'palette']])}</article></div>`:step===1?`<article class="setup-card setup-personal"><h3>${icon('palette')}${t('Tu firma en Zénit','Your signature in Zénit')}</h3><label for="onboard-name">${t('Nombre del perfil','Profile name')}<input id="onboard-name" maxlength="40" autocomplete="nickname" value="${esc(d.name)}"></label>${[['motion',t('Animaciones suaves','Smooth motion'),t('Transiciones ligeras que siguen tu ritmo.','Light transitions that follow your pace.')],['autosave',t('Guardar automáticamente','Auto save'),t('Con control de conflictos y copia previa.','With conflict checks and a previous copy.')]].map(([id,label,note])=>`<div class="preference-row"><label for="onboard-${id}" class="preference-label"><strong>${label}</strong><small>${note}</small></label><label class="platform-switch"><input type="checkbox" id="onboard-${id}" ${d[id]?'checked':''}><span></span></label></div>`).join('')}<p class="setup-local">${icon('shield')}${t('Tu perfil y tus preferencias se guardan en este equipo.','Your profile and preferences stay on this device.')}</p></article>`:`<div class="setup-ready">${glassArt('welcome')}<h2>${t('Hola','Hello')}, ${esc(d.name)}.</h2><p>${t('Un lugar para lo que viene.','A place for what comes next.')}</p><span class="ready-badge">${icon('check')}${t('Tu espacio está preparado','Your workspace is ready')}</span></div>`}</div>
      <footer class="setup-footer"><button class="secondary-button" id="onboard-back" ${step===0?'disabled':''}>${icon('chevron-left')}${t('Atrás','Back')}</button><p role="status" class="setup-feedback"></p><button class="primary-button" id="onboard-next">${step===2?t('Ir al inicio','Go to home'):t('Continuar','Continue')}${icon('arrow-right')}</button></footer></div></div>`;
    root.querySelectorAll('[data-choice]').forEach(b=>b.onclick=()=>{d[b.dataset.choice]=b.dataset.value;if(b.dataset.choice==='theme')document.documentElement.dataset.theme=b.dataset.value;for(const sibling of b.parentElement.children){const selected=sibling===b;sibling.classList.toggle('selected',selected);sibling.setAttribute('aria-pressed',String(selected));}});
    root.querySelector('#onboard-locale')?.addEventListener('change',e=>{d.locale=e.target.value;this.render(step,false);root.querySelector('#onboard-locale').focus();});
    root.querySelector('#onboard-back').onclick=()=>this.render(step-1);
    root.querySelector('#skip-onboarding').onclick=()=>this.finish(true);
    root.querySelector('#onboard-next').onclick=()=>{this.capture();d.name=d.name.trim();if(step===1&&!d.name){root.querySelector('#onboard-name').focus();return;}if(step===2)this.finish();else this.render(step+1);};
    root.onkeydown=e=>{if(e.key==='Tab'){const list=[...root.querySelectorAll('button:not(:disabled),input,select')];if(e.shiftKey&&document.activeElement===list[0]){e.preventDefault();list.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===list.at(-1)){e.preventDefault();list[0].focus();}}};
    if(animate)this.host.motion.play(root.querySelector('.setup-main'),[{opacity:0,translate:'0 6px'},{opacity:1,translate:'0 0'}],240);
    this.studio.hydrate(root);root.querySelector('#onboarding-title').focus({preventScroll:true});
  }
  async finish(skip=false){
    if(this.busy)return;this.busy=true;this.capture();const buttons=[...this.root.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);
    try{await this.studio.finishOnboarding(skip);}catch(error){this.root.querySelector('.setup-feedback').textContent=error.message;buttons.forEach(b=>b.disabled=false);this.root.querySelector('#onboard-back').disabled=this.step===0;}finally{this.busy=false;}
  }
}
