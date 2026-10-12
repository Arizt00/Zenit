// Authentication providers supplied by authorised extensions. No fabricated tokens.
const providers=new Map(),grants=new Set();let changed;
module.exports=function(v,consumer){
  changed ||= new v.EventEmitter();
  const get=id=>{const p=providers.get(id);if(!p)throw Error('Proveedor de autenticación no conectado: '+id+'. Instala y autoriza su proveedor antes de iniciar sesión.');return p;};
  const grantKey=(id,s)=>JSON.stringify([consumer,id,s.id,[...s.scopes].sort()]);
  v.authentication={
    onDidChangeSessions:changed.event,
    registerAuthenticationProvider(id,label,provider,options={}){
      if(providers.has(id))throw Error('Proveedor de autenticación ya registrado: '+id);
      const entry={id,label,provider,options};providers.set(id,entry);
      const listener=provider.onDidChangeSessions(e=>{for(const s of [...e.removed||[],...e.changed||[]])for(const key of [...grants])if(JSON.parse(key)[1]===id&&JSON.parse(key)[2]===s.id)grants.delete(key);changed.fire({provider:{id,label}});});
      return new v.Disposable(()=>{listener.dispose();providers.delete(id);for(const key of [...grants])if(JSON.parse(key)[1]===id)grants.delete(key);changed.fire({provider:{id,label}});});
    },
    async getAccounts(id){const sessions=await get(id).provider.getSessions();return [...new Map(sessions.map(s=>[s.account.id,s.account])).values()];},
    async getSession(id,scopes,options={}){
      if(!Array.isArray(scopes))throw Error('Las solicitudes WWW-Authenticate aún no están integradas.');
      if(options.silent&&(options.createIfNone||options.forceNewSession))throw Error('silent no puede combinarse con un inicio de sesión interactivo.');
      const p=get(id),sessions=(await p.provider.getSessions(scopes,{account:options.account})).filter(s=>scopes.every(scope=>s.scopes.includes(scope))&&(!options.account||s.account.id===options.account.id));
      const allowed=sessions.filter(s=>grants.has(grantKey(id,s)));
      if(options.silent)return allowed[0];
      let session=!options.forceNewSession&&allowed[0];if(session)return session;
      if(!options.createIfNone&&!options.forceNewSession)return undefined;
      const choice=await v.window.showQuickPick([{label:'Autorizar '+consumer,detail:'Compartir la sesión de '+p.label+' para: '+scopes.join(', '),allow:true},{label:'Cancelar',allow:false}],{title:'Acceso a la cuenta',ignoreFocusOut:true});
      if(!choice?.allow)throw Error('Acceso a la cuenta cancelado.');
      if(sessions.length&&!options.forceNewSession){const selected=sessions.length===1?{index:0}:await v.window.showQuickPick(sessions.map((s,index)=>({label:s.account.label,index})),{title:'Elegir cuenta'});if(!selected)throw Error('Selección de cuenta cancelada.');session=sessions[selected.index];}
      else session=await p.provider.createSession(scopes,{account:options.account});
      if(!session?.accessToken||!session.id||!session.account||!Array.isArray(session.scopes))throw Error('El proveedor no devolvió una sesión válida.');
      grants.add(grantKey(id,session));return session;
    }
  };
};
