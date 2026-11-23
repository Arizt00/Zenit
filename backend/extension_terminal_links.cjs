module.exports=function(v,host){
  const providers=new Set(),links=new Map();let next=0;const scope=require('node:crypto').randomUUID();
  v.window.registerTerminalLinkProvider=provider=>{providers.add(provider);return new v.Disposable(()=>{providers.delete(provider);for(const [id,item] of links)if(item.provider===provider)links.delete(id);});};
  return {has:id=>links.has(id),get count(){return providers.size;},async provide(request){
    if(typeof request.line!=='string'||request.line.length>10000)throw Error('Terminal line too long.');
    const info=await host.service('terminal.inspect',{terminal:request.terminal}),terminal=v.window.terminals.find(t=>t._sessionId===request.terminal)||{name:info.name,creationOptions:{cwd:info.cwd},exitStatus:info.closed?{code:info.code}:undefined,processId:Promise.resolve(info.pid),sendText:(text,addNewLine=true)=>host.service('terminal.linkWrite',{terminal:request.terminal,text:String(text)+(addNewLine?'\r':'')})};
    const items=[];for(const provider of providers){const result=await provider.provideTerminalLinks({line:request.line,terminal},{isCancellationRequested:false,onCancellationRequested:()=>new v.Disposable()})||[];for(const link of result.slice(0,100)){if(!Number.isInteger(link.startIndex)||!Number.isInteger(link.length)||link.startIndex<0||link.length<1||link.startIndex+link.length>request.line.length)continue;const id=scope+':'+(++next);links.set(id,{provider,link});items.push({id,startIndex:link.startIndex,length:link.length,tooltip:link.tooltip});}}
    while(links.size>1000)links.delete(links.keys().next().value);return {items};
  },async activate(id){const item=links.get(id);if(!item)throw Error('El enlace ha caducado. Vuelve a pasar el cursor por la línea.');return item.provider.handleTerminalLink(item.link);}};
};
