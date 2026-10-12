// Port attributes are evaluated by the host on demand. Forwarding remains an
// explicit transport capability; registering attributes never opens a port.
module.exports=function(v){
  const providers=new Set();
  v.PortAutoForwardAction={Notify:1,OpenBrowser:2,OpenBrowserOnce:3,OpenPreview:4,Silent:5,Ignore:6};
  v.PortAttributes=class{constructor(autoForwardAction){this.autoForwardAction=autoForwardAction;}};
  v.workspace.registerPortAttributesProvider=(selector,provider)=>{
    if(typeof provider?.providePortAttributes!=='function')throw Error('PortAttributesProvider requiere providePortAttributes.');
    const entry={selector,provider};providers.add(entry);return new v.Disposable(()=>providers.delete(entry));
  };
  return async values=>{
    if(!Array.isArray(values)||values.length>100)throw Error('Lista de puertos inválida.');
    const items=[];
    for(const value of values){
      if(!Number.isInteger(value.port)||value.port<1||value.port>65535)throw Error('Puerto inválido.');
      let attributes;
      for(const {selector,provider} of providers){
        const range=selector.portRange;if(typeof range==='number'&&value.port!==range||Array.isArray(range)&&(value.port<range[0]||value.port>=range[1]))continue;
        if(selector.commandPattern&&!new RegExp(selector.commandPattern).test(value.commandLine||''))continue;
        const result=await provider.providePortAttributes(value,{isCancellationRequested:false,onCancellationRequested:()=>new v.Disposable()});
        if(result)attributes={...attributes,...result};
      }
      if(attributes)items.push({port:value.port,pid:value.pid,attributes});
    }
    return {items};
  };
};
