// Binding planner only. NCC in the Python service authorizes the declaration
// and checks both complete candidates before any edit can reach the editor.
const fs=require('node:fs');
const {index,maskCode}=require('./scoped-navigation.cjs');
const core=require(process.argv[2]),request=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const files=request.sources,cache=new Map();
function analyse(name){if(!cache.has(name))cache.set(name,index(core,files[name]));return cache.get(name);}
function moduleFile(name){
 const relative=name.replaceAll('.','/')+'.n',wanted=[relative.toLowerCase(),('src/'+relative).toLowerCase()],matches=Object.keys(files).filter(p=>wanted.includes(p.toLowerCase()));
 if(matches.length!==1)throw Error('Módulo nC ausente o ambiguo: '+name);return matches[0];
}
function imports(text){const result=new Map();for(const use of maskCode(text).matchAll(/\buse\s*<([^>]+)>/g))for(const group of use[1].matchAll(/(?:^|\|)\s*project\s*:\s*([^|]+)/g))for(const name of group[1].split(',').map(s=>s.trim()))result.set(name.toLowerCase(),moduleFile(name));return result;}
function qualified(data){return [...data.masked.matchAll(/\b([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\b/g)].map(m=>({module:m[1],container:m[2],member:m[3],start:m.index,at:m.index+m[0].lastIndexOf(m[3]),end:m.index+m[0].length}));}
function main(){
 const selected=analyse(request.path),point=request.position;let target=request.path,hit=selected.selected(point);
 if(!hit){
  const dependencies=imports(files[request.path]);
  for(const row of qualified(selected)){
   const at=selected.position(row.at),end=selected.position(row.end);if(point.line<at.line||point.line>end.line||point.line===at.line&&point.character<at.character||point.line===end.line&&point.character>end.character)continue;
   target=dependencies.get(row.module.toLowerCase());if(!target)continue;
   if(selected.resolve(row.module,selected.position(row.start)))return null;
   const other=analyse(target),owners=other.definitions.filter(d=>d.kind==='containers'&&d.name===row.container);
   const matches=owners.length===1?other.definitions.filter(d=>d.kind==='functions'&&d.owner===owners[0].body&&d.name===row.member):[];
   if(matches.length!==1)throw Error('El miembro importado no tiene una declaración inequívoca.');hit=matches[0];break;
  }
 }
 if(!hit||hit.kind!=='functions')return null;
 const data=analyse(target),container=data.definitions.filter(d=>d.kind==='containers'&&d.body===hit.owner);if(container.length!==1)return null;
 const name=request.newName;if(!/^[A-Za-z_]\w*$/.test(name)||core.KEYWORDS.includes(name))throw Error('El nombre nuevo no es un identificador nC válido.');
 if(name===hit.name)return {target,container:container[0].name,member:hit.name,changes:[],references:0};
 const references=data.occurrences(hit),collision=data.definitions.some(d=>d!==hit&&d.name===name&&d.owner===hit.owner)||references.some(row=>data.resolve(name,row,false));
 if(collision)throw Error('El nombre nuevo colisiona con otro símbolo visible.');
 const edits=new Map([[target,references.map(row=>({range:{start:{line:row.line,character:row.character},end:{line:row.line,character:row.character+row.length}},newText:name}))]]);
 for(const [file,text] of Object.entries(files)){
  const other=analyse(file),dependencies=imports(text);
  for(const row of qualified(other)){
   if(dependencies.get(row.module.toLowerCase())!==target||row.container!==container[0].name||row.member!==hit.name)continue;
   if(other.masked.slice(0,row.start).trimEnd().endsWith('.'))throw Error('Referencia con más niveles sin vínculo comprobado.');
   if(other.resolve(row.module,other.position(row.start)))continue;
   const start=other.position(row.at),end=other.position(row.end),edit={range:{start,end},newText:name};if(!edits.has(file))edits.set(file,[]);edits.get(file).push(edit);
  }
 }
 const count=[...edits.values()].reduce((n,rows)=>n+rows.length,0);if(count>1000||edits.size>64)throw Error('La refactorización supera 1000 referencias o 64 archivos.');
 return {target,container:container[0].name,member:hit.name,changes:[...edits].map(([path,edits])=>({path,edits})),references:count};
}
try{process.stdout.write(JSON.stringify(main()));}catch(error){process.stderr.write(error.message);process.exitCode=1;}
