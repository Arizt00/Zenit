// File-system providers dispatch to the actual extension implementation.
// Virtual mounts are never translated into host file paths.
module.exports=function(v,event,makeDocument,documents,globPattern){
  const providers=new Map(),local={...v.workspace.fs},localOpen=v.workspace.openTextDocument,localWatcher=v.workspace.createFileSystemWatcher;
  v.FileChangeType={Changed:1,Created:2,Deleted:3};
  const changes=new v.EventEmitter();
  const entry=uri=>{const p=providers.get(uri.scheme);if(!p)throw v.FileSystemError.Unavailable('No hay proveedor para '+uri.scheme);return p;};
  v.workspace.registerFileSystemProvider=(scheme,provider,options={})=>{
    if(!/^[a-z][a-z\d+.-]*$/i.test(scheme)||scheme==='file'||providers.has(scheme))throw Error('Esquema de filesystem no válido o ya registrado: '+scheme);
    const item={provider,options};providers.set(scheme,item);
    const listener=provider.onDidChangeFile?.(values=>changes.fire(values));
    return new v.Disposable(()=>{listener?.dispose();providers.delete(scheme);});
  };
  v.workspace.fs.isWritableFileSystem=scheme=>scheme==='file'?true:providers.has(scheme)?!providers.get(scheme).options.isReadonly:undefined;
  for(const method of ['stat','readDirectory','readFile','createDirectory','writeFile','delete','rename','copy'])v.workspace.fs[method]=async(uri,...args)=>{
    if(uri.scheme==='file'){
      if(['rename','copy'].includes(method)&&args[0].scheme!=='file')throw v.FileSystemError.Unavailable('Operación entre filesystems distintos.');
      return local[method](uri,...args);
    }
    const {provider,options}=entry(uri);
    if(['createDirectory','writeFile','delete','rename','copy'].includes(method)&&options.isReadonly)throw v.FileSystemError.NoPermissions(uri);
    if(['rename','copy'].includes(method)&&args[0].scheme!==uri.scheme)throw v.FileSystemError.Unavailable('Operación entre filesystems distintos.');
    if(typeof provider[method]!=='function')throw v.FileSystemError.Unavailable('El proveedor no implementa '+method);
    if(method==='writeFile')args.push({create:true,overwrite:true});
    return provider[method](uri,...args);
  };
  v.workspace.openTextDocument=async value=>{
    if(!value||typeof value==='object'&&!value.scheme&&('content' in value||'language' in value)){
      const uri=v.Uri.parse('untitled:/'+require('node:crypto').randomUUID()),doc=makeDocument({uri,text:value?.content||'',language:value?.language||'plaintext',dirty:!!value?.content});documents.set(uri.toString(),doc);event('open').fire(doc);return doc;
    }
    if(!value?.scheme||!providers.has(value.scheme))return localOpen(value);
    const previous=documents.get(value.toString());if(previous)return previous;
    const bytes=await v.workspace.fs.readFile(value),text=new TextDecoder('utf-8',{fatal:true}).decode(bytes),doc=makeDocument({uri:value,text,path:value.fsPath});documents.set(value.toString(),doc);event('open').fire(doc);return doc;
  };
  v.workspace.createFileSystemWatcher=(pattern,ignoreCreate=false,ignoreChange=false,ignoreDelete=false)=>{
    const base=pattern?.baseUri;if(!base||base.scheme==='file')return localWatcher(pattern,ignoreCreate,ignoreChange,ignoreDelete);
    const {provider}=entry(base),watch=provider.watch?.(base,{recursive:true,excludes:[]}),match=globPattern(pattern.pattern),created=new v.EventEmitter(),changed=new v.EventEmitter(),deleted=new v.EventEmitter();
    const listener=changes.event(values=>{for(const value of values){if(value.uri.scheme!==base.scheme||value.uri.authority!==base.authority||!value.uri.path.startsWith(base.path.replace(/\/$/,'')+'/'))continue;const relative=value.uri.path.slice(base.path.replace(/\/$/,'').length+1);if(!match.test(relative))continue;if(value.type===1&&!ignoreChange)changed.fire(value.uri);if(value.type===2&&!ignoreCreate)created.fire(value.uri);if(value.type===3&&!ignoreDelete)deleted.fire(value.uri);}});
    return {onDidCreate:created.event,onDidChange:changed.event,onDidDelete:deleted.event,ignoreCreateEvents:ignoreCreate,ignoreChangeEvents:ignoreChange,ignoreDeleteEvents:ignoreDelete,dispose(){listener.dispose();watch?.dispose();created.dispose();changed.dispose();deleted.dispose();}};
  };
  return {has:uri=>providers.has(v.Uri.parse(uri).scheme),read:async uri=>new TextDecoder('utf-8',{fatal:true}).decode(await v.workspace.fs.readFile(v.Uri.parse(uri)))};
};
