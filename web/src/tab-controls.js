/** Recoverable tab navigation and bulk close use the normal dirty-file prompt. */
export function installTabControls(h){
  const tabs=document.getElementById('file-tabs'),closed=[],ed=h.editor,close=ed.close.bind(ed),reset=ed.reset.bind(ed);
  ed.close=path=>{if(ed.models.has(path)){closed.push(path);if(closed.length>20)closed.shift();}close(path);};
  ed.reset=()=>{closed.length=0;reset();};
  const reopen=async()=>{const path=closed.pop();if(path)await h.openFile(path);};
  const bulk=async paths=>{for(const path of paths){await h.closeFile(path);if(ed.models.has(path))break;}};
  tabs.addEventListener('contextmenu',e=>{const tab=e.target.closest('[data-tab]');if(!tab)return;e.preventDefault();const paths=[...ed.models.keys()],index=paths.indexOf(tab.dataset.tab);h.showMenu(tab,[{label:'Close tab',icon:'close',run:()=>h.closeFile(tab.dataset.tab)},{label:'Close other tabs',icon:'files',run:()=>bulk(paths.filter(p=>p!==tab.dataset.tab))},{label:'Close tabs to the right',icon:'arrow-right',disabled:index===paths.length-1,run:()=>bulk(paths.slice(index+1))},{label:'Reopen closed tab',icon:'refresh',disabled:!closed.length,run:reopen}],'Editor tabs');});
  tabs.addEventListener('auxclick',e=>{const tab=e.target.closest('[data-tab]');if(e.button===1&&tab){e.preventDefault();h.closeFile(tab.dataset.tab);}});
  document.addEventListener('keydown',e=>{
    if(document.getElementById('modal-backdrop')?.classList.contains('hidden')===false)return;
    const control=e.ctrlKey||e.metaKey;
    if(control&&e.shiftKey&&e.key.toLowerCase()==='t'){e.preventDefault();h.safe(reopen);return;}
    const paths=[...ed.models.keys()],index=paths.indexOf(ed.current);let next;
    if(control&&['PageUp','PageDown'].includes(e.key))next=(index+(e.key==='PageUp'?-1:1)+paths.length)%paths.length;
    else if(tabs.contains(e.target))next=e.key==='ArrowLeft'?(index-1+paths.length)%paths.length:e.key==='ArrowRight'?(index+1)%paths.length:e.key==='Home'?0:e.key==='End'?paths.length-1:undefined;
    if(next!==undefined&&paths.length){e.preventDefault();h.activateFile(paths[next]);if(tabs.contains(e.target))tabs.querySelector('.active')?.focus();}
  },true);
}
