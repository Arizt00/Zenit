import {tokenColor,themeEntries} from './theme-tokens.js';

const standardScopes={namespace:['entity.name.namespace'],class:['entity.name.type.class'],enum:['entity.name.type.enum'],interface:['entity.name.type.interface'],struct:['entity.name.type.struct'],typeParameter:['entity.name.type.parameter'],type:['entity.name.type'],parameter:['variable.parameter'],variable:['variable.other.readwrite'],property:['variable.other.property'],enumMember:['variable.other.enummember'],function:['entity.name.function'],method:['entity.name.function.member'],macro:['entity.name.function.preprocessor'],decorator:['entity.name.function.decorator'],comment:['comment'],string:['string'],keyword:['keyword'],number:['constant.numeric'],regexp:['string.regexp'],operator:['keyword.operator']};
const matches=(actual,wanted)=>actual===wanted||actual.startsWith(wanted+'.');
function scopeScore(selector,stack){
  if(typeof selector!=='string')return -1;
  const [positive,...negative]=selector.trim().split(/\s+-\s+/);
  if(negative.some(s=>scopeScore(s,stack)>=0))return -1;
  const parts=positive.split(/\s+/).filter(x=>x&&x!=='>');let index=stack.length-1,score=0;
  for(let p=parts.length-1;p>=0;p--){while(index>=0&&!matches(stack[index],parts[p]))index--;if(index<0)return -1;score+=parts[p].split('.').length*100+index;index--;}
  return parts.length?score:-1;
}
function tokenSettings(value,bg){
  const raw=typeof value==='string'?{foreground:value}:value,result={};if(!raw||typeof raw!=='object')return result;
  const foreground=tokenColor(raw.foreground,bg);if(foreground)result.foreground=foreground;
  if(typeof raw.fontStyle==='string')result.fontStyle=raw.fontStyle.split(/\s+/).filter(s=>['bold','italic','underline','strikethrough'].includes(s)).join(' ');
  for(const flag of ['bold','italic','underline','strikethrough'])if(typeof raw[flag]==='boolean')result[flag]=raw[flag];
  return result;
}
function selectorScore(selector,type,modifiers,language,parents){
  const [body,lang]=selector.split(':');if(lang&&lang!==language)return -1;
  const [base,...required]=body.split('.');if(required.some(m=>!modifiers.includes(m)))return -1;
  const distance=parents.indexOf(base);if(base!=='*'&&distance<0)return -1;
  return (base==='*'?0:1000-distance*10)+required.length*100+(lang?10000:0);
}

/** Resolve extension semantic categories through their declared TextMate scopes.
 * Standalone Monaco otherwise paints unknown custom categories in the default
 * foreground, erasing the grammar colours. Unmapped tokens stay lexical. */
export class SemanticStyles{
  constructor(changed=()=>{}){this.changed=changed;this.slots=new Map();this.classifications=[];this.rules=[];this.cache=new Map();this.legend={tokenTypes:Array.from({length:2048},(_,n)=>'zenitSemantic'+n),tokenModifiers:[]};this.configure({});this.setTheme(null,{});}
  configure(data){this.parents=new Map((data.semanticTokenTypes||[]).map(t=>[t.id,t.superType]));this.mappings=data.semanticTokenScopes||[];this.languageStyles=data.languageStyles||[];this.cache.clear();}
  setTheme(theme,palette,mode='dark'){this.theme=theme;this.palette=palette;this.entries=[...themeEntries(theme),...this.languageStyles.flatMap(s=>s[mode]?.tokenColors||[])];this.semanticColors={...theme?.data?.semanticTokenColors,...Object.assign({},...this.languageStyles.map(s=>s[mode]?.semanticTokenColors||{}))};this.cache.clear();this.rules=this.classifications.map(({type,modifiers,language},slot)=>this.rule(slot,this.resolve(type,modifiers,language)||{foreground:palette.text||'#808080'}));}
  rule(slot,style){return {token:this.legend.tokenTypes[slot],...(style.foreground?{foreground:style.foreground.slice(1)}:{}),fontStyle:style.fontStyle||''};}
  resolve(type,modifiers,language){
    const key=JSON.stringify([type,modifiers,language]);if(this.cache.has(key))return this.cache.get(key);
    const palette=this.palette,bg=palette.editor||'#ffffff',parents=[type];
    while(this.parents.get(parents.at(-1))&&!parents.includes(this.parents.get(parents.at(-1))))parents.push(this.parents.get(parents.at(-1)));
    const result={},scopes=[];
    for(const map of this.mappings)if(!map.language||map.language===language){
      const candidates=Object.entries(map.scopes||{}).map(([selector,values])=>({values,score:selectorScore(selector,type,modifiers,language,parents)})).filter(x=>x.score>=0).sort((a,b)=>b.score-a.score);
      if(candidates.length)scopes.push(...candidates[0].values);
    }
    if(!scopes.length)scopes.push(...(standardScopes[type]||[]));
    for(const scope of scopes){
      const stack=scope.split(/\s+/),entries=[];
      for(const entry of this.entries){
        const selectors=Array.isArray(entry.scope)?entry.scope:String(entry.scope||'').split(',');
        const score=Math.max(-1,...selectors.map(s=>scopeScore(s,stack)));
        if(score>=0)entries.push({score,settings:entry.settings});
      }
      if(entries.length){for(const entry of entries.sort((a,b)=>a.score-b.score))Object.assign(result,tokenSettings(entry.settings,bg));break;}
      const leaf=stack.at(-1),role=leaf.startsWith('comment')?'comment':leaf.startsWith('string')?'string':leaf.startsWith('constant.numeric')?'number':/^(?:keyword|storage)/.test(leaf)?'keyword':/^(?:support.type|entity.name.type)/.test(leaf)?'type':/^(?:support.function|entity.name.function)/.test(leaf)?'function':null;
      if(role&&palette[role])Object.assign(result,{foreground:palette[role],...(role==='comment'?{fontStyle:'italic'}:{})});
    }
    const overrides=Object.entries(this.semanticColors).map(([selector,value])=>({score:selectorScore(selector,type,modifiers,language,parents),value})).filter(x=>x.score>=0).sort((a,b)=>a.score-b.score);
    for(const item of overrides)Object.assign(result,tokenSettings(item.value,bg));
    if(['bold','italic','underline','strikethrough'].some(k=>k in result)){
      const flags=new Set((result.fontStyle||'').split(' ').filter(Boolean));for(const k of ['bold','italic','underline','strikethrough'])if(k in result){result[k]?flags.add(k):flags.delete(k);delete result[k];}result.fontStyle=[...flags].join(' ');
    }
    const resolved=Object.keys(result).length?result:null;
    if(this.cache.size>=8192)this.cache.clear();this.cache.set(key,resolved);return resolved;
  }
  rewrite(data,original,language){
    const output=[];let line=0,column=0,lastLine=0,lastColumn=0,added=false;
    for(let n=0;n+4<data.length;n+=5){
      line+=data[n];column=data[n]?data[n+1]:column+data[n+1];const type=original.tokenTypes[data[n+3]];if(!type)continue;
      const bits=data[n+4]>>>0,modifiers=original.tokenModifiers.filter((_,i)=>i<32&&(bits&(1<<i))),style=this.resolve(type,modifiers,language);if(!style)continue;
      const key=JSON.stringify([type,modifiers,language]);let slot=this.slots.get(key);
      if(slot===undefined){if(this.slots.size>=this.legend.tokenTypes.length)continue;slot=this.slots.size;this.slots.set(key,slot);this.classifications.push({type,modifiers,language});this.rules.push(this.rule(slot,style));added=true;}
      output.push(line-lastLine,line===lastLine?column-lastColumn:column,data[n+2],slot,0);lastLine=line;lastColumn=column;
    }
    if(added)this.changed();return new Uint32Array(output);
  }
}
