const fs=require('node:fs'),path=require('node:path');
module.exports=function(v,host,storage){
  const file=path.join(storage,'environment-collection.json'),scopes=new Map();let persistent=true,description,scheduled=false;
  v.EnvironmentVariableMutatorType={Replace:1,Append:2,Prepend:3};
  try{const saved=JSON.parse(fs.readFileSync(file,'utf8'));for(const item of saved)scopes.set(item.scope,new Map(item.values));}catch{}
  const publish=()=>{if(!host.service)throw Error('El servicio de entorno no está conectado.');if(scheduled)return;scheduled=true;queueMicrotask(()=>{scheduled=false;const collections=[...scopes].map(([scope,map])=>({scope,values:[...map]}));try{if(persistent){const temp=file+'.tmp';fs.writeFileSync(temp,JSON.stringify(collections));fs.renameSync(temp,file);}else if(fs.existsSync(file))fs.unlinkSync(file);}catch(error){console.error('No se pudo conservar la colección de entorno: '+error.message);}host.service('environment.update',{collections}).catch(e=>console.error(e.message));});};
  const collection=scope=>{
    if(!scopes.has(scope))scopes.set(scope,new Map());const values=scopes.get(scope),update=(variable,value,type,options={})=>{if(typeof variable!=='string'||!variable||/[=\0]/.test(variable)||typeof value!=='string'||value.includes('\0'))throw Error('Variable de entorno inválida.');if(options.applyAtShellIntegration)throw Error('Las mutaciones en shell integration aún no están integradas.');values.set(variable,{value,type,options});publish();};
    return {get persistent(){return persistent;},set persistent(value){persistent=!!value;publish();},get description(){return description;},set description(value){description=value;},replace:(key,value,opts)=>update(key,value,1,opts),append:(key,value,opts)=>update(key,value,2,opts),prepend:(key,value,opts)=>update(key,value,3,opts),get:key=>values.get(key),delete(key){values.delete(key);publish();},clear(){values.clear();publish();},forEach(callback,thisArg){values.forEach((value,key)=>callback.call(thisArg,key,value,this));},[Symbol.iterator]:()=>values[Symbol.iterator](),getScoped:folder=>collection(folder?.uri?.fsPath||null)};
  };
  const root=collection(null);if(host.service&&[...scopes.values()].some(map=>map.size))publish();return root;
};
