import {icon} from './icons.js';
/** One player per window. Only explicit Listen actions send text to Emma. */
export class MelodyVoiceUI{
 constructor(platform){
  this.platform=platform;this.sequence=0;this.audio=new Audio();this.audio.preload='auto';
  this.bar=document.createElement('div');this.bar.className='melody-voice';this.bar.hidden=true;
  this.bar.innerHTML='<span>'+icon('speaker')+'</span><div><strong>Melody · voz de Emma</strong><small role="status" aria-live="polite"></small></div><button class="icon-button voice-pause" aria-label="Pausar lectura" hidden>'+icon('pause')+'</button><button class="icon-button voice-stop" aria-label="Detener lectura">'+icon('stop')+'</button>';
  document.getElementById('ai-form').before(this.bar);this.status=this.bar.querySelector('small');this.pause=this.bar.querySelector('.voice-pause');
  this.pause.onclick=()=>platform.safe(async()=>{if(this.audio.paused)await this.audio.play();else this.audio.pause();});this.bar.querySelector('.voice-stop').onclick=()=>platform.safe(()=>this.stop());
  this.audio.onplay=()=>{this.pause.innerHTML=icon('pause');this.pause.setAttribute('aria-label','Pausar lectura');};
  this.audio.onpause=()=>{this.pause.innerHTML=icon('play');this.pause.setAttribute('aria-label','Reanudar lectura');};
  this.audio.ontimeupdate=()=>{if(!this.audio.duration||this.bar.hidden)return;const clock=n=>`${Math.floor(n/60)}:${String(Math.floor(n%60)).padStart(2,'0')}`;this.status.textContent=`${clock(this.audio.currentTime)} / ${clock(this.audio.duration)} · español`;};
  this.audio.onended=()=>{this.status.textContent='Lectura terminada';this.pause.innerHTML=icon('play');this.pause.setAttribute('aria-label','Escuchar de nuevo');};
  this.audio.onerror=()=>{if(this.audio.src&&this.job){this.status.textContent='No se pudo reproducir la voz. Puedes volver a escuchar la respuesta.';this.pause.hidden=true;}};
  const button=document.createElement('button');button.type='button';button.className='icon-button melody-selection-voice';button.innerHTML=icon('speaker');button.title='Escuchar la selección con la voz de Emma';button.setAttribute('aria-label',button.title);button.onclick=()=>platform.safe(async()=>{const text=platform.host.editor.getSelection()||document.getElementById('ai-input').value;if(!text.trim())throw Error('Selecciona texto o escribe un mensaje para escucharlo con Emma.');await this.speak(text);});document.querySelector('.assistant-heading .heading-actions').prepend(button);
 }
 attach(element,text){
  const button=document.createElement('button');button.className='text-button melody-listen';button.type='button';button.innerHTML=icon('speaker')+'<span>Escuchar</span>';button.title='Leer esta respuesta con la voz de Emma; los bloques de código se omiten';button.onclick=()=>this.platform.safe(()=>this.speak(text));element.append(button);return button;
 }
 async speak(text,owner=null){
  await this.stop();const sequence=++this.sequence;this.owner=owner;this.bar.hidden=false;this.status.textContent='Comprobando la voz de Emma…';this.pause.hidden=true;
  try{
   const status=await this.platform.api('/ai/voice');if(sequence!==this.sequence)return;if(!status.available)throw Error(status.message);
   const result=await this.platform.api('/ai/voice/start',{text});
   if(sequence!==this.sequence){await this.platform.api('/ai/voice/cancel',{id:result.id});return;}
   this.job=result.id;
   for(;;){
    const state=await this.platform.api('/ai/voice/job?id='+encodeURIComponent(result.id));if(sequence!==this.sequence)return;this.status.textContent=state.message;
    if(state.done){if(state.cancelled)return;if(state.error)throw Error(state.error);break;}
    await new Promise(resolve=>setTimeout(resolve,400));if(sequence!==this.sequence)return;
   }
   const blob=await this.platform.host.voiceAudio(result.id);if(sequence!==this.sequence)return;
   this.url=URL.createObjectURL(blob);this.audio.src=this.url;this.pause.hidden=false;this.status.textContent='Voz preparada · pulsa reproducir';
   try{await this.audio.play();}catch(error){if(error.name!=='NotAllowedError')throw error;this.pause.innerHTML=icon('play');this.pause.setAttribute('aria-label','Reproducir lectura');}
  }catch(error){if(sequence===this.sequence){this.status.textContent=error.message;this.pause.hidden=true;throw error;}}
 }
 async stop(owner=null){
  if(owner&&owner!==this.owner)return;this.sequence++;this.owner=null;this.audio.pause();this.audio.removeAttribute('src');this.audio.load();if(this.url){URL.revokeObjectURL(this.url);this.url=null;}this.bar.hidden=true;
  const id=this.job;this.job=null;if(id){await this.platform.api('/ai/voice/cancel',{id}).catch(()=>{});for(let n=0;n<16;n++){const state=await this.platform.api('/ai/voice/job?id='+encodeURIComponent(id)).catch(()=>({done:true}));if(state.done)break;await new Promise(r=>setTimeout(r,300));}}
 }
 dispose(){this.stop().catch(()=>{});this.bar.remove();}
}
