import {escapeHTML as esc} from './icons.js';
export function installExplorerMenu(host){
  let clipboard=null,lastTrash=null;
  const sidebar=document.querySelector('#sidebar-content');let focused=null;
  sidebar.addEventListener('focusin',e=>{const item=e.target.closest('[data-file],[data-dir]');if(item)focused=item;});
  sidebar.addEventListener('keydown',e=>{
    const item=e.target.closest('[data-file],[data-dir]')||focused;if(!item||e.target.matches('input,textarea'))return;
    const path=item.dataset.file||item.dataset.dir||'',parent=item.hasAttribute('data-dir')?path:path.split('/').slice(0,-1).join('/');
    const control=e.ctrlKey||e.metaKey;let action;
    if(e.key==='F2'&&path)action=()=>renameFile(path);
    if(e.key==='Delete'&&path)action=()=>deleteFile(path);
    if(control&&['c','x'].includes(e.key.toLowerCase())&&path)action=()=>{clipboard={path,cut:e.key.toLowerCase()==='x'};};
    if(control&&e.key.toLowerCase()==='v'&&clipboard)action=async()=>{await operation(clipboard.cut?'move':'copy',clipboard.path,(parent?parent+'/':'')+clipboard.path.split('/').pop());if(clipboard.cut)clipboard=null;};
    if(action){e.preventDefault();e.stopPropagation();safe(action);}
  });
  const safe=fn=>Promise.resolve().then(fn).catch(e=>host.notify(e.message,'error',6000));
  const affected=path=>[...host.editor.models.keys()].filter(x=>x===path||x.startsWith(path+'/'));
  const clean=async path=>{for(const p of affected(path))if(host.editor.isDirty(p)){if(!await host.confirmDialog('Cambios sin guardar',`Guarda los cambios de ${p} antes de continuar.`,'Guardar y continuar'))return false;await host.saveFile(p);}return true;};
  async function operation(action,path,destination){
    if(action==='delete'&&!await clean(path))return;
    const result=await host.api('/platform/files/operation',{operation:action,path,destination});
    if(action==='rename'||action==='move'){
      if(!result.unchanged)await host.relocated([{oldPath:result.oldPath||path,path:result.path}]);
      await host.refreshTree();return result;
    }
    if(action==='delete'){lastTrash=result.ticket;await host.removed(result.edit);if(!host.editor.current&&host.editor.visiblePaths().length)host.editor.activate(host.editor.visiblePaths().at(-1));host.refreshDocuments();}
    await host.refreshTree();
    if(action==='delete')host.notify('Movido a la papelera del proyecto. Usa «Deshacer eliminación» en el menú.');
  }
  async function deleteFile(path){
    if(host.editor.models.get(path)?.transient)return host.closeFile(path);
    if(!path||/^(?:[A-Za-z]:|\/)/.test(path))throw Error('Abre la carpeta de este archivo como proyecto para eliminarlo.');
    for(const detached of host.editor.detachedPaths)if(detached===path||detached.startsWith(path+'/'))throw Error('Vuelve a acoplar el archivo separado antes de eliminarlo.');
    if(await (host.confirmRoutine||host.confirmDialog)('Eliminar del proyecto',`¿Mover ${path} a la papelera del proyecto? Podrás recuperarlo con «Deshacer eliminación».`,'Eliminar'))await operation('delete',path);
  }
  async function restoreDeleted(){
    if(!lastTrash)return host.notify('No hay una eliminación pendiente de deshacer en esta sesión.');
    await host.api('/platform/files/operation',{operation:'restore',ticket:lastTrash});lastTrash=null;await host.refreshTree();
  }
  function renameFile(path){
    if(host.editor.models.get(path)?.transient)return host.saveAs(path);
    if(!path||/^(?:[A-Za-z]:|\/)/.test(path))throw Error('Abre la carpeta de este archivo como proyecto para cambiar su nombre.');
    for(const detached of host.editor.detachedPaths)if(detached===path||detached.startsWith(path+'/'))throw Error('Vuelve a acoplar el archivo separado antes de cambiar su nombre.');
    const name=path.split('/').pop(),prefix=path.slice(0,-name.length);
    host.modal('Cambiar nombre',`<form id="file-rename-form"><label class="field-label">Nuevo nombre<input id="file-rename-name" name="name" required autocomplete="off" spellcheck="false" value="${esc(name)}"></label><p class="muted-copy">${esc(prefix||'Raíz del proyecto')} · Se conservarán los cambios sin guardar.</p><p data-rename-error role="alert"></p><div class="modal-actions"><button type="button" class="secondary-button" data-rename-cancel>Cancelar</button><button type="submit" class="primary-button">Cambiar nombre</button></div></form>`);
    const form=document.querySelector('#file-rename-form'),input=form.elements.name;
    form.querySelector('[data-rename-cancel]').onclick=()=>host.closeModal();
    requestAnimationFrame(()=>{if(!input.isConnected)return;input.focus();const dot=name.lastIndexOf('.');input.setSelectionRange(0,dot>0?dot:name.length);});
    form.onsubmit=e=>{e.preventDefault();safe(async()=>{
      const value=input.value.trim(),error=form.querySelector('[data-rename-error]');error.textContent='';
      if(!value||['.','..'].includes(value)||/[\\/]/.test(value)){error.textContent='Escribe un nombre de archivo, sin carpetas.';input.focus();return;}
      if(value===name){host.closeModal();return;}
      const button=form.querySelector('[type=submit]');button.disabled=true;
      try{await operation('rename',path,prefix+value);host.closeModal();}
      catch(failure){if(form.isConnected){error.textContent=failure.message;input.focus();}}
      finally{if(button.isConnected)button.disabled=false;}
    });};
  }
  function nameDialog(title,path,action,initial){host.modal(title,`<form id="file-operation"><label>Ruta dentro del proyecto<input id="file-operation-path" required value="${esc(initial)}"></label><div class="modal-actions"><button class="primary-button">${esc(title)}</button></div></form>`);document.querySelector('#file-operation').onsubmit=e=>{e.preventDefault();safe(async()=>{const value=document.querySelector('#file-operation-path').value.trim();if(action==='new'){await host.api('/save',{path:value,content:'',create:true});await host.refreshTree();await host.openFile(value);}else if(action==='mkdir')await operation('mkdir',value);else await operation(action,path,value);host.closeModal();});};}
  function menu(e){
    const element=e.target.closest('[data-file],[data-dir]'),path=element?.dataset.file||element?.dataset.dir||'',directory=!!element?.hasAttribute('data-dir')||!path,parent=directory?path:path.split('/').slice(0,-1).join('/'),prefix=parent?parent+'/':'';
    if(element){focused=element;element.focus();}e.preventDefault();e.stopPropagation();const items=[
      {label:'Nuevo archivo…',icon:'file',run:()=>nameDialog('Nuevo archivo',path,'new',prefix)},
      {label:'Nueva carpeta…',icon:'folder',run:()=>nameDialog('Nueva carpeta',path,'mkdir',prefix)},
      {separator:true},
      ...(!directory?[{label:'Abrir',icon:'file',run:()=>host.openFile(path)},
        {label:'Guardar',icon:'check',shortcut:'Ctrl S',run:async()=>{if(!host.editor.models.has(path))await host.openFile(path);await host.saveFile(path);}},
        {label:'Guardar como…',icon:'file',shortcut:'Ctrl Shift O',run:()=>host.saveAs(path)},
        {label:'Abrir en otra ventana',icon:'plus',run:()=>host.newWindow(path)},{label:'Abrir y ejecutar con Lantern',icon:'play',run:async()=>{await host.openFile(path);await host.lantern.action('start');}}]:[]),
      {label:'Buscar en esta carpeta',icon:'search',run:()=>host.search(parent)},
      {label:'Copiar ruta',icon:'copy',run:()=>navigator.clipboard.writeText(host.workspace().replaceAll('\\','/')+(path?'/'+path:''))},
      {label:'Copiar ruta relativa',icon:'copy',run:()=>navigator.clipboard.writeText(path||'.')},
      {separator:true},
      ...(path?[{label:'Cortar',icon:'code',shortcut:'Ctrl X',run:()=>{clipboard={path,cut:true};}},{label:'Copiar',icon:'copy',shortcut:'Ctrl C',run:()=>{clipboard={path,cut:false};}}]:[]),
      ...(clipboard?[{label:'Pegar',icon:'file',shortcut:'Ctrl V',run:async()=>{await operation(clipboard.cut?'move':'copy',clipboard.path,prefix+clipboard.path.split('/').pop());if(clipboard.cut)clipboard=null;}}]:[]),
      ...(path?[{label:'Duplicar…',icon:'copy',run:()=>nameDialog('Duplicar',path,'copy',path+'.copy')},{label:'Cambiar nombre…',icon:'rename',shortcut:'F2',run:()=>renameFile(path)},{label:'Eliminar',icon:'trash',shortcut:'Supr',run:()=>deleteFile(path)}]:[]),
      ...(lastTrash?[{label:'Deshacer eliminación',icon:'undo',run:()=>restoreDeleted()}]:[]),
      {separator:true},{label:'Actualizar explorador',icon:'refresh',run:host.refreshTree}
    ];host.showMenu({getBoundingClientRect:()=>({left:e.clientX,right:e.clientX,bottom:e.clientY})},items,path.split('/').pop()||'Proyecto');
  }
  sidebar.addEventListener('contextmenu',menu);
  return {renameFile,deleteFile,restoreDeleted,canRestoreDeleted:()=>!!lastTrash};
}
