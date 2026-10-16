#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 L4CE (Arizt00).
"""Independent JSON-in/JSON-out CPU laboratory, distributed with its source.

Uses the real LLVM assembler/linker and Unicorn CPU emulation. It deliberately
does not emulate an operating system or execute guest syscalls on the host.
"""
import io
import json
import re
import struct
from pathlib import Path
import subprocess
import sys
import tempfile

def build_nasm(request,folder,source):
    arch=request['architecture'];system=request['system'];bits=64 if arch=='x86_64' else 32
    declared=re.search(r'(?im)^\s*\[?bits\s+(16|32|64)\b',source)
    if declared and int(declared.group(1))!=bits:raise ValueError('BITS no coincide con la arquitectura seleccionada en el laboratorio.')
    fmt=('win' if system=='windows' else 'elf')+str(bits)
    labels=re.findall(r'(?im)^\s*([A-Za-z_][\w$@]*)\s*:',source)
    entry=next((name for name in ('_start','main','_main','start') if name in labels),None)
    if not entry:
        entry='__zenit_entry';source='global '+entry+'\nsection .text\n'+entry+':\n'+source
    file=folder/'buffer.asm';obj=folder/'buffer.obj';image=folder/('buffer.exe' if system=='windows' else 'buffer.elf')
    file.write_text(source,encoding='utf-8')
    commands=[[request['nasm'],'-f',fmt,'-I',request.get('includeRoot',str(folder))+'/',str(file),'-o',str(obj)]]
    if system=='windows':
        symbol=entry.removeprefix('_') if bits==32 else entry
        commands.append([request['linker'],'/machine:'+('x64' if bits==64 else 'x86'),'/subsystem:console','/nodefaultlib','/fixed','/base:0x10000','/entry:'+symbol,'/out:'+str(image),str(obj)])
    else:commands.append([request['linker'],'-m','elf_x86_64' if bits==64 else 'elf_i386','--image-base=0x10000','-Ttext=0x100000','--entry='+entry,str(obj),'-o',str(image)])
    for argv in commands:
        result=subprocess.run(argv,capture_output=True,timeout=15,creationflags=0x08000000 if sys.platform=='win32' else 0)
        if result.returncode:
            message=result.stderr.decode('utf-8','replace').replace(str(folder),'<búfer>')[:12000]
            if system=='windows' and 'undefined symbol' in message:message+='\nEste laboratorio simula instrucciones de CPU. Las funciones de DLL/WinAPI externas requieren un proceso Windows real o una VM.'
            raise ValueError(message)
        if any(p.exists() and p.stat().st_size>4*1024*1024 for p in (obj,image)):raise ValueError('El objeto o la imagen NASM supera los 4 MiB del laboratorio.')
    return image.read_bytes(),fmt

def pe_segments(raw,bits):
    """Read the bounded, fixed PE image emitted by our own lld-link invocation."""
    pe=struct.unpack_from('<I',raw,0x3c)[0]
    if raw[:2]!=b'MZ' or raw[pe:pe+4]!=b'PE\0\0':raise ValueError('Imagen PE no válida.')
    coff=pe+4;machine,count=struct.unpack_from('<HH',raw,coff);size=struct.unpack_from('<H',raw,coff+16)[0];opt=coff+20
    if count>64 or machine!=(0x8664 if bits==64 else 0x14c):raise ValueError('La imagen PE no coincide con la arquitectura.')
    magic=struct.unpack_from('<H',raw,opt)[0]
    if magic!=(0x20b if bits==64 else 0x10b):raise ValueError('Formato PE no válido.')
    base=struct.unpack_from('<Q' if bits==64 else '<I',raw,opt+(24 if bits==64 else 28))[0]
    entry=base+struct.unpack_from('<I',raw,opt+16)[0]
    length,headers=struct.unpack_from('<II',raw,opt+56)
    segments=[(base,length,raw[:headers])];text=None
    for n in range(count):
        offset=opt+size+n*40;name=raw[offset:offset+8].rstrip(b'\0');virtual,rva,amount,pointer=struct.unpack_from('<IIII',raw,offset+8)
        if pointer+amount>len(raw) or rva+max(virtual,amount)>length:raise ValueError('Sección PE fuera de los límites.')
        segments.append((base+rva,max(virtual,amount),raw[pointer:pointer+amount]))
        if name==b'.text':text=(base+rva,raw[pointer:pointer+min(virtual,amount)])
    if not text or not text[0]<=entry<text[0]+len(text[1]):raise ValueError('El punto de entrada debe estar en .text.')
    return entry,text,segments

def simulate(request):
    from elftools.elf.elffile import ELFFile
    import unicorn as u
    import capstone as c
    from unicorn import x86_const as x, arm_const as a, arm64_const as aa, riscv_const as r, mips_const as m
    definitions={
        'x86':('i386-none-elf',u.UC_ARCH_X86,u.UC_MODE_32,c.CS_ARCH_X86,c.CS_MODE_32,x.UC_X86_REG_EIP,x.UC_X86_REG_ESP,
               {name:getattr(x,'UC_X86_REG_'+name.upper()) for name in ('eax','ebx','ecx','edx','esi','edi','esp','ebp')}),
        'x86_64':('x86_64-none-elf',u.UC_ARCH_X86,u.UC_MODE_64,c.CS_ARCH_X86,c.CS_MODE_64,x.UC_X86_REG_RIP,x.UC_X86_REG_RSP,
                  {name:getattr(x,'UC_X86_REG_'+name.upper()) for name in ('rax','rbx','rcx','rdx','rsi','rdi','rsp','rbp','r8','r9')}),
        'arm':('armv7-none-eabi',u.UC_ARCH_ARM,u.UC_MODE_ARM,c.CS_ARCH_ARM,c.CS_MODE_ARM,a.UC_ARM_REG_PC,a.UC_ARM_REG_SP,
               {**{'r'+str(i):getattr(a,'UC_ARM_REG_R'+str(i)) for i in range(13)},'sp':a.UC_ARM_REG_SP,'lr':a.UC_ARM_REG_LR}),
        'arm64':('aarch64-none-elf',u.UC_ARCH_ARM64,u.UC_MODE_ARM,c.CS_ARCH_ARM64,c.CS_MODE_ARM,aa.UC_ARM64_REG_PC,aa.UC_ARM64_REG_SP,
                 {**{'x'+str(i):getattr(aa,'UC_ARM64_REG_X'+str(i)) for i in range(16)},'sp':aa.UC_ARM64_REG_SP}),
        'mips':('mipsel-none-elf',u.UC_ARCH_MIPS,u.UC_MODE_MIPS32,c.CS_ARCH_MIPS,c.CS_MODE_MIPS32|c.CS_MODE_LITTLE_ENDIAN,m.UC_MIPS_REG_PC,m.UC_MIPS_REG_SP,
                {name:getattr(m,'UC_MIPS_REG_'+name.upper()) for name in ('v0','v1','a0','a1','sp','t0','t1','t2','s0','s1','ra')}),
        'riscv32':('riscv32-none-elf',u.UC_ARCH_RISCV,u.UC_MODE_RISCV32,c.CS_ARCH_RISCV,c.CS_MODE_RISCV32,r.UC_RISCV_REG_PC,r.UC_RISCV_REG_SP,
                   {name:getattr(r,'UC_RISCV_REG_'+name.upper()) for name in ('ra','sp','t0','t1','t2','s0','s1','a0','a1','a2')}),
        'riscv64':('riscv64-none-elf',u.UC_ARCH_RISCV,u.UC_MODE_RISCV64,c.CS_ARCH_RISCV,c.CS_MODE_RISCV64,r.UC_RISCV_REG_PC,r.UC_RISCV_REG_SP,
                   {name:getattr(r,'UC_RISCV_REG_'+name.upper()) for name in ('ra','sp','t0','t1','t2','s0','s1','a0','a1','a2')})}
    architecture=request.get('architecture')
    if architecture not in definitions:raise ValueError('Arquitectura desconocida.')
    source=request.get('source')
    if not isinstance(source,str) or len(source.encode())>131072:raise ValueError('ASM admite hasta 128 KiB.')
    steps=request.get('steps',100)
    if type(steps) is not int or not 1<=steps<=10000:raise ValueError('Usa entre 1 y 10.000 instrucciones.')
    triple,arch,mode,csarch,csmode,pc,sp,registers=definitions[architecture]
    with tempfile.TemporaryDirectory(prefix='zenit-asm-') as folder:
        folder=Path(folder);file=folder/'buffer.s';obj=folder/'buffer.o';image=folder/'buffer.elf'
        nasm=request.get('engine')=='nasm';fmt='';system=request.get('system')
        if nasm:raw,fmt=build_nasm(request,folder,source)
        else:
            file.write_text(source,encoding='utf-8')
            flags=['-march=rv64im'] if architecture=='riscv64' else ['-march=rv32im'] if architecture=='riscv32' else ['-mno-abicalls','-fno-pic'] if architecture=='mips' else []
            for argv in ([request['clang'],'-target',triple,*flags,'-c',str(file),'-o',str(obj)],
                     [request['linker'],'--image-base=0x10000','-Ttext=0x100000','--entry=0x100000',str(obj),'-o',str(image)]):
                result=subprocess.run(argv,capture_output=True,timeout=15,creationflags=0x08000000 if sys.platform=='win32' else 0)
                if result.returncode:raise ValueError(result.stderr.decode('utf-8','replace').replace(str(folder),'<búfer>')[:12000])
            raw=image.read_bytes()
        if nasm and system=='windows':entry,(start,text),segments=pe_segments(raw,64 if architecture=='x86_64' else 32)
        else:
            elf=ELFFile(io.BytesIO(raw));section=elf.get_section_by_name('.text')
            if not section or not section.data():raise ValueError('No hay instrucciones en .text.')
            start=section['sh_addr'];text=section.data();entry=elf.header['e_entry']
            segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
        end=start+len(text);cpu=u.Uc(arch,mode);pages=set()
        for lo,length,data in segments:
            if length>4*1024*1024 or lo<0x10000 or lo+length>0x200000:raise ValueError('La imagen excede la memoria del laboratorio.')
            for page in range(lo&~4095,(lo+length+4095)&~4095,4096):
                if page not in pages:cpu.mem_map(page,4096);pages.add(page)
            cpu.mem_write(lo,data)
        cpu.mem_map(0x200000,65536);stack=0x20ffe8 if architecture=='x86_64' else 0x20fff0;cpu.reg_write(sp,stack)
        if nasm:cpu.mem_write(stack,end.to_bytes(8 if architecture=='x86_64' else 4,'little'))
        disassembler=c.Cs(csarch,csmode);instructions=[];trace=[];count=0
        for instruction in disassembler.disasm(text,start):
            instructions.append({'address':hex(instruction.address),'bytes':instruction.bytes.hex(' '),'text':instruction.mnemonic+' '+instruction.op_str})
            if len(instructions)>=2000:break
        def hook(engine,address,size,_):
            nonlocal count
            count+=1
            if len(trace)<256:trace.append({'address':hex(address),'registers':{name:hex(engine.reg_read(reg)) for name,reg in registers.items()}})
        cpu.hook_add(u.UC_HOOK_CODE,hook)
        fault='';exited=False;exit_code=None;output=bytearray()
        def linux_call(engine,*_):
            nonlocal fault,exited,exit_code
            wide=architecture=='x86_64';reg=lambda name:engine.reg_read(registers[name])
            call=reg('rax' if wide else 'eax');args=[reg(n) for n in (('rdi','rsi','rdx') if wide else ('ebx','ecx','edx'))]
            if call==(60 if wide else 1):exited=True;exit_code=args[0]&255;engine.emu_stop()
            elif call==(1 if wide else 4):
                if args[0] not in (1,2) or args[2]>65536 or len(output)+args[2]>65536:fault='write simulado admite stdout/stderr y hasta 64 KiB.';engine.emu_stop();return
                output.extend(engine.mem_read(args[1],args[2]));engine.reg_write(registers['rax' if wide else 'eax'],args[2])
            else:fault='Servicio Linux '+str(call)+' no implementado en el laboratorio. Usa Linux/WSL o una VM para un sistema completo.';engine.emu_stop()
        if nasm and system=='linux':
            if architecture=='x86_64':cpu.hook_add(u.UC_HOOK_INSN,linux_call,None,1,0,x.UC_X86_INS_SYSCALL)
            else:
                def interrupt(engine,number,_):
                    nonlocal fault
                    if number==0x80:linux_call(engine)
                    else:fault='Interrupción no implementada: '+str(number);engine.emu_stop()
                cpu.hook_add(u.UC_HOOK_INTR,interrupt)
        elif nasm:
            def unsupported(engine,*_):
                nonlocal fault
                fault='Las llamadas al kernel no se simulan para Windows. Ejecuta este programa en una estación o VM Windows.';engine.emu_stop()
            if architecture=='x86_64':cpu.hook_add(u.UC_HOOK_INSN,unsupported,None,1,0,x.UC_X86_INS_SYSCALL)
            cpu.hook_add(u.UC_HOOK_INTR,unsupported)
        try:cpu.emu_start(entry,end,timeout=1_000_000,count=steps)
        except u.UcError as exc:fault=str(exc)
        position=cpu.reg_read(pc)
        return {'architecture':architecture,'instructions':instructions,'trace':trace,'executed':count,'pc':hex(position),
                'registers':{name:hex(cpu.reg_read(reg)) for name,reg in registers.items()},'memory':cpu.mem_read(0x20ffc0,64).hex(' '),
                'status':'fault' if fault else 'complete' if exited or position==end else 'paused','error':fault,
                **({'system':system,'format':fmt,'exitCode':exit_code if exited else (cpu.reg_read(registers['rax' if architecture=='x86_64' else 'eax'])&0xffffffff if system=='windows' and position==end else None)} if nasm else {}),
                **({'output':output.decode('utf-8','replace')} if output else {}),
                'note':('NASM · '+fmt+' · CPU emulada. Linux: exit/write simulados; Windows: retorno de main. Sin kernel, DLL externas ni llamadas al anfitrión.' if nasm else 'CPU y memoria emuladas. Sin sistema operativo ni llamadas al sistema del anfitrión.')}

if __name__=='__main__':
    try:result=simulate(json.loads(sys.stdin.read(150000)))
    except Exception as exc:result={'status':'error','error':str(exc)}
    print(json.dumps(result,ensure_ascii=False))
