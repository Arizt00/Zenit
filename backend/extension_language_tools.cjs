// Extension-contributed tools can be invoked explicitly. This is not a model
// provider or an automatic grant to use the user's assistant credentials.
module.exports=function(v,options){
  const tools=new Map();
  v.LanguageModelTextPart=class{constructor(value){this.value=value;}};
  v.LanguageModelToolResult=class{constructor(content){this.content=content;}};
  v.lm={
    get tools(){return [...tools].map(([name])=>{const declared=options.manifest.contributes?.languageModelTools?.find(x=>x.name===name);return {name,description:declared?.modelDescription||declared?.userDescription||name,inputSchema:declared?.inputSchema,tags:declared?.tags||[]};});},
    registerTool(name,tool){if(tools.has(name)||typeof tool?.invoke!=='function')throw Error('Herramienta de modelo no válida o duplicada: '+name);tools.set(name,tool);return new v.Disposable(()=>tools.delete(name));},
    async invokeTool(name,opts,token={isCancellationRequested:false,onCancellationRequested:()=>new v.Disposable()}){
      const tool=tools.get(name);if(!tool)throw Error('Herramienta de modelo no registrada: '+name);if(token.isCancellationRequested)throw new v.CancellationError();
      const preparation=await tool.prepareInvocation?.({input:opts.input,invocationContext:opts.invocationContext},token);
      if(preparation?.confirmationMessages){const message=preparation.confirmationMessages,choice=await v.window.showQuickPick([{label:'Permitir',detail:typeof message.message==='string'?message.message:message.message?.value,allow:true},{label:'Cancelar',allow:false}],{title:message.title||name});if(!choice?.allow)throw Error('Invocación de herramienta cancelada.');}
      return tool.invoke(opts,token);
    }
  };
};
