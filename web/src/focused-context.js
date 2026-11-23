/** Deterministic excerpts from the already-open buffer. No filesystem discovery. */
export function focusedContext({text,question='',line=1,diagnostics=[],limit=56000}){
 if(text.length<=limit)return {content:text,partial:false,ranges:[],totalLines:text.split('\n').length};
 const lines=text.split('\n'),terms=[...new Set((question.match(/[\p{L}_][\p{L}\p{N}_]{2,}/gu)||[]).map(x=>x.toLocaleLowerCase()))].slice(0,16);
 const centers=[0,Math.max(0,Math.min(lines.length-1,line-1)),...diagnostics.slice(0,8).map(d=>Math.max(0,(Number(d.line)||1)-1))];
 const ranked=[];for(let i=0;i<lines.length;i++){const lower=lines[i].toLocaleLowerCase(),score=terms.reduce((n,t)=>n+(lower.includes(t)?1:0),0);if(score)ranked.push([score,i]);}
 ranked.sort((a,b)=>b[0]-a[0]||a[1]-b[1]);centers.push(...ranked.slice(0,16).map(x=>x[1]));
 const selected=new Set();let used=350;
 for(const center of centers){for(let distance=0;distance<=18;distance++)for(const i of distance?[center-distance,center+distance]:[center]){
  if(i<0||i>=lines.length||selected.has(i))continue;
  const cost=lines[i].length+16;if(used+cost>limit)continue;selected.add(i);used+=cost;
 }}
 const indexes=[...selected].sort((a,b)=>a-b),ranges=[];for(const i of indexes){const last=ranges.at(-1);if(last&&last[1]===i)last[1]=i+1;else ranges.push([i+1,i+1]);}
 let content='CONTEXTO PARCIAL DEL BÚFER · '+lines.length+' líneas. Solo se adjuntan los intervalos indicados; el resto se ha omitido. No es un archivo completo ni debe usarse para reemplazarlo.\n';
 for(const [a,b] of ranges){content+='\n[ líneas '+a+'–'+b+' ]\n';for(let n=a;n<=b;n++)content+=n+': '+lines[n-1]+'\n';}
 if(!indexes.length){let snippet=lines[Math.max(0,Math.min(lines.length-1,line-1))].slice(0,Math.max(0,limit-content.length-100));if(/[\uD800-\uDBFF]$/.test(snippet))snippet=snippet.slice(0,-1);content+='\n[ línea '+line+', fragmento parcial ]\n'+snippet;}
 return {content,partial:true,ranges,totalLines:lines.length};
}
