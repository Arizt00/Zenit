// A Live revision includes the followed file and the other unsaved sources.
// Binary documents, external files and private/generated paths stay out.
const excluded=new Set(['.git','.lumen','.ncc','node_modules','__pycache__','.venv','venv','Library','Temp','obj','bin','target','dist','build']);
export function captureLanternBuffers(editor,path=editor.current){
  const record=editor.models.get(path);
  if(!record||record.kind==='binary')return null;
  const read=(name,item)=>name===editor.current?editor.getValue():item.model?.getValue()??item.value;
  const buffers=[];
  for(const [name,item] of editor.models){
    if(name===path||item.kind==='binary'||!editor.isDirty(name)||/^(?:[A-Za-z]:[\\/]|\/)/.test(name))continue;
    if(name.replaceAll('\\','/').split('/').some(part=>excluded.has(part)||part.startsWith('.env')))continue;
    buffers.push({path:name,content:read(name,item)});
  }
  buffers.sort((a,b)=>a.path.localeCompare(b.path));
  return {path,content:read(path,record),version:record.model?.getVersionId()??0,buffers};
}
export function sameLanternCapture(first,second){
  return !!first&&!!second&&first.path===second.path&&first.content===second.content&&first.version===second.version&&
    first.buffers.length===second.buffers.length&&first.buffers.every((row,index)=>row.path===second.buffers[index].path&&row.content===second.buffers[index].content);
}
