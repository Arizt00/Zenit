/** Bounded comparisons of observed output, never inferred program state. */
export function lanternRevisions(state){
  const items=(state.history||[]).filter(x=>x.path===state.path&&Number.isInteger(x.revision)).map(x=>({...x}));
  if(state.revision>0){const current={revision:state.revision,path:state.path,output:state.output||'',code:state.code,time:state.updatedAt};const index=items.findIndex(x=>x.revision===state.revision);if(index<0)items.push(current);else items[index]=current;}
  return items.sort((a,b)=>a.revision-b.revision).slice(-20);
}
export function compareLanternOutput(before='',after=''){
  const left=String(before).slice(-8000).split('\n'),right=String(after).slice(-8000).split('\n'),truncated=left.length>200||right.length>200;
  const a=left.slice(-200),b=right.slice(-200),table=Array.from({length:a.length+1},()=>new Uint16Array(b.length+1));
  for(let i=a.length-1;i>=0;i--)for(let j=b.length-1;j>=0;j--)table[i][j]=a[i]===b[j]?table[i+1][j+1]+1:Math.max(table[i+1][j],table[i][j+1]);
  const lines=[];let i=0,j=0;
  while(i<a.length||j<b.length){if(i<a.length&&j<b.length&&a[i]===b[j]){lines.push({kind:'same',text:a[i++]});j++;}else if(j<b.length&&(i===a.length||table[i][j+1]>=table[i+1][j]))lines.push({kind:'added',text:b[j++]});else lines.push({kind:'removed',text:a[i++]});}
  return {lines,truncated,added:lines.filter(x=>x.kind==='added').length,removed:lines.filter(x=>x.kind==='removed').length};
}
export function lanternConsultation(state,baseline){
  const revisions=lanternRevisions(state),previous=revisions.find(x=>x.revision===baseline)||revisions.at(-2);
  return 'Review this observed Lantern execution. Explain the result, prioritize actual errors and suggest the next verification. Distinguish facts from hypotheses. Do not edit files.\n'+JSON.stringify({path:state.path,status:state.status,revision:state.revision,exitCode:state.code??null,diagnostics:(state.diagnostics||[]).slice(0,40),output:String(state.output||'').slice(-6500),...(previous?{baseline:{revision:previous.revision,exitCode:previous.code??null,output:String(previous.output||'').slice(-3500)}}:{})},null,2);
}
