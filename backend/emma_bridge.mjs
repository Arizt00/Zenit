// Uses Emma's own local inference API. No Emma profile, memory or credentials are read.
import {pathToFileURL} from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import readline from 'node:readline';
const emit=value=>process.stdout.write(JSON.stringify(value)+'\n');
const argument=name=>{const index=process.argv.indexOf(name);return index<0?'':process.argv[index+1]||'';};
let runtime;
try {
 const directory=process.argv[2];
 const {NativeInferenceRuntime}=await import(pathToFileURL(path.join(directory,'electron','inference-runtime.mjs')).href);
 const {MAIN_MODEL,validateModelFile}=await import(pathToFileURL(path.join(directory,'electron','inference-models.mjs')).href);
 runtime=new NativeInferenceRuntime({directory:path.join(directory,'resources','inference')});
 const specs=JSON.parse(argument('--model-specs')||'[]');
 if(!Array.isArray(specs)||specs.length>16)throw Error('Catálogo local no válido.');
 for(const spec of specs){
  if(!spec||typeof spec.id!=='string'||!path.isAbsolute(spec.path||'')||!Number.isSafeInteger(spec.bytes)||spec.bytes<1||!/^[a-f0-9]{64}$/.test(spec.sha256||''))throw Error('Modelo local no válido.');
 }
 // Zénit resolves only its pinned, verified additions. Emma's files stay unchanged.
 const resolve=runtime.model.bind(runtime);
 runtime.model=(settings={})=>{
  const spec=specs.find(item=>item.id===settings.localModel);
  return spec?{...spec,file:validateModelFile(spec.path,spec)}:resolve(settings);
 };
 let catalog=[];
 const file=path.join(directory,'electron','model-catalog.json');
 if(fs.existsSync(file)&&fs.statSync(file).size<2_000_000){const data=JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));if(Array.isArray(data))catalog=data;}
 const candidates=[...new Set([MAIN_MODEL.id,...catalog.map(item=>item.id),...specs.map(item=>item.id)].filter(id=>typeof id==='string'))];
 const available=candidates.filter(id=>runtime.status({localModel:id}).available);
 if(process.argv.includes('--models')){
  if(!available.length)throw Error('No hay ningún modelo GGUF verificado disponible en Emma o Zénit.');
  emit({type:'ready',models:available,provider:'llama.cpp'});process.exit(0);
 }
 const model=argument('--model');
 if(!model||!available.includes(model))throw Error('El modelo seleccionado no está disponible: '+model+'. Consulta los modelos de Emma; no se sustituirá por otro.');
 emit({type:'ready',model,provider:'llama.cpp'});
 const lines=readline.createInterface({input:process.stdin});
 const controller=new AbortController();let started=false;
 lines.on('line',async line=>{
  try{
   const request=JSON.parse(line);
   if(request.cancel){controller.abort();runtime.stop();return;}
   if(started)return;started=true;
   if(!Array.isArray(request.messages))throw Error('Mensajes no válidos.');
   // Reserve output space and the language reference instead of truncating at 4K.
   const budget=Math.ceil(Buffer.byteLength(JSON.stringify(request.messages),'utf8')/2)+request.maxTokens+512;
   if(budget>32768)throw Error('El contexto supera el presupuesto local de 32768 tokens. Selecciona menos código o reduce el límite de salida.');
   const context=Math.max(8192,Math.ceil(budget/2048)*2048);
   emit({type:'status',message:'Cargando '+model+' · contexto '+context+'…'});
   const result=await runtime.complete({settings:{localModel:model,localContextTokens:context,localGpuLayers:48},messages:request.messages,signal:controller.signal,maxTokens:request.maxTokens,onDelta:text=>emit({type:'delta',text})});
   emit({type:'done',metrics:result.metrics});
  }catch(error){emit({type:'error',message:error.message});}
  finally{runtime.stop();lines.close();setTimeout(()=>process.exit(0),50);}
 });
 process.stdin.on('end',()=>{controller.abort();runtime.stop();});
}catch(error){emit({type:'error',message:error.message});runtime?.stop();process.exitCode=1;}
