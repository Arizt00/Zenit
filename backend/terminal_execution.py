"""Run a reviewed runtime plan in one terminal, without typing into its shell.

The shell stays alive. A bounded, interactive PTY owns input during execution;
its output goes only to the selected terminal. Compiler phases stop on failure.
"""
import os
from pathlib import Path
import threading
import time
import uuid
from .terminals import TerminalSession


class TerminalExecution:
    def __init__(self, session, commands, cwd, project, path, target, environment=None):
        self.session=session;self.commands=commands;self.cwd=cwd;self.project=project
        self.environment=environment or {};self.cancelled=threading.Event();self.child=None;self.observed_output=''
        self.state={'id':uuid.uuid4().hex,'path':path,'target':target,'running':True,'code':None,'phase':0}
        self.thread=threading.Thread(target=self.run,name='zenit-terminal-execution',daemon=True)

    def start(self):self.thread.start()

    def run(self):
        s=self.session;code=None
        s._append('\r\n\x1b[36m▶ '+self.state['path']+' · '+self.state['target']+'\x1b[0m\r\n')
        try:
            from .foundation import tool_environment
            for index,argv in enumerate(self.commands):
                with s.lock:
                    if self.cancelled.is_set() or s.closed:break
                    env={**self.environment,'PYTHONUNBUFFERED':'1'}
                    env['PATH']=str(Path(argv[0]).parent)+os.pathsep+env.get('PATH',tool_environment()['PATH'])
                    self.child=TerminalSession({'id':'execution','label':self.state['path'],'argv':argv},self.cwd,self.project,environment=env,governor=getattr(s,'governor',None))
                    self.state['phase']=index+1
                offset=0;deadline=time.monotonic()+120 if index<len(self.commands)-1 else None
                while True:
                    child=self.child
                    if self.cancelled.is_set() or s.closed or deadline and time.monotonic()>deadline:
                        self.cancelled.set();child.close()
                    result=child.read(offset);offset=result['offset']
                    if result['data']:self.observed_output=(self.observed_output+result['data'])[-24000:];s._append(result['data'])
                    if result['closed']:
                        code=result['code'];break
                    self.cancelled.wait(.025) if not self.cancelled.is_set() else time.sleep(.025)
                if self.cancelled.is_set() or code!=0:break
        except Exception as error:
            code=1;s._append('\r\n'+str(error)+'\r\n')
        finally:
            with s.lock:
                self.child=None;self.state.update(running=False,code=code,cancelled=self.cancelled.is_set())
            s._append('\r\n\x1b[2m'+('Ejecución detenida' if self.cancelled.is_set() else 'Process exited with code '+str(code))+'\x1b[0m\r\n')

    def write(self,text):
        with self.session.lock:
            if not self.state['running']:return False
            if self.child and not self.child.closed:return self.child.write(text)
            return True  # Never leak program input into the retained shell.

    def stop(self):
        self.cancelled.set()
        with self.session.lock:child=self.child
        if child:child.close()


def start(features,ws,body):
    if not ws.trusted:raise PermissionError('Autoriza el proyecto para ejecutar su código.')
    if not features.prefs.get('security.terminals'):raise PermissionError('Las terminales están desactivadas.')
    session=features.terminals.get(body.get('id'))
    if session.profile.get('id','').startswith('extension:') or session.profile.get('id')=='hacker':
        raise ValueError('Selecciona una terminal de shell para ejecutar el archivo actual.')
    if Path(session.cwd).resolve()!=ws.root.resolve():raise ValueError('La terminal pertenece a otro proyecto. Abre una en este proyecto.')
    path=body.get('path','');execution_ws,path=features.execution_workspace(ws,path)
    args=body.get('args',[])
    if not isinstance(args,list) or len(args)>128 or any(not isinstance(x,str) or '\0' in x for x in args):raise ValueError('Argumentos no válidos.')
    with session.lock:
        if session.closed:raise ValueError('Esta terminal está cerrada. Abre otra.')
        old=getattr(session,'execution_channel',None)
        if old and old.state['running']:raise ValueError('Esta terminal ya está ejecutando un archivo. Deténlo o elige otra terminal.')
        plan=features.runtimes.plan(execution_ws,path)
        if plan.get('preview'):return {'preview':features.preview.start(execution_ws,path)}
        commands=[list(row) for row in plan.get('commands',[])]
        if not commands:raise ValueError('No hay una orden de ejecución para este archivo.')
        if args and plan.get('executionTarget'):
            raise ValueError('Configura los argumentos en el adaptador del destino remoto.')
        commands[-1].extend(args)
        target=plan.get('executionTarget') or features.execution.selected(ws)
        target=target.get('label',target.get('id','Este equipo')) if isinstance(target,dict) else str(target)
        channel=TerminalExecution(session,commands,plan.get('cwd',execution_ws.root),features.app.project,path,target,features.extension_services.environment(ws.root))
        channel.state['evidence']=features.investigations.capture_optional(execution_ws,commands)
        channel.state['args']=args
        session.execution_channel=channel;channel.start()
        return {'terminal':{'id':session.id,'profile':session.profile,'kind':session.kind},'execution':dict(channel.state),'artifacts':plan.get('artifacts')}
