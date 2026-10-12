// Uses the existing, authorized Emma voice. No assistant memory or credentials.
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import readline from 'node:readline';
const root=process.argv[2],emit=value=>process.stdout.write(JSON.stringify(value)+'\n');
let runtime;
try{
 const {OriginalVoiceRuntime}=await import(pathToFileURL(path.join(root,'electron/original-voice.mjs')));
 const {assistantVoice}=await import(pathToFileURL(path.join(root,'electron/assistant-voices.mjs')));
 const selected=assistantVoice('emma');
 if(!selected.authorized||selected.defaultEngine!=='qwen'||!selected.id?.startsWith('podcast-emma-'))throw Error('La nueva voz seleccionada de Emma todavía no está preparada en esta instalación.');
 runtime=new OriginalVoiceRuntime({identityDirectory:path.join(root,'resources/voice-identity'),authorizedIdentityDirectory:selected.directory});
 const status=runtime.status();
 // Never silently substitute a different voice/engine for the approved one.
 if(!status.personalIdentity?.active||!status.genericAvailable||status.personalIdentity.id!==selected.id)throw Error('El motor Qwen de la nueva voz de Emma no está disponible en esta instalación.');
 emit({type:'ready',engine:'qwen',identity:status.personalIdentity.id});
 if(process.argv.includes('--status')){runtime.stop();process.exit(0);}
 const input=readline.createInterface({input:process.stdin}),abort=new AbortController();let started=false;
 input.on('line',async line=>{
  try{
   const request=JSON.parse(line);if(request.cancel){abort.abort();runtime.stop();return;}if(started)return;started=true;
   const result=await runtime.speak({plan:{text:request.text,language:'es-ES',acousticMode:'selected',speed:1},signal:abort.signal,onChunk:chunk=>emit({type:'audio',pcm:chunk.pcm,sampleRate:chunk.sampleRate})});
   if(result.engine!=='qwen')throw Error('Emma no ha usado la nueva voz seleccionada.');emit({type:'done',engine:result.engine});
  }catch(error){emit({type:'error',message:error.message});}
  finally{runtime.stop();input.close();setTimeout(()=>process.exit(0),100);}
 });
 process.stdin.on('end',()=>{abort.abort();runtime.stop();});
}catch(error){emit({type:'error',message:error.message});runtime?.stop();process.exitCode=1;}
