// Assignments made by EditorConfig and other extensions reach the real Monaco model.
module.exports=(host,decorate)=>editor=>{
  decorate(editor);
  const descriptor=Object.getOwnPropertyDescriptor(editor,'options');
  const read=descriptor?.get?()=>descriptor.get.call(editor):()=>descriptor?.value||{};
  const publish=value=>{if(!value||typeof value!=='object')throw Error('Opciones del editor inválidas.');host.service('editor.options',{uri:editor.document.uri,options:value}).catch(error=>console.error(error.message));};
  Object.defineProperty(editor,'options',{configurable:true,get:()=>new Proxy({...read()},{set(target,key,value){publish({[key]:value});target[key]=value;return true;}}),set:publish});
  return editor;
};
