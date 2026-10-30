"""One console grammar routes every configured language through its real runtime."""
import shlex
from pathlib import Path,PurePosixPath

def dispatch(features,ws,body):
 command=body.get('command','');cwd=body.get('cwd','')
 if not isinstance(command,str) or len(command)>4096:raise ValueError('Comando no válido o demasiado largo.')
 lexer=shlex.shlex(command,posix=True);lexer.whitespace_split=True;lexer.commenters='';lexer.escape=''
 try:parts=list(lexer)
 except ValueError:raise ValueError('Revisa las comillas del comando.')
 if not parts or parts[0] not in ('run','build','check') or parts==['check']:return features.app.runner.console(ws,command,cwd)
 action=parts[0]
 if len(parts)<2:raise ValueError('Uso: '+action+' <archivo> [-- argumentos]')
 directory=ws.resolve(cwd)
 if not directory.is_dir():raise ValueError('El directorio de trabajo no es una carpeta.')
 target=ws.resolve(str(PurePosixPath(directory.relative_to(ws.root).as_posix())/parts[1].replace('\\','/'))).relative_to(ws.root).as_posix()
 args=parts[2:];args=args[1:] if args[:1]==['--'] else args
 if len(args)>128 or action!='run' and args:raise ValueError('Solo run admite argumentos del programa, hasta 128.')
 plan=features.runtimes.plan(ws,target,check=action=='check',build_only=action=='build')
 if plan.get('preview'):
  if args or action=='build':raise ValueError('La vista web no admite argumentos ni compilación por consola.')
  return {'preview':features.preview.start(ws,target),'path':target}
 commands=plan['commands']
 if action=='build' and not plan.get('buildOnly'):
  if plan.get('executionTarget') or len(commands)<2:raise ValueError('Este adaptador no ofrece compilación separada. Configura build en SDK y lenguajes.')
  commands=commands[:-1]
 if args:
  if plan.get('executionTarget'):raise ValueError('Los argumentos desde esta consola requieren Este equipo; configura los argumentos remotos en su tarea.')
  commands=[*commands[:-1],[*commands[-1],*args]]
 if not commands:return {'path':target,'output':'Comprobación completada.\n'}
 return {**features.app.runner.start(commands,Path(plan.get('cwd',ws.root)),timeout=120 if action!='run' else 0),
  'path':target,'language':plan['language'],'action':action,'target':plan.get('executionTarget','local')}
