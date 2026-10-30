import {icon} from './icons.js';
import {sideOf} from './layout-state.js';

/** One header contract; keep the live panels, actions and their handlers. */
export function installPanelChrome(host){
  // Native windows have their own return/destination toolbar.
  if(new URLSearchParams(location.search).has('panel'))return {dispose(){}};
  const p=host.platform,dock=p.host.dock,t=(es,en)=>p.t(es,en),records=new Map();
  const button=(command,glyph)=>{const b=document.createElement('button');b.type='button';b.className='icon-button';b.dataset.headerCommand=command;b.innerHTML=icon(glyph);return b;};
  const label=(b,text)=>{b.title=text;b.setAttribute('aria-label',text);if(b.dataset.tooltip)b.dataset.tooltip=text;};
  const editor=document.querySelector('.editor-tabbar');
  const projectMark=document.querySelector('#project-panel .heading-mark');projectMark.innerHTML=icon('folder');projectMark.dataset.icon='folder';
  editor.querySelector('.panel-header-identity')?.remove();
  for(const [id,selector] of [['project','#project-panel>.panel-heading'],['editor','.editor-tabbar'],['console','.terminal-toolbar'],['assistant','#assistant-panel>.assistant-heading']]){
    const header=document.querySelector(selector);if(!header)continue;
    header.classList.add('workbench-heading');header.dataset.panelHeader=id;
    const container=header.querySelector(id==='console'?'.terminal-tools':'.heading-actions')||header;
    const detach=header.querySelector(id==='editor'?'[data-action=detach-editor]':'[data-panel-detach]');
    let more=header.querySelector('.zenit-tools-menu');if(!more){more=button('more','more');more.classList.add('zenit-tools-menu');}
    const collapse=button('collapse',id==='editor'?'focus':'panel-collapse-left');
    detach.dataset.headerCommand='detach';more.dataset.headerCommand='more';
    const controls=document.createElement('div');controls.className='panel-header-actions';controls.setAttribute('role','group');
    // Secondary tools stay in the DOM so extension/native hooks remain valid.
    for(const b of container.querySelectorAll('button'))if(b!==detach&&b!==more&&!b.matches('.zenit-terminal-picker,.file-tab,.tab-close,.new-tab'))b.classList.add('panel-header-overflow');
    if(id==='editor')for(const b of header.querySelectorAll('.editor-workflows button,[data-action=editor-menu]'))if(b!==detach)b.classList.add('panel-header-overflow');
    detach.classList.remove('zenit-overflow-action','zenit-responsive-action');
    controls.append(collapse,detach,more);container.append(controls);
    const record={id,header,controls,collapse,detach,more};records.set(id,record);
    collapse.onclick=()=>collapsePanel(id);more.onclick=()=>menu(id,more);
    if(id==='console'&&p.runTerminalButton){const context=document.createElement('div');context.className='panel-header-context';p.runTerminalButton.classList.remove('panel-header-overflow','zenit-overflow-action');context.append(p.runTerminalButton);controls.before(context);}
    // Stopping a response must stay immediately reachable while it is running.
    if(id==='assistant'){
      const context=document.createElement('div');context.className='panel-header-context';
      const stop=header.querySelector('#ai-cancel-generation'),fresh=header.querySelector('.melody-new-chat');
      for(const b of [fresh,stop])if(b){b.classList.remove('panel-header-overflow','zenit-overflow-action');context.append(b);}
      record.context=context;controls.before(context);
    }
  }
  function collapsePanel(id){
    if(id==='editor'){dock.focus();return;}
    const side=sideOf(dock.state,id);
    if(dock.state.floating[id]||side==='bottom')dock.hide(id);else dock.collapse(side);
  }
  function rows(id){
    const r=records.get(id);
    return [...r.header.querySelectorAll('button')].filter(b=>!b.closest('.panel-header-actions,.panel-header-context')&&!b.matches('.file-tab,.tab-close,.new-tab,.terminal-tab,.zenit-terminal-picker,.dock-grip,[data-collapse-panel],[data-action=toggle-terminal]')&&(b.classList.contains('panel-header-overflow')||b.classList.contains('zenit-overflow-action'))).map(b=>({
      label:b.getAttribute('aria-label')||b.title||b.textContent.trim(),icon:b.querySelector('[data-glyph]')?.dataset.glyph||'settings',disabled:b.disabled,run:()=>b.click()
    }));
  }
  function menu(id,anchor){
    const extras=id==='editor'?[{label:t('Espacios guardados','Saved spaces'),icon:'workspace',run:()=>host.perform('saved-spaces')},{label:t('Organizar paneles','Arrange panels'),icon:'layout',run:()=>host.perform('layout-settings')}]:[{label:t('Mover o agrupar panel','Move or group panel'),icon:'layout',run:()=>dock.organize(id)}];
    host.showMenu(anchor,[...rows(id),{separator:true},...extras],id==='editor'?'Editor':id==='assistant'?'Melody':id==='console'?t('Terminal','Terminal'):t('Proyecto','Project'));
  }
  function updateControls(record){
    const {id,collapse,detach,more,controls}=record,side=sideOf(dock.state,id),focus=dock.state.preset==='focus';
    const text=id==='editor'?(focus?t('Restaurar paneles','Restore panels'):t('Concentrar editor','Focus editor')):t('Contraer panel','Collapse panel');
    label(collapse,text);const glyph=id==='editor'?'focus':side==='bottom'||dock.state.floating[id]?'chevron-down':'panel-collapse-'+side;
    if(collapse.firstElementChild?.dataset.glyph!==glyph)collapse.innerHTML=icon(glyph);
    if(id==='editor')collapse.setAttribute('aria-pressed',String(focus));
    collapse.setAttribute('aria-controls',id==='editor'?'workspace':dock.panels[id].id);
    label(detach,t('Separar en otra ventana','Detach to another window'));label(more,t('Más opciones','More options'));
    more.setAttribute('aria-haspopup','menu');controls.setAttribute('aria-label',t('Acciones del panel','Panel actions'));
  }
  function refresh(){
    for(const r of records.values()){
      updateControls(r);
      if(r.context)r.controls.before(r.context);
    }
    // DockManager regenerates group toolbars. Give them the same action order
    // without touching the panels, terminal connections or editor models.
    for(const [side,slot] of Object.entries(dock.slots)){
      if(!slot.classList.contains('is-grouped'))continue;
      for(const tab of slot.querySelectorAll('.dock-tab'))tab.setAttribute('aria-label',tab.querySelector('span').textContent);
      const id=slot.querySelector('.dock-tab[aria-selected=true]')?.dataset.dockTab,source=records.get(id),container=slot.querySelector('.dock-group-actions');if(!source)continue;
      if(source.context)container.before(source.context);
      container.replaceChildren();container.classList.add('panel-header-actions');
      const collapse=button('collapse','panel-collapse-'+side),detach=button('detach','detach'),more=button('more','more');
      updateControls({id,collapse,detach,more,controls:container});
      collapse.onclick=()=>collapsePanel(id);detach.onclick=()=>source.detach.click();more.onclick=()=>menu(id,more);container.append(collapse,detach,more);
    }
  }
  const change=()=>refresh();dock.root.addEventListener('lumen:layout-rendered',change);
  const apply=p.applyPreferences.bind(p);p.applyPreferences=(...args)=>{const result=apply(...args);refresh();return result;};refresh();
  return {dispose(){dock.root.removeEventListener('lumen:layout-rendered',change);}};
}
