/** Recoverable tab navigation and bulk close use the normal dirty-file prompt. */
export function installTabControls(h){
  const tabs=document.getElementById('file-tabs'),closed=[],ed=h.editor,close=ed.close.bind(ed),reset=ed.reset.bind(ed);
  const detached=document.createElement('button');detached.type='button';detached.className='detached-files-chip';detached.hidden=true;tabs.after(detached);
  detached.onclick=()=>h.showMenu(detached,[...ed.detachedPaths].map(path=>({label:path,icon:'detach',run:()=>h.openFile(path)})),'Archivos en otra ventana');
  let revealFrame=0;
  const revealActive=()=>{
    cancelAnimationFrame(revealFrame);
    revealFrame=requestAnimationFrame(()=>{
      const separated=ed.detachedPaths.size;detached.hidden=!separated;detached.textContent=separated+' '+(separated===1?'separado':'separados');detached.setAttribute('aria-label',separated+' archivos separados en otra ventana');
      const tab=tabs.querySelector('.file-tab.active');if(!tab||!tabs.clientWidth)return;
      const rect=tab.getBoundingClientRect(),viewport=tabs.getBoundingClientRect();
      if(rect.width>viewport.width||rect.left<viewport.left)tabs.scrollLeft+=rect.left-viewport.left;
      else if(rect.right>viewport.right)tabs.scrollLeft+=rect.right-viewport.right;
    });
  };
  // Native window restoration, density and title/font changes resize the strip
  // after renderTabs has already revealed the active file.
  const resize=new ResizeObserver(revealActive);resize.observe(tabs);
  ed.close=path=>{if(ed.models.has(path)){closed.push(path);if(closed.length>20)closed.shift();}close(path);};
  ed.reset=()=>{closed.length=0;reset();};
  const renamed=e=>{for(let i=0;i<closed.length;i++){const row=e.detail.find(r=>closed[i]===r.oldPath||closed[i].startsWith(r.oldPath+'/'));if(row)closed[i]=row.path+closed[i].slice(row.oldPath.length);}};
  document.addEventListener('zenit:files-renamed',renamed);
  const deleted=e=>{for(let i=closed.length-1;i>=0;i--)if(e.detail.some(path=>closed[i]===path||closed[i].startsWith(path+'/')))closed.splice(i,1);};document.addEventListener('zenit:files-deleted',deleted);
  const reopen=async()=>{const path=closed.pop();if(path)await h.openFile(path);};
  tabs.addEventListener('auxclick',e=>{const tab=e.target.closest('[data-tab]');if(e.button===1&&tab){e.preventDefault();h.closeFile(tab.dataset.tab);}});
  document.addEventListener('keydown',e=>{
    if(document.getElementById('modal-backdrop')?.classList.contains('hidden')===false)return;
    const control=e.ctrlKey||e.metaKey;
    if(control&&e.shiftKey&&e.key.toLowerCase()==='t'){e.preventDefault();h.safe(reopen);return;}
    if(control&&!e.shiftKey&&e.key.toLowerCase()==='w'&&(tabs.contains(e.target)||ed.view?.hasTextFocus())){e.preventDefault();e.stopPropagation();h.safe(()=>h.closeFile(ed.current));return;}
    const paths=[...tabs.querySelectorAll('[data-tab]')].filter(tab=>!tab.hidden).map(tab=>tab.dataset.tab),index=paths.indexOf(ed.current);let next;
    if(control&&['PageUp','PageDown'].includes(e.key))next=(index+(e.key==='PageUp'?-1:1)+paths.length)%paths.length;
    else if(tabs.contains(e.target))next=e.key==='ArrowLeft'?(index-1+paths.length)%paths.length:e.key==='ArrowRight'?(index+1)%paths.length:e.key==='Home'?0:e.key==='End'?paths.length-1:undefined;
    if(next!==undefined&&paths.length){e.preventDefault();h.activateFile(paths[next]);if(tabs.contains(e.target))tabs.querySelector('.active')?.focus();}
  },true);
  const mutation=new MutationObserver(revealActive);mutation.observe(tabs,{childList:true,attributes:true,attributeFilter:['class','hidden'],subtree:true});
  return {reopen,canReopen:()=>closed.length>0,dispose(){resize.disconnect();mutation.disconnect();detached.remove();cancelAnimationFrame(revealFrame);document.removeEventListener('zenit:files-renamed',renamed);document.removeEventListener('zenit:files-deleted',deleted);}};
}
