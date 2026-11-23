"""Bounded ELF/PE section and symbol readers; no tool execution or whole-file loads."""
import struct
from .binary_view import revision

class Reader:
 def __init__(self,stream):self.stream=stream;self.size=stream.seek(0,2);self.budget=8000000
 def read(self,offset,count):
  if offset<0 or count<0 or offset+count>self.size or count>self.budget:raise ValueError('Tabla binaria fuera del archivo o del presupuesto de inspección.')
  self.budget-=count;self.stream.seek(offset);value=self.stream.read(count)
  if len(value)!=count:raise ValueError('El binario cambió durante su inspección.')
  return value
 def unpack(self,fmt,offset):return struct.unpack(fmt,self.read(offset,struct.calcsize(fmt)))
def string(data,index):
 if not 0<=index<len(data):return ''
 end=data.find(b'\0',index,min(len(data),index+1024));return data[index:end if end>=0 else min(len(data),index+1024)].decode('utf-8','replace')

def elf(r):
 ident=r.read(0,16)
 if ident[4] not in (1,2) or ident[5] not in (1,2):raise ValueError('Clase o orden ELF desconocido.')
 wide=ident[4]==2;endian='<' if ident[5]==1 else '>';header=r.unpack(endian+('HHIQQQIHHHHHH' if wide else 'HHIIIIIHHHHHH'),16);machine=header[1];offset=header[5];entrysize=header[10];count=header[11];namesindex=header[12];fmt=endian+('IIQQQQIIQQ' if wide else 'IIIIIIIIII');minimum=struct.calcsize(fmt)
 if count>4096 or entrysize<minimum or not count or namesindex>=count:raise ValueError('Tabla ELF extendida, ausente o demasiado grande para esta vista.')
 table=r.read(offset,entrysize*count);sections=[struct.unpack_from(fmt,table,i*entrysize) for i in range(count)];names=r.read(sections[namesindex][4],sections[namesindex][5]);rows=[];symbols=[];truncated=False
 for index,s in enumerate(sections):
  rows.append({'index':index,'name':string(names,s[0]),'type':s[1],'flags':hex(s[2]),'address':hex(s[3]),'offset':s[4],'size':s[5],'fileSize':0 if s[1]==8 else s[5]})
  if s[1] not in (2,11) or not s[9] or s[6]>=count:continue
  symfmt=endian+('IBBHQQ' if wide else 'IIIBBH');symsize=struct.calcsize(symfmt)
  if s[9]<symsize or s[5]%s[9]:raise ValueError('Tabla de símbolos ELF dañada.')
  strings=sections[s[6]];data=r.read(strings[4],strings[5]);available=s[5]//s[9];take=min(available,3000-len(symbols));raw=r.read(s[4],take*s[9]);truncated|=take<available
  for pos in range(take):
   values=struct.unpack_from(symfmt,raw,pos*s[9]);name,info,other,section,value,size=values if wide else (values[0],values[3],values[4],values[5],values[1],values[2]);label=string(data,name)
   if label:symbols.append({'name':label,'address':hex(value),'size':size,'section':section,'binding':info>>4,'type':info&15})
 return {'format':'ELF64' if wide else 'ELF32','architecture':{3:'x86',62:'x86-64',40:'ARM',183:'AArch64',243:'RISC-V',8:'MIPS'}.get(machine,str(machine)),'entry':hex(header[3]),'sections':rows,'symbols':symbols,'symbolsTruncated':truncated}

def pe(r):
 offset=r.unpack('<I',60)[0]
 if r.read(offset,4)!=b'PE\0\0':raise ValueError('La cabecera MZ no contiene un ejecutable PE.')
 machine,count,timestamp,symoffset,symcount,optional,flags=r.unpack('<HHIIIHH',offset+4)
 if not 0<count<=256 or optional>4096 or symcount>1000000:raise ValueError('Tablas PE fuera del presupuesto de inspección.')
 opt=r.read(offset+24,optional);magic=struct.unpack_from('<H',opt)[0] if len(opt)>=2 else 0;entry=struct.unpack_from('<I',opt,16)[0] if len(opt)>=20 else 0;rows=[]
 for index in range(count):
  s=r.unpack('<8sIIIIIIHHI',offset+24+optional+40*index);rows.append({'index':index+1,'name':s[0].split(b'\0')[0].decode('ascii','replace'),'address':hex(s[2]),'offset':s[4],'size':s[1],'fileSize':s[3],'flags':hex(s[9])})
 symbols=[];truncated=False
 if symoffset and symcount:
  length=r.unpack('<I',symoffset+symcount*18)[0]
  strings=r.read(symoffset+symcount*18,length);take=min(symcount,6000);raw=r.read(symoffset,take*18);index=0
  while index<take and len(symbols)<3000:
   name,value,section,kind,storage,aux=struct.unpack_from('<8sIhHBB',raw,index*18);label=string(strings,struct.unpack_from('<I',name,4)[0]) if name[:4]==b'\0'*4 else name.split(b'\0')[0].decode('utf-8','replace');symbols.append({'name':label,'address':hex(value),'section':section,'type':kind,'binding':storage});index+=1+aux
  truncated=index<symcount
 return {'format':'PE32+' if magic==0x20b else 'PE32','architecture':{0x14c:'x86',0x8664:'x86-64',0xaa64:'AArch64',0x1c4:'ARM'}.get(machine,hex(machine)),'entry':hex(entry),'sections':rows,'symbols':symbols,'symbolsTruncated':truncated}

def inspect(file,name):
 before=revision(file)
 with file.open('rb') as stream:
  r=Reader(stream);magic=r.read(0,min(4,r.size))
  data=elf(r) if magic==b'\x7fELF' else pe(r) if magic[:2]==b'MZ' else {'format':'Datos binarios','sections':[],'symbols':[],'message':'Este archivo no contiene tablas ELF o PE.'}
 if revision(file)!=before:raise ValueError('El archivo cambió durante la inspección.')
 return {**data,'path':name,'revision':before,'size':r.size}

def compare(first,second,offset=0,count=65536):
 if type(offset) is not int or offset<0 or type(count) is not int or not 1<=count<=65536:raise ValueError('Intervalo de comparación no válido.')
 stamps=[revision(first),revision(second)];sizes=[first.stat().st_size,second.stat().st_size];end=min(max(sizes),offset+count)
 if offset>max(sizes):raise ValueError('El intervalo está fuera de ambos binarios.')
 with first.open('rb') as a,second.open('rb') as b:a.seek(offset);b.seek(offset);left=a.read(count);right=b.read(count)
 groups=[];different=0
 for i in range(max(len(left),len(right))):
  if left[i:i+1]==right[i:i+1]:continue
  different+=1
  if groups and groups[-1]['offset']+groups[-1]['count']==offset+i:groups[-1]['count']+=1
  elif len(groups)<256:groups.append({'offset':offset+i,'count':1})
 if stamps!=[revision(first),revision(second)]:raise ValueError('Un binario cambió durante la comparación.')
 return {'offset':offset,'end':end,'sizes':sizes,'revisions':stamps,'differentBytes':different,'ranges':groups,'rangesTruncated':sum(g['count'] for g in groups)<different,'nextOffset':end if end<max(sizes) else None,'identicalInRange':different==0}
