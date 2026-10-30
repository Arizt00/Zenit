// Stable DocumentSelector semantics: every declared filter must match.
module.exports=function(glob){
 const normalize=value=>String(value).replace(/\\/g,'/');
 function score(selector,document){
  if(!document)return 0;
  if(Array.isArray(selector))return selector.reduce((n,item)=>Math.max(n,score(item,document)),0);
  if(typeof selector==='string')return selector==='*'?5:selector===document.languageId?10:0;
  if(!selector||typeof selector!=='object')return 0;
  let result=0;
  for(const [field,value] of [['language',document.languageId],['scheme',document.uri.scheme],['notebookType',document.notebook?.notebookType]]){
   if(selector[field]===undefined)continue;
   if(!value)return 0;
   if(selector[field]==='*')result=Math.max(result,5);
   else if(selector[field]===value)result=10;else return 0;
  }
  if(selector.pattern!==undefined){
   let file=normalize(document.uri.path||document.fileName),pattern=selector.pattern;
   if(typeof pattern==='object'){
    const base=pattern.baseUri;if(base&&(base.scheme!==document.uri.scheme||base.authority!==document.uri.authority))return 0;
    const prefix=normalize(base?.path||pattern.base||'').replace(/\/$/,'');
    if(!prefix||!file.startsWith(prefix+'/'))return 0;file=file.slice(prefix.length+1);pattern=pattern.pattern;
   }
   if(typeof pattern!=='string'||pattern.length>4096)return 0;
   try{if(!glob(normalize(pattern)).test(file))return 0;}catch{return 0;}
   result=10;
  }
  return result;
 }
 return score;
};
