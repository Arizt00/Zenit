// Lossless notebook structure; outputs use the actual nbformat MIME encoding.
module.exports=v=>({
 deserializeNotebook(bytes){
  const raw=JSON.parse(Buffer.from(bytes).toString('utf8'));
  if(raw.nbformat!==4||!Array.isArray(raw.cells))throw Error('Solo se admiten cuadernos nbformat 4.');
  const text=x=>Array.isArray(x)?x.join(''):x||'';
  return {_raw:raw,metadata:raw.metadata||{},cells:raw.cells.map(c=>({_raw:c,kind:c.cell_type==='markdown'?1:2,value:text(c.source),languageId:c.cell_type==='markdown'?'markdown':raw.metadata?.language_info?.name||'python',metadata:c.metadata||{},executionSummary:c.execution_count==null?undefined:{executionOrder:c.execution_count},outputs:(c.outputs||[]).map(o=>new v.NotebookCellOutput(o.output_type==='stream'?[v.NotebookCellOutputItem.text(text(o.text),o.name==='stderr'?'application/vnd.code.notebook.stderr':'application/vnd.code.notebook.stdout')]:o.output_type==='error'?[v.NotebookCellOutputItem.json({name:o.ename,message:o.evalue,stack:(o.traceback||[]).join('\n')},'application/vnd.code.notebook.error')]:Object.entries(o.data||{}).map(([mime,value])=>mime==='application/json'?v.NotebookCellOutputItem.json(value,mime):/^image\/(?!svg)/.test(mime)?new v.NotebookCellOutputItem(Buffer.from(text(value),'base64'),mime):v.NotebookCellOutputItem.text(text(value),mime)),o.metadata||{}))}))};
 },
 serializeNotebook(value){
  const output=entry=>entry.items.flatMap(item=>{
   const text=Buffer.from(item.data).toString('utf8');
   if(item.mime==='application/vnd.code.notebook.stdout'||item.mime==='application/vnd.code.notebook.stderr')return [{output_type:'stream',name:item.mime.endsWith('stderr')?'stderr':'stdout',text}];
   if(item.mime==='application/vnd.code.notebook.error'){const e=JSON.parse(text);return [{output_type:'error',ename:e.name,evalue:e.message,traceback:(e.stack||'').split('\n')}];}
   return [];
  });
  const rich=entry=>entry.items.filter(i=>!i.mime.startsWith('application/vnd.code.notebook.'));
  return Buffer.from(JSON.stringify({...value._raw,nbformat:4,nbformat_minor:value._raw?.nbformat_minor??5,metadata:value.metadata,cells:value.cells.map(c=>({...c._raw,cell_type:c.kind===1?'markdown':'code',metadata:c.metadata||{},source:c.value.split(/(?<=\n)/),...(c.kind===1?{}:{execution_count:c.executionSummary?.executionOrder??null,outputs:c.outputs.flatMap(o=>{const items=rich(o);return [...output(o),...(items.length?[{output_type:'display_data',metadata:o.metadata||{},data:Object.fromEntries(items.map(i=>[i.mime,i.mime==='application/json'?JSON.parse(Buffer.from(i.data).toString('utf8')):/^image\/(?!svg)/.test(i.mime)?Buffer.from(i.data).toString('base64'):Buffer.from(i.data).toString('utf8')]))}]:[])];})})}))},null,2));
 }
});
