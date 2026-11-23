/** Convert a declarative VS Code language configuration to Monaco's API. */
export function languageConfiguration(raw={},indent={None:0,Indent:1,IndentOutdent:2,Outdent:3}){
  const result={},pattern=value=>{
    const source=typeof value==='string'?value:value?.pattern,flags=typeof value==='object'?value.flags||'':'';
    if(typeof source!=='string'||source.length>8000||!/^[imsu]*$/.test(flags))return undefined;
    try{return new RegExp(source,flags);}catch{return undefined;}
  };
  if(raw.comments&&typeof raw.comments==='object')result.comments=raw.comments;
  for(const key of ['brackets','colorizedBracketPairs','autoClosingPairs','surroundingPairs'])if(Array.isArray(raw[key]))result[key]=raw[key].slice(0,200).filter(p=>Array.isArray(p)?p.length===2&&p.every(s=>typeof s==='string'):p&&typeof p.open==='string'&&typeof p.close==='string');
  if(typeof raw.autoCloseBefore==='string')result.autoCloseBefore=raw.autoCloseBefore;
  if(raw.wordPattern){const re=pattern(raw.wordPattern);if(re)result.wordPattern=re;}
  if(raw.indentationRules){const rules={};for(const key of ['increaseIndentPattern','decreaseIndentPattern','indentNextLinePattern','unIndentedLinePattern']){const re=pattern(raw.indentationRules[key]);if(re)rules[key]=re;}if(rules.increaseIndentPattern&&rules.decreaseIndentPattern)result.indentationRules=rules;}
  if(Array.isArray(raw.onEnterRules))result.onEnterRules=raw.onEnterRules.slice(0,100).flatMap(rule=>{
    const beforeText=pattern(rule?.beforeText),action=rule?.action,value={none:indent.None,indent:indent.Indent,outdent:indent.Outdent,indentOutdent:indent.IndentOutdent}[action?.indent];
    if(!beforeText||value===undefined)return [];
    const item={beforeText,action:{indentAction:value}};
    for(const key of ['afterText','previousLineText'])if(rule[key]){const re=pattern(rule[key]);if(!re)return [];item[key]=re;}
    if(typeof action.appendText==='string')item.action.appendText=action.appendText;
    if(Number.isInteger(action.removeText)&&action.removeText>=0)item.action.removeText=action.removeText;
    return [item];
  });
  if(raw.folding&&typeof raw.folding==='object'){
    result.folding={offSide:raw.folding.offSide===true};const start=pattern(raw.folding.markers?.start),end=pattern(raw.folding.markers?.end);if(start&&end)result.folding.markers={start,end};
  }
  return result;
}
