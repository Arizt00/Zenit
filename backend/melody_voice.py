"""Bounded, cancellable local speech jobs. Audio remains in memory in this session."""
import base64
import io
import json
import os
from pathlib import Path
import queue
import re
import secrets
import subprocess
import threading
import time
import wave
from .runtime_paths import find_tool

ERRORS = {'VOICE_RESOURCE_BUDGET':'Emma necesita más memoria de GPU disponible o una temperatura menor para generar voz.',
          'VOICE_TIMEOUT':'Emma tardó demasiado en generar la voz.',
          'ORIGINAL_VOICE_FAILED':'El motor de voz de Emma se ha detenido.',
          'ORIGINAL_VOICE_UNAVAILABLE':'La voz aprobada de Emma no está disponible.'}

def spoken_text(value):
    if not isinstance(value,str) or len(value)>100000:raise ValueError('Respuesta de voz inválida.')
    value=re.sub(r'```[\s\S]*?(?:```|$)','',value)
    value=re.sub(r'`([^`\n]*)`',r'\1',value)
    value=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',value)
    value=re.sub(r'(?m)^\s*[#>*-]+\s*','',value)
    value=value.replace('**','').replace('__','').strip()
    if not value:raise ValueError('Esta respuesta no contiene texto para leer; los bloques de código se conservan en el editor.')
    if len(value)>2500:raise ValueError('Selecciona un fragmento de hasta 2500 caracteres para leerlo con Emma.')
    return value

class MelodyVoice:
    def __init__(self,prefs):
        self.prefs=prefs;self.jobs={};self.lock=threading.RLock();self.closed=False

    def command(self):
        selected=self.prefs.get('ai.voiceDirectory') or self.prefs.get('ai.emmaDirectory')
        if not selected:raise ValueError('Indica la carpeta de Emma en Ajustes → Inteligencia artificial → Voz de Melody.')
        root=Path(selected).expanduser().resolve()
        for file in ('electron/original-voice.mjs','electron/authorized-voice-identity.mjs','electron/moss_voice_worker.py','electron/moss_streaming.py'):
            if not (root/file).is_file():raise ValueError('La carpeta seleccionada no contiene el motor de voz original de Emma.')
        node=find_tool('node')
        if not node:raise ValueError('La voz de Emma necesita el Node.js de Zénit.')
        return [str(node),str(Path(__file__).with_name('emma_voice_bridge.mjs')),str(root)]

    def status(self):
        try:
            result=subprocess.run([*self.command(),'--status'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            for line in result.stdout.splitlines():
                item=json.loads(line)
                if item.get('type')=='ready':return {'available':True,'voice':'Emma','engine':item['engine'],'language':'es-ES'}
                if item.get('type')=='error':raise ValueError(item['message'])
            raise ValueError('El motor de voz de Emma no respondió.')
        except (ValueError,OSError,subprocess.TimeoutExpired) as error:return {'available':False,'voice':'Emma','message':str(error)}

    def start(self,text):
        text=spoken_text(text);command=self.command()
        with self.lock:
            if self.closed:raise ValueError('La sesión de voz se ha cerrado.')
            if any(not job['done'] for job in self.jobs.values()):raise ValueError('Emma ya está preparando una respuesta de voz en otra ventana. Detén esa lectura antes de iniciar otra.')
            self.jobs.clear();ident=secrets.token_urlsafe(18)
            job={'id':ident,'done':False,'cancelled':False,'error':'','audio':None,'process':None,'cancel':threading.Event(),'message':'Preparando la voz de Emma…'};self.jobs[ident]=job
        threading.Thread(target=self.run,args=(job,text,command),daemon=True).start()
        return {'id':ident}

    def get(self,ident):
        with self.lock:
            if ident not in self.jobs:raise FileNotFoundError('La lectura ya no está disponible.')
            return self.jobs[ident]

    def snapshot(self,ident):
        with self.lock:
            job=self.get(ident)
            return {k:job[k] for k in ('id','done','cancelled','error','message')}

    def audio(self,ident):
        with self.lock:
            job=self.get(ident)
            if not job['done'] or job['cancelled'] or not job['audio']:raise FileNotFoundError('La voz todavía no está lista.')
            return job['audio']

    def cancel(self,ident):
        with self.lock:
            job=self.get(ident);job['cancel'].set();job['cancelled']=True;job['audio']=None
        return {'cancelled':True}

    def run(self,job,text,command):
        process=None;chunks=[];rate=None
        try:
            process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            job['process']=process;events=queue.Queue()
            def read():
                try:
                    for line in process.stdout:
                        if len(line)>20000000:break
                        try:events.put(json.loads(line))
                        except ValueError:pass
                finally:events.put({'type':'exit'})
            threading.Thread(target=read,daemon=True).start();deadline=time.monotonic()+210;size=0
            while not job['cancel'].is_set():
                if time.monotonic()>deadline:raise ValueError('Emma tardó demasiado en preparar esta lectura.')
                try:item=events.get(timeout=.1)
                except queue.Empty:continue
                kind=item.get('type')
                if kind=='ready':
                    process.stdin.write(json.dumps({'text':text},ensure_ascii=False)+'\n');process.stdin.flush();job['message']='Generando la voz de Emma…'
                elif kind=='audio':
                    current=item.get('sampleRate');pcm=base64.b64decode(item['pcm'],validate=True)
                    if current not in (24000,44100,48000) or rate and current!=rate or len(pcm)%2:raise ValueError('Emma devolvió audio con un formato inesperado.')
                    rate=current;size+=len(pcm)
                    if size>24_000_000:raise ValueError('La lectura supera el límite de audio de esta sesión.')
                    chunks.append(pcm)
                elif kind=='done':
                    if not chunks:raise ValueError('Emma no ha generado audio.')
                    audio=io.BytesIO()
                    with wave.open(audio,'wb') as wav:wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(b''.join(chunks))
                    with self.lock:
                        if not job['cancel'].is_set():job['audio']=audio.getvalue();job['message']='Voz de Emma lista'
                    break
                elif kind=='error':raise ValueError(ERRORS.get(item.get('message'),item.get('message','La voz no pudo generarse.')))
                elif kind=='exit':raise ValueError('El motor de Emma terminó antes de generar la voz.')
        except (ValueError,OSError) as error:job['error']=str(error)
        finally:
            if process:
                if process.poll() is None:
                    try:process.stdin.write('{"cancel":true}\n');process.stdin.flush();process.wait(timeout=4)
                    except (OSError,subprocess.TimeoutExpired):
                        if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=8,creationflags=subprocess.CREATE_NO_WINDOW)
                        else:process.kill()
                process.stdin.close();process.stdout.close()
            job['process']=None;job['done']=True;job['message']='Lectura detenida' if job['cancelled'] else job['message']

    def stop(self):
        with self.lock:
            for job in self.jobs.values():self.cancel(job['id'])

    def shutdown(self):self.closed=True;self.stop()
