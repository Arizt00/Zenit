/* Local nC source navigation. Uses the selected integration's declaration parser.
 * Imports keep its existing project/catalog resolver. Unknown/ambiguous bindings
 * are never turned into a project-wide textual rename.
 */
'use strict';
function maskCode(text) {
  const out=text.split('');let quote='',comment=0;
  const blank=i=>{if(out[i]!=='\r'&&out[i]!=='\n')out[i]=' ';};
  for(let i=0;i<text.length;i++){
    const c=text[i],next=text[i+1];
    if(comment===1){if(c==='\n')comment=0;else blank(i);continue;}
    if(comment===2){blank(i);if(c==='*'&&next==='/'){blank(++i);comment=0;}continue;}
    if(quote){blank(i);if(c==='\\'){if(i+1<text.length)blank(++i);}else if(c===quote)quote='';continue;}
    if(c==='/'&&next==='/'){blank(i);blank(++i);comment=1;}
    else if(c==='/'&&next==='*'){blank(i);blank(++i);comment=2;}
    else if(c==='"'||c==="'"){quote=c;blank(i);}
  }
  return out.join('');
}
function index(core,text){
  const masked=maskCode(text),lines=masked.split('\n'),starts=[0];
  const importRanges=[...masked.matchAll(/\buse\s*<[^>]+>/g)].map(m=>[m.index,m.index+m[0].length]);
  for(let i=0;i<masked.length;i++)if(masked[i]==='\n')starts.push(i+1);
  const offset=p=>(starts[p.line]??masked.length)+p.character;
  const position=n=>{let lo=0,hi=starts.length;while(lo+1<hi){const mid=(lo+hi)>>1;if(starts[mid]<=n)lo=mid;else hi=mid;}return {line:lo,character:n-starts[lo]};};
  const root={start:-1,end:masked.length,parent:null,children:[]},stack=[root],scopes=[];
  for(let i=0;i<masked.length;i++){
    if(masked[i]==='{'){const s={start:i,end:masked.length,parent:stack.at(-1),children:[]};s.parent.children.push(s);scopes.push(s);stack.push(s);}
    else if(masked[i]==='}'){if(stack.length===1)throw Error('Corrige las llaves antes de navegar o renombrar.');stack.pop().end=i;}
  }
  if(stack.length!==1)throw Error('Corrige las llaves antes de navegar o renombrar.');
  const scopeAt=n=>{let scope=root;while(true){const child=scope.children.find(s=>s.start<n&&n<s.end);if(!child)return scope;scope=child;}};
  // The selected parser recognizes declaration lines. Present a whitespace-only
  // view with one declaration per line, then map every coordinate back to the
  // unchanged original text. Compact source and Allman braces keep their scope.
  const boundaries=new Set([...masked.matchAll(/\b(?:fn|stc|public|private|protected|fa)\s*:/g)].map(m=>m.index+m[0].length));
  let declarationText='',atStart=true;const originalOffsets=[];
  for(let i=0;i<masked.length;i++){
    const c=/\s/.test(masked[i])?' ':masked[i];
    if(!(atStart&&c===' ')){originalOffsets.push(i);declarationText+=c;atStart=false;}
    if(';{}'.includes(c)||boundaries.has(i+1)){originalOffsets.push(i+1);declarationText+='\n';atStart=true;}
  }
  const declarationStarts=[0];for(let i=0;i<declarationText.length;i++)if(declarationText[i]==='\n')declarationStarts.push(i+1);
  const parsed=core.parseSymbols(declarationText),definitions=[];
  for(const rows of Object.values(parsed))for(const row of rows){const p=position(originalOffsets[(declarationStarts[row.line]||0)+row.character]??masked.length);row.line=p.line;row.character=p.character;}
  for(const kind of ['containers','functions','variables','parameters'])for(const row of parsed[kind]||[]){
    const at=offset(row);
    const body=['containers','functions','parameters'].includes(kind)?scopes.find(s=>s.start>at&&!/[;{}]/.test(masked.slice(at,s.start))):null;
    const owner=kind==='parameters'?body:scopeAt(at);
    if(owner&&masked.slice(at,at+row.name.length)===row.name)definitions.push({...row,kind,at,owner,body});
  }
  const codeOccurrence=(name,p)=>{
    const at=offset(p),line=lines[p.line]||'';let previous=at-1;while(previous>=0&&/\s/.test(masked[previous]))previous--;const before=masked[previous];
    return masked.slice(at,at+name.length)===name&&!/[\w]/.test(masked[at-1]||'')&&!/[\w]/.test(masked[at+name.length]||'')&&!importRanges.some(([start,end])=>start<=at&&at<end);
  };
  const resolve=(name,p,checkSpelling=true)=>{
    if(checkSpelling&&!codeOccurrence(name,p))return null;
    const at=offset(p),decl=definitions.find(d=>d.at===at&&d.name===name);if(decl)return decl;
    const prefix=masked.slice(0,at),qualified=prefix.match(/([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*$/);
    if(qualified){
      if(prefix.slice(0,qualified.index).trimEnd().endsWith('.'))return null;
      const owners=definitions.filter(d=>d.kind==='containers'&&d.name===qualified[1]);
      if(owners.length!==1)return null;
      const matches=definitions.filter(d=>d.name===name&&d.owner===owners[0].body);
      return matches.length===1?matches[0]:null;
    }
    for(let scope=scopeAt(at);scope;scope=scope.parent){
      const matches=definitions.filter(d=>d.name===name&&d.owner===scope&&(d.kind!=='variables'||definitions.some(c=>c.kind==='containers'&&c.body===scope)||d.at<=at));
      if(matches.length>1)throw Error('El símbolo es ambiguo en este ámbito; revisa sus declaraciones.');
      if(matches.length)return matches[0];
    }
    return null;
  };
  const symbol=p=>{
    const line=lines[p.line]||'';for(const match of line.matchAll(/[A-Za-z_][A-Za-z0-9_]*/g))if(match.index<=p.character&&p.character<=match.index+match[0].length)return {name:match[0],position:{line:p.line,character:match.index}};return null;
  };
  const selected=p=>{const token=symbol(p);return token&&!core.KEYWORDS.includes(token.name)?resolve(token.name,token.position):null;};
  const occurrences=definition=>core.collectCodeOccurrences(masked,definition.name).filter(row=>resolve(definition.name,row)===definition);
  return {definitions,selected,occurrences,resolve,position,masked,importAt:p=>importRanges.some(([start,end])=>start<=offset(p)&&offset(p)<end)};
}
function create(core,vscode){
  const cache=new Map();
  const analyse=document=>{
    const key=document.uri.toString(),text=document.getText(),previous=cache.get(key);cache.delete(key);
    const data=previous?.text===text?previous.data:index(core,text);cache.set(key,{text,data});
    while(cache.size>4||[...cache.values()].reduce((n,row)=>n+row.text.length,0)>2_000_000)cache.delete(cache.keys().next().value);
    return data;
  };
  return {
    importAt(document,position){return analyse(document).importAt(position);},
    definition(document,position){const data=analyse(document),hit=data.selected(position);return hit?new vscode.Location(document.uri,new vscode.Range(hit.line,hit.character,hit.line,hit.character+hit.name.length)):null;},
    async memberDefinition(document,position,resolveModule){
      const data=analyse(document),line=data.masked.split('\n')[position.line]||'';
      for(const match of line.matchAll(/\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b/g)){
        const start=match.index+match[1].length+match[2].length+2;
        if(position.character<start||position.character>start+match[3].length)continue;
        const imported=[...data.masked.matchAll(/\buse\s*<\s*project\s*:\s*([^>]+)>/g)].some(row=>row[1].split(',').map(s=>s.trim()).includes(match[1]));
        if(!imported)return null;
        const target=await resolveModule(match[1]);if(!target)return null;
        const other=analyse(target),owners=other.definitions.filter(d=>d.kind==='containers'&&d.name===match[2]);
        const hits=owners.length===1?other.definitions.filter(d=>d.name===match[3]&&d.owner===owners[0].body):[];
        if(hits.length===1){const d=hits[0];return new vscode.Location(target.uri,new vscode.Range(d.line,d.character,d.line,d.character+d.name.length));}
      }
      return null;
    },
    references(document,position){const data=analyse(document),hit=data.selected(position);return hit?data.occurrences(hit).map(row=>new vscode.Location(document.uri,new vscode.Range(row.line,row.character,row.line,row.character+row.length))):[];},
    rename(document,position,newName){
      if(!/^[A-Za-z_][A-Za-z0-9_]*$/.test(newName)||core.KEYWORDS.includes(newName))throw Error('El nuevo nombre no es un identificador nC válido.');
      const data=analyse(document),hit=data.selected(position);if(!hit)throw Error('Se necesita una declaración local inequívoca para renombrar este símbolo.');
      if(newName===hit.name)return new vscode.WorkspaceEdit();
      const rows=data.occurrences(hit),collision=data.definitions.some(d=>d!==hit&&d.name===newName&&d.owner===hit.owner)||rows.some(row=>data.resolve(newName,row,false));
      if(collision)throw Error('Ese nombre ya pertenece a otro símbolo visible. El renombrado se ha cancelado.');
      const edit=new vscode.WorkspaceEdit();for(const row of rows)edit.replace(document.uri,new vscode.Range(row.line,row.character,row.line,row.character+row.length),newName);return edit;
    },
    symbols(document){
      const data=analyse(document),nodes=new Map(),owners=new Map();
      for(const d of data.definitions){
        const end=d.body?data.position(d.body.end+1):{line:d.line,character:d.character+d.name.length};
        const selection=new vscode.Range(d.line,d.character,d.line,d.character+d.name.length),range=new vscode.Range(d.line,d.character,end.line,end.character);
        nodes.set(d,new vscode.DocumentSymbol(d.name,d.typeName||({containers:'container',functions:'fn',parameters:'parameter'})[d.kind]||'stc',({containers:vscode.SymbolKind.Namespace,functions:vscode.SymbolKind.Function,variables:vscode.SymbolKind.Variable,parameters:vscode.SymbolKind.Variable})[d.kind],range,selection));
        if(d.body&&d.kind!=='parameters')owners.set(d.body,d);
      }
      const out=[];for(const d of data.definitions){const parent=owners.get(d.owner);if(parent&&parent!==d)nodes.get(parent).children.push(nodes.get(d));else out.push(nodes.get(d));}return out;
    }
  };
}
module.exports={create,index,maskCode};
