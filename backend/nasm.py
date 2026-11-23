"""NASM syntax, object targets and small examples shared with the laboratory."""
import os
import re

def target_system(source, default=None):
    header=re.search(r'(?im)^\s*;\s*(?:sistema|system|os|target)\s*:\s*(linux|windows)\b',source)
    if header:return header.group(1).lower()
    # Linux entry points using its syscall ABI must never be linked as WinMain.
    if re.search(r'(?im)^\s*(?:syscall\b|int\s+(?:0x80|80h)\b)',source):return 'linux'
    return default or ('windows' if os.name=='nt' else 'linux')

EXAMPLES={
 'linux':{
  'x86_64':'; Sistema: Linux\n; Sintaxis: NASM\nglobal _start\nsection .text\n_start:\n    mov rax, 5\n    add rax, 3\n    mov rdi, rax\n    mov rax, 60\n    syscall\n',
  'x86':'; Sistema: Linux\nbits 32\nglobal _start\nsection .text\n_start:\n    mov eax, 5\n    add eax, 3\n    mov ebx, eax\n    mov eax, 1\n    int 0x80\n'},
 'windows':{
  'x86_64':'; Sistema: Windows\n; main devuelve el resultado al runtime de Windows\nglobal main\nsection .text\nmain:\n    mov eax, 5\n    add eax, 3\n    ret\n',
  'x86':'; Sistema: Windows\nbits 32\nglobal _main\nsection .text\n_main:\n    mov eax, 5\n    add eax, 3\n    ret\n'}}

ENGINE={'id':'nasm','label':'NASM + Unicorn · Linux / Windows','architectures':['x86','x86_64'],'step':True,
        'systems':['linux','windows'],
        'examples':{system:{arch:[{'label':'Suma 5 + 3 · '+system.title(),'source':source}] for arch,source in values.items()} for system,values in EXAMPLES.items()}}
