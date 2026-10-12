/** Theme syntax colours stay distinct from the shell's contrast adjustments. */
export function hexColor(value){
  if(typeof value!=='string'||!/^#(?:[\da-f]{3,4}|[\da-f]{6}|[\da-f]{8})$/i.test(value))return null;
  return value.length<6?'#'+[...value.slice(1)].map(c=>c+c).join(''):value;
}
export function tokenColor(value,background='#ffffff'){
  const color=hexColor(value);if(!color)return null;if(color.length===7)return color;
  const alpha=parseInt(color.slice(7),16)/255,bg=hexColor(background)||'#ffffff';
  return '#'+[1,3,5].map(i=>Math.round(parseInt(color.slice(i,i+2),16)*alpha+parseInt(bg.slice(i,i+2),16)*(1-alpha)).toString(16).padStart(2,'0')).join('');
}
export const themeEntries=theme=>Array.isArray(theme?.data?.tokenColors)?theme.data.tokenColors.filter(e=>e&&typeof e==='object'):[];
const styles=value=>typeof value==='string'?value.split(/\s+/).filter(s=>['italic','bold','underline','strikethrough'].includes(s)).join(' '):undefined;
const aliases={storage:['keyword'],'constant.numeric':['number'],constant:['number'],'entity.name.function':['function'],'support.function':['function'],'entity.name.type':['type','type.identifier'],'support.type':['type','type.identifier'],'entity.name.tag':['tag'],'entity.other.attribute-name':['attribute.name']};
export function monacoThemeRules(theme){
  const base=theme.uiTheme==='vs'||theme.uiTheme==='hc-light'?'#ffffff':'#1e1e1e',bg=tokenColor(theme.data?.colors?.['editor.background'],base)||base,rules=[];
  for(const entry of themeEntries(theme)){
    const foreground=tokenColor(entry.settings?.foreground,bg),fontStyle=styles(entry.settings?.fontStyle);if(!foreground&&fontStyle===undefined)continue;
    const scopes=Array.isArray(entry.scope)?entry.scope:String(entry.scope||'').split(',');
    for(const value of scopes){if(typeof value!=='string')continue;const scope=value.trim();if(/\s|[><]/.test(scope))continue;
      // Only context-free aliases can be represented by Monaco's lexical tokens.
      for(const token of aliases[scope]||[scope])rules.push({token,...(foreground?{foreground:foreground.slice(1)}:{}),...(fontStyle!==undefined?{fontStyle}:{})});
    }
  }
  // Standalone Monaco supports type/modifier rules; language selectors and
  // arbitrary wildcard combinations require a separate semantic styling layer.
  for(const [selector,value] of Object.entries(theme.data?.semanticTokenColors||{})){
    if(!/^[A-Za-z][\w]*(?:\.[A-Za-z][\w]*)*$/.test(selector))continue;
    const settings=typeof value==='string'?{foreground:value}:value;if(!settings||typeof settings!=='object')continue;
    const foreground=tokenColor(settings.foreground,bg);let fontStyle=styles(settings.fontStyle);
    if(fontStyle===undefined&&['bold','italic','underline','strikethrough'].some(k=>typeof settings[k]==='boolean'))fontStyle=['bold','italic','underline','strikethrough'].filter(k=>settings[k]===true).join(' ');
    if(foreground||fontStyle!==undefined)rules.push({token:selector,...(foreground?{foreground:foreground.slice(1)}:{}),...(fontStyle!==undefined?{fontStyle}:{})});
  }
  return rules;
}
export function terminalTheme(theme,fallback){
  const colors=theme?.data?.colors||{},result={...fallback};
  for(const name of ['black','red','green','yellow','blue','magenta','cyan','white','brightBlack','brightRed','brightGreen','brightYellow','brightBlue','brightMagenta','brightCyan','brightWhite']){
    const value=hexColor(colors['terminal.ansi'+name[0].toUpperCase()+name.slice(1)]);if(value)result[name]=value;
  }
  for(const [name,key] of [['cursor','terminalCursor.foreground'],['cursorAccent','terminalCursor.background'],['selectionBackground','terminal.selectionBackground']]){const value=hexColor(colors[key]);if(value)result[name]=value;}
  return result;
}
