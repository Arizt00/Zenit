"""Host a real QEMU serial socket in the IDE PTY, preserving pasted commands.

Windows QEMU stdio can discard a burst of characters in its console input
driver. A local TCP chardev applies QEMU's input backpressure instead.
"""
import ctypes
import os
import socket
import subprocess
import sys
import threading
import json,re,tempfile,time
from pathlib import Path

def console_milestones(text):
    # Bash also emits OSC window titles, not just CSI colour sequences. They
    # must not hide a real prompt or be mistaken for that prompt themselves.
    clean=re.sub(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)','',text)
    clean=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',clean)
    result=[]
    if 'Linux version ' in clean:result.append(('kernel-output',None))
    if re.search(r'(?:^|[\r\n])[^\r\n]{0,80}login:\s*$',clean):result.append(('login-prompt','login-prompt'))
    if re.search(r'(?:^|[\r\n])[^\r\n]{0,80}zenit@zenit-arch[^\r\n]{0,80}[$#]\s*$',clean):result.append(('shell-prompt','shell-ready'))
    return result

def main():
    argv=sys.argv[1:]
    metrics=None;origin=time.perf_counter()
    if argv[:1]==['--metrics']:
        metrics=Path(argv[1]);origin=float(argv[3]);argv=argv[4:]
    if not argv or '--serial-placeholder' not in argv:raise ValueError('Missing machine arguments')
    measurements={'schema':1,'state':'starting','phases':[]};seen=set();tail=''
    def mark(name,state=None):
        if name in seen:return
        seen.add(name);measurements['phases'].append({'name':name,'ms':round((time.perf_counter()-origin)*1000,3)})
        if state:measurements['state']=state
        if metrics:
            temporary=None
            try:
                fd,temporary=tempfile.mkstemp(prefix='.boot-',dir=metrics.parent)
                with os.fdopen(fd,'w',encoding='utf-8') as output:json.dump(measurements,output);output.flush()
                os.chmod(temporary,0o600);os.replace(temporary,metrics)
            except OSError:pass
            finally:
                if temporary and os.path.exists(temporary):os.unlink(temporary)
    mark('worker-started')
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(.25)
    port=listener.getsockname()[1];argv[argv.index('--serial-placeholder')]=f'tcp:127.0.0.1:{port}'
    process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                             creationflags=0x08000000 if os.name=='nt' else 0)
    mark('qemu-spawned')
    def diagnostics():
        while data:=process.stdout.read1(4096):sys.stdout.buffer.write(data);sys.stdout.buffer.flush()
    threading.Thread(target=diagnostics,daemon=True).start();connection=None;original=None
    try:
        while process.poll() is None:
            try:connection,_=listener.accept();break
            except socket.timeout:continue
        if connection is None:return process.returncode or 1
        mark('serial-connected','booting')
        connection.settimeout(None);connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        if os.name=='nt':
            from ctypes import wintypes
            kernel=ctypes.windll.kernel32
            kernel.GetStdHandle.restype=wintypes.HANDLE
            kernel.GetConsoleMode.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
            kernel.SetConsoleMode.argtypes=[wintypes.HANDLE,wintypes.DWORD]
            handle=kernel.GetStdHandle(-10);mode=wintypes.DWORD()
            if kernel.GetConsoleMode(handle,ctypes.byref(mode)):
                original=(handle,mode.value);kernel.SetConsoleMode(handle,(mode.value&~7)|0x200)
        else:
            import termios,tty
            original=termios.tcgetattr(sys.stdin.fileno());tty.setraw(sys.stdin.fileno())
        def input_reader():
            try:
                while data:=os.read(sys.stdin.fileno(),4096):connection.sendall(data)
            except OSError:pass
        threading.Thread(target=input_reader,daemon=True).start()
        while data:=connection.recv(16384):
            mark('first-output')
            tail=(tail+data.decode('utf-8','replace'))[-4096:]
            for name,state in console_milestones(tail):mark(name,state)
            sys.stdout.buffer.write(data);sys.stdout.buffer.flush()
        return process.wait(timeout=10)
    finally:
        mark('console-closed','closed')
        if connection:connection.close()
        listener.close()
        if original is not None:
            if os.name=='nt':ctypes.windll.kernel32.SetConsoleMode(*original)
            else:termios.tcsetattr(sys.stdin.fileno(),termios.TCSADRAIN,original)
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill()
        process.stdout.close()

if __name__=='__main__':raise SystemExit(main())
