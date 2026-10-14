import {icon,escapeHTML as esc} from './icons.js';

/** Capability-driven editor menu. Every leaf runs an existing editor or extension action. */
export class EditorContextMenu {
  constructor(preview){this.preview=preview;this.h=preview.host;this.levels=[];this.bindings=[];}
  attach(view){
    view.updateOptions({contextmenu:false});
    this.bindings.push(view.onContextMenu(e=>{
      if(!e.target.position)return;
      e.event.preventDefault();e.event.stopPropagation();view.focus();
      if(!view.getSelection()?.containsPosition(e.target.position))view.setPosition(e.target.position);
      this.open(view,e.event.posx,e.event.posy);
    }));
    view.addAction({id:'zenit.contextMenu',label:'Open editor menu',keybindings:[monaco.KeyMod.Shift|monaco.KeyCode.F10],run:()=>{
      const node=view.getDomNode().getBoundingClientRect(),pos=view.getScrolledVisiblePosition(view.getPosition());
      this.open(view,node.left+(pos?.left||20),node.top+(pos?.top||20)+(pos?.height||20));
    }});
  }
  items(view){
    const h=this.h,p=h.platform,t=(es,en)=>p.t(es,en),item=(label,run,glyph='code',shortcut='')=>({label,run,glyph,shortcut});
    const action=(id,es,en,key='')=>{const a=view.getAction(id);return a?.isSupported()?item(t(es,en),()=>a.run(),'code',key):null;};
    const group=(label,glyph,items)=>({label,glyph,children:items.filter(Boolean)});
    const supported=(entries)=>entries.map(x=>action(...x)).filter(Boolean);
    const navigation=supported([
      ['editor.action.revealDefinition','Ir a definición','Go to Definition','F12'],
      ['editor.action.revealDeclaration','Ir a declaración','Go to Declaration'],
      ['editor.action.goToTypeDefinition','Ir a definición del tipo','Go to Type Definition'],
      ['editor.action.goToImplementation','Ir a implementación','Go to Implementation','Ctrl F12'],
      ['editor.action.goToReferences','Buscar referencias','Find References','Shift F12']]);
    const peek=supported([['editor.action.peekDefinition','Definición','Definition','Alt F12'],['editor.action.referenceSearch.trigger','Referencias','References']]);
    const refactor=supported([['editor.action.rename','Renombrar símbolo','Rename Symbol','F2'],['editor.action.changeAll','Cambiar todas las coincidencias','Change All Occurrences','Ctrl F2'],['editor.action.quickFix','Corrección rápida…','Quick Fix…','Ctrl .'],['editor.action.refactor','Refactorizar…','Refactor…'],['editor.action.sourceAction','Acciones de código…','Source Actions…'],['editor.action.formatDocument','Formatear documento','Format Document','Shift Alt F'],['editor.action.formatSelection','Formatear selección','Format Selection']]);
    const ask=(question)=>{h.dock.floatPanel('assistant');p.setMelodyMode?.('chat');const input=document.getElementById('ai-input');input.value=question;input.focus();};
    const lang=view.getModel()?.getLanguageId(),native=['c','cpp','nc','asm'].includes(lang),known=native||lang==='python';
    const extensionGroups=new Map();
    for(const [id,c] of this.preview.runtimeCommands||[]){if(!extensionGroups.has(c.ext))extensionGroups.set(c.ext,[]);extensionGroups.get(c.ext).push(item(c.title||c.id,()=>p.pluginCommand(id),'extensions'));}
    const extensionActions=[...extensionGroups].map(([label,children])=>group(label,'extensions',children));
    return [
      ...navigation,peek.length?group(t('Vista rápida','Peek'),'search',peek):null,
      navigation.length||peek.length?{separator:true}:null,
      group('Melody','sparkles',[
        item(t('Explicar selección o archivo','Explain Selection or File'),()=>ask(t('Explica el código adjunto y su flujo.','Explain the attached code and its control flow.')),'bulb'),
        item(t('Revisar y encontrar errores','Review and Find Bugs'),()=>ask(t('Revisa el código adjunto. Señala errores demostrables y propone pruebas.','Review the attached code. Identify demonstrable bugs and propose tests.')),'shield'),
        item(t('Diseñar pruebas','Design Tests'),()=>ask(t('Propón pruebas del código adjunto, incluidos casos límite.','Propose tests for the attached code, including boundary cases.')),'flask')]),
      group(t('Ejecutar e inspeccionar','Run & Inspect'),'play',[
        item(t('Ejecutar archivo','Run File'),()=>h.perform('run'),'play'),
        item(t('Comprobar archivo','Check File'),()=>h.perform('check-file'),'check'),
        item(t('Depurar…','Debug…'),()=>h.studio.debug(),'bug','F5'),
        item('Lantern · '+t('ejecutar búfer','run buffer'),()=>h.studio.lantern.action('start'),'sparkles')]),
      known?item(t('Dependencias del proyecto…','Project Dependencies…'),()=>p.extensions(native?'native':'python'),'extensions'):null,
      {separator:true},...refactor,refactor.length?{separator:true}:null,
      ...supported([['editor.action.clipboardCutAction','Cortar','Cut','Ctrl X'],['editor.action.clipboardCopyAction','Copiar','Copy','Ctrl C'],['editor.action.clipboardPasteAction','Pegar','Paste','Ctrl V'],['editor.action.commentLine','Alternar comentario','Toggle Line Comment','Ctrl /']]),
      group(t('Archivo','File'),'file',[
        item(t('Guardar','Save'),()=>h.saveFile(h.editor.current),'check','Ctrl S'),
        item(t('Guardar como…','Save As…'),()=>this.preview.saveAs(),'file'),
        item(t('Copiar ruta relativa','Copy Relative Path'),()=>navigator.clipboard.writeText(h.editor.current),'copy'),
        item(t('Abrir en otra ventana','Open in Another Window'),()=>this.preview.newWindow(h.editor.current),'arrow-up-right')]),
      extensionActions.length?{separator:true}:null,extensionActions.length?group(t('Extensiones activas','Active Extensions'),'extensions',extensionActions):null,
      {separator:true},item(t('Paleta de comandos…','Command Palette…'),()=>h.studio.host.palette('>'),'search','Ctrl Shift P')
    ].filter(Boolean);
  }
  open(view,x,y){
    this.close(false);this.view=view;this.x=x;this.y=y;this.all=this.items(view);
    this.render(this.all,0,x,y,true);
    this.outside=e=>{if(!e.target.closest?.('.editor-context-menu'))this.close(false);};
    this.scroll=e=>{if(!e.target.closest?.('.editor-context-menu'))this.close(false);};
    document.addEventListener('pointerdown',this.outside,true);window.addEventListener('resize',this.outside);document.addEventListener('wheel',this.scroll,{capture:true,passive:true});
  }
  render(items,level,x,y,search=false){
    this.trim(level);const menu=document.createElement('section');menu.className='editor-context-menu';menu.setAttribute('role','menu');menu.setAttribute('aria-label',level?'Submenu':'Editor actions');
    if(search){const label=document.createElement('label');label.className='editor-menu-search';label.innerHTML=icon('search')+'<input type="search" autocomplete="off" placeholder="'+esc(this.h.platform.t('Buscar acción…','Search actions…'))+'" aria-label="'+esc(this.h.platform.t('Buscar acción','Search actions'))+'">';menu.append(label);label.querySelector('input').oninput=e=>this.filter(e.target.value);}
    const list=document.createElement('div');list.className='editor-menu-items';menu.append(list);document.body.append(menu);this.levels.push(menu);this.fill(list,items,level);
    menu.style.left=Math.max(8,Math.min(x,innerWidth-menu.offsetWidth-8))+'px';menu.style.top=Math.max(8,Math.min(y,innerHeight-menu.offsetHeight-8))+'px';
    menu.onkeydown=e=>this.keys(e,level);menu.querySelector('input,button')?.focus();return menu;
  }
  fill(list,items,level){
    list.replaceChildren();let previousSeparator=true;
    items.forEach((item,i)=>{
      if(item.separator){if(!previousSeparator&&items.slice(i+1).some(x=>!x.separator)){const hr=document.createElement('hr');hr.setAttribute('role','separator');list.append(hr);}previousSeparator=true;return;}previousSeparator=false;
      const b=document.createElement('button');b.type='button';b.setAttribute('role','menuitem');b.tabIndex=-1;b.innerHTML=icon(item.glyph||'code')+'<span>'+esc(item.label)+'</span>'+(item.children?icon('chevron-right'):'<kbd>'+esc(item.shortcut||'')+'</kbd>');list.append(b);
      const expand=()=>{if(!b.isConnected)return;this.trim(level+1);if(!item.children)return;const r=b.getBoundingClientRect();const child=this.render(item.children,level+1,r.right+5,r.top);b.setAttribute('aria-expanded','true');if(r.right+5+child.offsetWidth>innerWidth-8)child.style.left=Math.max(8,r.left-child.offsetWidth-5)+'px';};
      if(item.children){b.setAttribute('aria-haspopup','menu');b.setAttribute('aria-expanded','false');b.expand=expand;}
      b.onpointerenter=()=>{clearTimeout(this.hover);this.hover=setTimeout(()=>{if(item.children){const previous=document.activeElement;expand();previous?.focus();}else this.trim(level+1);},140);};
      b.onclick=()=>{clearTimeout(this.hover);if(item.children)return expand();this.close();this.preview.safe(item.run);};
    });
  }
  filter(query){this.trim(1);const q=query.trim().toLocaleLowerCase(),flatten=(items,path='')=>items.flatMap(x=>x.children?flatten(x.children,path+x.label+' › '):x.run?[{...x,label:path+x.label}]:[]);this.fill(this.levels[0].querySelector('.editor-menu-items'),q?flatten(this.all).filter(x=>x.label.toLocaleLowerCase().includes(q)):this.all,0);}
  keys(e,level){
    const menu=this.levels[level],buttons=[...menu.querySelectorAll('button')],index=buttons.indexOf(document.activeElement);let target;
    if(e.key==='Escape'){e.preventDefault();e.stopPropagation();this.close();return;}
    if(e.key==='Tab'){this.close();return;}
    if(e.key==='ArrowRight'&&document.activeElement.expand){e.preventDefault();document.activeElement.expand();return;}
    if(e.key==='ArrowLeft'&&level){e.preventDefault();const parent=this.levels[level-1].querySelector('[aria-expanded=true]');this.trim(level);parent?.focus();return;}
    if(e.key==='ArrowDown')target=buttons[(index+1)%buttons.length];
    if(e.key==='ArrowUp')target=buttons[(index-1+buttons.length)%buttons.length];
    if(e.key==='Home'&&e.target.tagName!=='INPUT')target=buttons[0];
    if(e.key==='End'&&e.target.tagName!=='INPUT')target=buttons.at(-1);
    if(target){e.preventDefault();target.focus();target.scrollIntoView({block:'nearest'});}
  }
  trim(level){while(this.levels.length>level)this.levels.pop().remove();for(const menu of this.levels.slice(level-1))menu.querySelectorAll('[aria-expanded=true]').forEach(b=>b.setAttribute('aria-expanded','false'));}
  close(focus=true){clearTimeout(this.hover);this.trim(0);document.removeEventListener('pointerdown',this.outside,true);window.removeEventListener('resize',this.outside);document.removeEventListener('wheel',this.scroll,true);if(focus)this.view?.focus();}
}
