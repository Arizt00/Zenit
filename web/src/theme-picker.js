import {themePalette} from './extension-theme.js';
import {icon,escapeHTML as esc} from './icons.js';

/** Palette previews come from the actual installed theme, with no extra renderer. */
export class ThemePicker{
  constructor(platform){this.platform=platform;}
  open(owner=''){
    const p=this.platform,themes=(p.extensionThemes||[]).filter(t=>!owner||t.owner===owner),active=p.prefs['appearance.extensionTheme'];
    if(!themes.length){p.host.notify('Esta extensión no aporta temas activos.');return;}
    p.host.modal(p.t('Elegir tema','Choose a theme'),`<section class="theme-picker"><p>${p.t('Explora los colores de tus temas instalados y elige una variante.','Explore the colours of your installed themes and choose a variant.')}</p><label class="theme-picker-search">${icon('search')}<input autofocus aria-label="${p.t('Buscar un tema','Search themes')}" placeholder="${p.t('Buscar tema o extensión…','Search theme or extension…')}"></label><div class="theme-picker-grid"></div><p class="error-message" role="alert"></p></section>`,{wide:true});
    const root=document.querySelector('.theme-picker'),grid=root.querySelector('.theme-picker-grid');
    for(const theme of themes){
      const {palette:c,dark}=themePalette(theme),button=document.createElement('button');button.className='theme-picker-option';button.dataset.themeId=theme.id;button.dataset.search=(theme.label+' '+theme.owner).toLocaleLowerCase();button.setAttribute('aria-pressed',String(theme.id===active));
      button.innerHTML=`<span class="theme-colour-preview"><span class="theme-preview-sidebar"></span><span class="theme-preview-lines"><i></i><i></i><i></i></span><span class="theme-preview-accent"></span></span><span class="theme-option-label"><strong>${esc(theme.label)}</strong><small>${esc(theme.owner)} · ${dark?p.t('Oscuro','Dark'):p.t('Claro','Light')}</small></span><span class="theme-selected">${icon('check')}</span>`;
      for(const [key,value] of Object.entries({bg:c.editor,side:c.surface,keyword:c['syntax-keyword'],string:c['syntax-string'],comment:c['syntax-comment'],accent:c.accent}))button.style.setProperty('--preview-'+key,value);
      button.onclick=async()=>{grid.querySelectorAll('button').forEach(b=>b.disabled=true);try{const index=p.extensionThemes.findIndex(t=>t.id===theme.id);if(index<0)throw Error('El tema dejó de estar disponible.');await p.applyExtensionTheme(index);if(root.isConnected)p.host.closeModal();}catch(error){root.querySelector('[role=alert]').textContent=error.message;grid.querySelectorAll('button').forEach(b=>b.disabled=false);}};
      grid.append(button);
    }
    const input=root.querySelector('input');input.oninput=()=>{const query=input.value.toLocaleLowerCase().trim();for(const button of grid.children)button.hidden=!button.dataset.search.includes(query);};input.onkeydown=e=>{if(e.key==='ArrowDown'){e.preventDefault();grid.querySelector('button:not([hidden])')?.focus();}};
    grid.onkeydown=e=>{const buttons=[...grid.children].filter(b=>!b.hidden&&!b.disabled),index=buttons.indexOf(document.activeElement),columns=getComputedStyle(grid).gridTemplateColumns.split(' ').length,step={ArrowRight:1,ArrowLeft:-1,ArrowDown:columns,ArrowUp:-columns}[e.key];if(step!==undefined){e.preventDefault();buttons[(index+step+buttons.length)%buttons.length]?.focus();}if(e.key==='Home'||e.key==='End'){e.preventDefault();buttons[e.key==='Home'?0:buttons.length-1]?.focus();}};input.focus();
  }
}
