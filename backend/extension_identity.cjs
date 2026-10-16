// Provider identities are queried explicitly; registration never creates a session.
module.exports=function(v,event){
  const providers=new Map();v.EditSessionIdentityMatch={None:0,Partial:50,Complete:100};
  v.workspace.onWillCreateEditSessionIdentity=event('editSessionIdentity').event;
  v.workspace.registerEditSessionIdentityProvider=(scheme,provider)=>{if(providers.has(scheme))throw Error('Edit session identity provider already registered.');providers.set(scheme,provider);return new v.Disposable(()=>providers.delete(scheme));};
  return async request=>{
    const folder=v.workspace.workspaceFolders[0],provider=providers.get(request.scheme||folder.uri.scheme);if(!provider)return undefined;
    const token={isCancellationRequested:false,onCancellationRequested:()=>new v.Disposable()};
    if(request.action==='match')return provider.provideEditSessionIdentityMatch(request.identity1,request.identity2,token);
    const pending=[];let dispatch=true;event('editSessionIdentity').fire({token,workspaceFolder:folder,waitUntil(value){if(!dispatch)throw Error('waitUntil must be called during dispatch.');pending.push(Promise.resolve(value));}});dispatch=false;await Promise.all(pending);return provider.provideEditSessionIdentity(folder,token);
  };
};
