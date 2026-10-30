/** Cancel obsolete editor queries without aborting commands or user dialogs. */
export function extensionRequests(api){
  const pending=new Set();let disposed=false;
  const empty=()=>({items:[],incomplete:false,cancelled:true});
  return {dispose(){disposed=true;for(const cancel of [...pending])cancel();},async request(body,model,token){
    if(disposed||model?.isDisposed()||token?.isCancellationRequested)return empty();
    const requestKey=crypto.randomUUID(),listeners=[];let cancelled=false,finish;
    const obsolete=new Promise(resolve=>{finish=resolve;});
    const cancel=()=>{
      if(cancelled)return;cancelled=true;finish(empty());
      void api('/extensions/runtime/cancel',{id:body.id,requestKey}).catch(()=>{});
    };
    pending.add(cancel);
    for(const event of [model?.onDidChangeContent?.bind(model),model?.onWillDispose?.bind(model),token?.onCancellationRequested?.bind(token)])if(event)listeners.push(event(cancel));
    const response=Promise.resolve().then(()=>api('/extensions/runtime/request',{...body,requestKey}));
    try{return await Promise.race([response,obsolete]);}
    finally{pending.delete(cancel);for(const listener of listeners)listener?.dispose();}
  }};
}
