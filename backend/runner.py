"""Explicit local task execution. This is a command console, not a PTY."""
from __future__ import annotations
import ast
import hashlib
import os
import platform
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from .workspace import Workspace
from .terminals import child_environment


@dataclass
class Job:
    id: str
    commands: list
    cwd: Path
    shell: bool = False
    output: str = ""
    done: bool = False
    code: int | None = None
    process: object = None
    cancelled: bool = False
    timeout: float = 120
    stop_on_output_limit: bool = True
    extra_env: dict = field(default_factory=dict)
    input_text: str | None = None
    close_input: bool = False
    stream_output: str = ""
    stream_sha256: str = ""
    stream_bytes: int = 0
    stream_complete: bool = False
    command_index: int = -1
    elapsed: float = 0
    lock: threading.RLock = field(default_factory=threading.RLock)

    def append(self, text: str):
        with self.lock:
            if not self.stop_on_output_limit:
                self.output=(self.output+text)[-512_000:]
                return
            available = 512_000 - len(self.output)
            if available > 0:
                self.output += text[:available]

    def cancel(self):
        self.cancelled = True
        governor=getattr(self,'governor',None)
        if governor:governor.cancel_tree(self.id)
        if getattr(self,'queued',False) and self.process is None:self.code=-1;self.done=True
        p = self.process
        if p and p.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    os.killpg(p.pid, signal.SIGKILL)
            except (OSError, subprocess.SubprocessError):
                p.kill()

    def write(self,text):
        if not isinstance(text,str) or len(text)>65536:raise ValueError('Entrada demasiado larga.')
        with self.lock:
            if self.done or not self.process or self.process.poll() is not None:raise ValueError('No hay un programa esperando entrada.')
            try:self.process.stdin.write(text.encode('utf-8'));self.process.stdin.flush()
            except (OSError,ValueError) as exc:raise ValueError('El programa ha cerrado su entrada.') from exc

    def environment(self):
        env=child_environment();folders=[]
        for command in self.commands:
            if isinstance(command,list) and command and Path(command[0]).is_absolute():folders.append(str(Path(command[0]).parent))
        env['PATH']=os.pathsep.join(dict.fromkeys(folders))+os.pathsep+env.get('PATH','')
        env.update(self.extra_env)
        if getattr(self,'governor',None):
            for key,value in self.governor.environment().items():env.setdefault(key,value)
        return env

    def finish_input(self):
        with self.lock:
            if self.done or not self.process:raise ValueError('No hay un programa activo.')
            try:
                if not self.process.stdin.closed:self.process.stdin.close()
            except (OSError,ValueError):pass

    def run(self):
        started = time.monotonic()
        reuse=getattr(self.commands,'build_reuse',None);reuse_locked=False;self.reusedBuild=False
        try:
            for index,command in enumerate(self.commands):
                if self.cancelled:
                    break
                cache=reuse if index==0 else None
                if cache:
                    while not self.cancelled:
                        if cache.lock.acquire(timeout=.1):reuse_locked=True;break
                    if self.cancelled:break
                    if cache.hit(self.environment()):
                        self.reusedBuild=True;self.code=0;self.append('Compilación reutilizada: entradas y artefactos verificados.\n');cache.lock.release();reuse_locked=False;continue
                shown = command if isinstance(command, str) else shlex.join(command)
                self.append(f"$ {shown}\n")
                opts = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
                self.process = subprocess.Popen(command, cwd=self.cwd, shell=self.shell,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, env=self.environment(), **opts)
                if getattr(self,'governor',None):self.governor.attach(self)
                self.command_index=index
                if getattr(self,'on_process',None):
                    try:self.on_process(self)
                    except Exception as error:
                        self.cancel()
                        raise OSError('No se pudo confirmar el proceso en el registro de recuperación.') from error
                if self.cancelled:self.cancel()
                stream = self.process.stdout
                self.stream_output = ""
                self.stream_sha256 = hashlib.sha256().hexdigest();self.stream_bytes=0;self.stream_complete=False
                command_started = time.monotonic()
                def read_output(stream=stream,cache=cache):
                    import codecs
                    decoder = codecs.getincrementaldecoder("utf-8")("replace");pending=''
                    hasher=hashlib.sha256()
                    def raw(text):
                        value=text.encode('utf-8');hasher.update(value)
                        self.stream_output=(self.stream_output+text)[-512_000:]
                        self.stream_sha256=hasher.hexdigest();self.stream_bytes+=len(value)
                    with stream:
                        while True:
                            chunk = stream.read1(4096)
                            if not chunk:
                                tail=decoder.decode(b"", final=True);self.append(cache.output(pending+tail) if cache else tail)
                                raw(tail);self.stream_complete=True
                                break
                            text=decoder.decode(chunk)
                            raw(text)
                            if cache:
                                pending+=text
                                while '\n' in pending:
                                    line,pending=pending.split('\n',1);self.append(cache.output(line+'\n'))
                            else:self.append(text)
                reader = threading.Thread(target=read_output, daemon=True)
                reader.start()
                if index==len(self.commands)-1 and (self.input_text is not None or self.close_input):
                    def feed(process=self.process):
                        try:
                            if self.input_text is not None:process.stdin.write(self.input_text.encode('utf-8'));process.stdin.flush()
                            if self.close_input:process.stdin.close()
                        except (OSError,ValueError):pass
                    threading.Thread(target=feed,daemon=True).start()
                while self.process.poll() is None:
                    if self.timeout and time.monotonic() - started > self.timeout:
                        self.append(f"\nTime limit reached ({self.timeout:g} s).\n")
                        self.cancel()
                    if self.stop_on_output_limit and len(self.output) >= 512_000:
                        self.cancel()
                    time.sleep(0.05)
                self.code = self.process.wait()
                self.elapsed=time.monotonic()-command_started
                try:
                    if not self.process.stdin.closed:self.process.stdin.close()
                except (OSError,ValueError):pass
                reader.join(timeout=2)
                if cache:
                    if not self.code and not self.cancelled:cache.save(self.environment())
                    cache.lock.release();reuse_locked=False
                if self.code:
                    break
            if self.cancelled:
                self.code = -1
                self.append("\nTask stopped.\n")
            else:
                self.append(f"\nProcess exited with code {self.code or 0} · {time.monotonic() - started:.2f}s\n")
        except (OSError, subprocess.SubprocessError) as exc:
            self.code = -1
            self.append(f"\nCannot run task: {exc}\n")
        finally:
            if reuse_locked:reuse.lock.release()
            self.done = True


class Runner:
    def __init__(self, allow_shell=False):
        self.allow_shell = allow_shell
        self.jobs: dict[str, Job] = {}
        self.lock = threading.RLock()
        self.parallelism = max(1,min(4,(os.cpu_count() or 2)//2))
        self.pool = ThreadPoolExecutor(max_workers=self.parallelism,thread_name_prefix='zenit-run')
        self.closing = False

    def start(self, commands: list, cwd: Path, shell=False, timeout=120, env=None, stop_on_output_limit=True, scheduler=None, stdin=None, close_stdin=False, on_created=None, on_finished=None, on_process=None, resource_class='foreground') -> dict:
        if scheduler and (on_created or on_finished or on_process):raise ValueError('Los observadores duraderos requieren el ejecutor de primer plano.')
        if stdin is not None and (not isinstance(stdin,str) or len(stdin.encode('utf-8'))>65536):raise ValueError('La entrada preparada admite hasta 64 KiB.')
        with self.lock:
            if self.closing:raise ValueError('El ejecutor se está cerrando.')
            if not scheduler and sum(not j.done and not getattr(j,'background',False) for j in self.jobs.values()) >= self.parallelism+16:
                raise ValueError('La cola de ejecución está llena. Espera o detén una tarea.')
            if len(self.jobs) > 40:
                for old in [k for k, v in self.jobs.items() if v.done][:-20]:
                    del self.jobs[old]
            job = Job(uuid.uuid4().hex, commands, cwd, shell)
            job.background=bool(scheduler)
            job.resource_class='background' if scheduler or resource_class=='background' else 'foreground';job.governor=getattr(self,'governor',None)
            job.timeout = timeout
            job.stop_on_output_limit = stop_on_output_limit
            job.extra_env = dict(env or {})
            job.input_text=stdin;job.close_input=bool(close_stdin)
            job.on_process=on_process
            self.jobs[job.id] = job
        # A durable caller reserves the identity before any worker can spawn.
        try:
            if on_created:on_created(job)
        except BaseException:
            with self.lock:self.jobs.pop(job.id,None)
            raise
        if scheduler:
            try: scheduler.schedule_process(job)
            except Exception:
                self.jobs.pop(job.id,None)
                raise
        else:
            job.queued = True
            def execute():
                job.queued = False
                try:job.run()
                finally:
                    if on_finished:
                        try:on_finished(job)
                        except Exception as error:job.persistence_error=str(error)
            self.pool.submit(execute)
        return {"job": job.id,"queued":getattr(job,'queued',False)}

    def snapshot(self):
        with self.lock:return {'parallelism':self.parallelism,'queueLimit':16,'running':sum(not j.done and not getattr(j,'background',False) and not getattr(j,'queued',False) for j in self.jobs.values()),'queued':sum(not j.done and not getattr(j,'background',False) and getattr(j,'queued',False) for j in self.jobs.values()),'retained':len(self.jobs)}

    def task(self, ws: Workspace, name: str, *, check=False) -> dict:
        if not ws.trusted:
            raise PermissionError("Confirma que confías en este proyecto antes de ejecutar código local.")
        path = ws.resolve(name)
        suffix = path.suffix.lower()
        if suffix == ".py":
            if check:
                ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
                return {"output": "Python syntax check passed.\n"}
            commands = [[sys.executable, "--python-child", str(path)]] if getattr(sys,"frozen",False) else [[sys.executable, "-u", str(path)]]
        elif suffix in (".js", ".mjs", ".cjs"):
            if not shutil.which("node"):
                raise ValueError("Node.js no está instalado o no está en PATH.")
            commands = [["node", *(["--check"] if check else []), str(path)]]
        elif suffix in (".c", ".cpp", ".cc", ".cxx", ".s"):
            cxx = suffix in (".cpp", ".cc", ".cxx")
            compiler = shutil.which("g++" if cxx else "gcc")
            if not compiler:
                raise ValueError("No se encuentra g++/gcc. Instala una toolchain o usa WSL con build-essential.")
            if suffix == ".s" and not (sys.platform.startswith("linux") and platform.machine().lower() in ("x86_64", "amd64")):
                raise ValueError("El ejemplo ASM incluido requiere Linux/WSL x86-64.")
            standard = ["-std=c++17"] if cxx else (["-std=c11"] if suffix == ".c" else [])
            if check and suffix != ".s":
                commands = [[compiler, *standard, "-Wall", "-Wextra", "-fsyntax-only", str(path)]]
            else:
                exe = ws.private_dir("run") / ("task_" + uuid.uuid4().hex + (".exe" if os.name == "nt" else ""))
                commands = [[compiler, *standard, "-Wall", "-Wextra", str(path), "-o", str(exe)]]
                if not check:
                    commands.append([str(exe)])
        else:
            raise ValueError("No hay un ejecutor configurado para este tipo. Los componentes C# necesitan Unity y no se ejecutan como programas independientes. Prueba Examples/hello.py.")
        return self.start(commands, ws.root)

    def git(self, ws: Workspace, mode="status") -> str:
        if not shutil.which("git"):
            return "Git no está instalado.\n"
        args = {"status": ["status", "--short", "--branch"], "diff": ["diff", "--no-ext-diff", "--no-textconv", "--stat"],
                "log": ["log", "-5", "--oneline", "--no-decorate"], "branch": ["branch", "--list"]}
        if mode not in args:
            raise ValueError("Operación Git no admitida.")
        result = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=" + os.devnull, "--no-pager", *args[mode]], cwd=ws.root, capture_output=True,
                                timeout=8, text=True, encoding="utf-8", errors="replace", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if result.returncode and "not a git repository" in result.stderr.lower():
            return "Este proyecto no es un repositorio Git. No se ha creado ni modificado ninguno.\n"
        return (result.stdout + result.stderr)[:100_000] or "No changes.\n"

    def console(self, ws: Workspace, command: str, cwd_name="") -> dict:
        if len(command) > 4096:
            raise ValueError("Comando demasiado largo.")
        cwd = ws.resolve(cwd_name)
        if not cwd.is_dir():
            raise ValueError("El directorio de trabajo no es una carpeta.")
        try:
            parts = shlex.split(command, posix=True)
        except ValueError as exc:
            raise ValueError("Revisa las comillas del comando.") from exc
        if not parts:
            return {"output": ""}
        name, args = parts[0], parts[1:]
        if name in ("help", "?"):
            return {"output": ("ZÉNIT · consola del proyecto\n"
                "help · pwd · ls [path] · cd [path] · cat <file>\n"
                "check · check <file> · build <file> · run <file> [-- argumentos] · stats <file> · clear\n"
                "git status | diff | log | branch · version\n"
                "Durante una ejecución: escribe la entrada o :eof para cerrarla.\n"
                "Las herramientas de cada lenguaje deben estar instaladas o configuradas.\n"
                "Autoriza el proyecto antes de ejecutar programas.\n"
                + ("La shell sin restricciones está habilitada en esta sesión.\n" if self.allow_shell else "Los operadores de shell y las órdenes arbitrarias están deshabilitados.\n"))}
        if name == "clear":
            return {"clear": True, "output": ""}
        if name == "pwd":
            return {"output": str(cwd) + "\n"}
        if name in ("ls", "dir"):
            target = ws.resolve(str(cwd.relative_to(ws.root) / (args[0] if args else ".")))
            if not target.is_dir():
                raise ValueError("ls necesita una carpeta.")
            children = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            return {"output": "\n".join(p.name + ("/" if p.is_dir() else "") for p in children if not p.is_symlink()) + "\n"}
        if name == "cd":
            target = ws.resolve(str(cwd.relative_to(ws.root) / (args[0] if args else ".")))
            if not target.is_dir():
                raise ValueError("La ruta no es una carpeta.")
            return {"cwd": target.relative_to(ws.root).as_posix(), "output": ""}
        if name in ("cat", "stats", "run"):
            if len(args) != 1:
                raise ValueError(f"Uso: {name} <archivo>")
            relative = str(cwd.relative_to(ws.root) / args[0])
            if name == "run":
                return self.task(ws, relative)
            result = ws.read(relative)
            if name == "cat":
                return {"output": result["content"] + "\n"}
            import json
            return {"output": json.dumps(result["stats"], ensure_ascii=False, indent=2) + "\n"}
        if name == "check":
            return {"output": ws.check()}
        if name == "version":
            from .version import VERSION,REVISION
            return {"output": f"Zénit {VERSION} R{REVISION}\nPython {platform.python_version()}\n{ws.native.name}\n"}
        if name == "git" and len(args) == 1 and args[0] in ("status", "diff", "log", "branch"):
            return {"output": self.git(ws, args[0])}
        if self.allow_shell and ws.trusted:
            return self.start([command], cwd, shell=True)
        raise ValueError("Comando no habilitado. Escribe help. La consola no interpreta tuberías ni redirecciones en modo protegido.")

    def shutdown(self):
        self.closing=True
        for job in self.jobs.values():
            if not job.done:
                job.cancel()
        self.pool.shutdown(wait=True)
