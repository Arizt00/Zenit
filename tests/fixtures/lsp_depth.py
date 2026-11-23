"""Deterministic protocol fixture; tests transport and editor integration, not analysis."""
import json,re,sys
from pathlib import Path
from urllib.parse import unquote,urlparse

root=None;documents={}
def send(message):
 raw=json.dumps(message).encode();sys.stdout.buffer.write(b'Content-Length: '+str(len(raw)).encode()+b'\r\n\r\n'+raw);sys.stdout.buffer.flush()
def span(line,start,end):return {'start':{'line':line,'character':start},'end':{'line':line,'character':end}}
while True:
 headers={}
 while True:
  line=sys.stdin.buffer.readline()
  if not line:raise SystemExit
  if line in (b'\r\n',b'\n'):break
  key,_,value=line.decode().partition(':');headers[key.lower()]=value.strip()
 message=json.loads(sys.stdin.buffer.read(int(headers.get('content-length','0'))));method=message.get('method');params=message.get('params',{})
 if 'method' not in message:
  if message.get('id')=='folders-check':assert message['result']==[{'uri':root.as_uri(),'name':root.name}]
  continue
 if method=='exit':break
 if method=='textDocument/didOpen':documents[params['textDocument']['uri']]=params['textDocument']['text']
 if method=='textDocument/didChange':documents[params['textDocument']['uri']]=params['contentChanges'][-1]['text']
 if 'id' not in message:continue
 result=None
 if method=='initialize':
  assert params['capabilities']['workspace'].get('workspaceFolders') is True
  parsed=unquote(urlparse(params['rootUri']).path);parsed=parsed[1:] if re.match(r'^/[A-Za-z]:',parsed) else parsed;root=Path(parsed)
  send({'jsonrpc':'2.0','id':'folders-check','method':'workspace/workspaceFolders','params':{}})
  result={'capabilities':{'positionEncoding':'utf-16','textDocumentSync':1,'definitionProvider':True,'referencesProvider':True,'documentSymbolProvider':True,'renameProvider':{'prepareProvider':True},'documentFormattingProvider':True,'codeActionProvider':{'codeActionKinds':['refactor.rewrite']}}}
 elif method=='textDocument/definition':result=[{'uri':(root/'helper.py').as_uri().replace('file:///C:','file:///c:'),'range':span(0,0,5)}]
 elif method=='textDocument/references':result=[{'uri':(root/'helper.py').as_uri(),'range':span(0,0,5)},{'uri':(root/'main.py').as_uri(),'range':span(1,6,11)}]
 elif method=='textDocument/documentSymbol':result=[{'name':'main','detail':'protocol fixture','kind':12,'range':{'start':{'line':0,'character':0},'end':{'line':1,'character':12}},'selectionRange':span(1,0,5),'children':[]}]
 elif method=='textDocument/prepareRename':result={'range':span(1,6,11),'placeholder':'value'}
 elif method=='textDocument/rename':
  changes={}
  for name in ('main.py','helper.py'):
   uri=(root/name).as_uri();text=documents.get(uri,(root/name).read_text());edits=[]
   for line,textline in enumerate(text.splitlines()):
    for match in re.finditer(r'\bvalue\b',textline):edits.append({'range':span(line,match.start(),match.end()),'newText':params['newName']})
   changes[uri]=edits
  result={'changes':changes}
 elif method=='textDocument/codeAction':result=[{'title':'Fixture · cambiar literal','kind':'refactor.rewrite','edit':{'changes':{(root/'helper.py').as_uri():[{'range':span(0,8,9),'newText':'8'}]}}}]
 elif method=='textDocument/formatting':result=[]
 send({'jsonrpc':'2.0','id':message['id'],'result':result})
