import './theme-cache.js';
import {themeEntries} from './theme-tokens.js';
// Only color values from an extension may enter the shell; never arbitrary CSS.
const rgb=hex=>[1,3,5].map(n=>parseInt(hex.slice(n,n+2),16));
const hex=values=>'#'+values.map(v=>Math.round(v).toString(16).padStart(2,'0')).join('');
const opaque=(color,background)=>{const alpha=color.length===9?parseInt(color.slice(7),16)/255:1;return hex(rgb(color).map((c,i)=>c*alpha+rgb(background)[i]*(1-alpha)));};
function luminance(color){const c=rgb(color).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return c[0]*.2126+c[1]*.7152+c[2]*.0722;}
export function contrastRatio(a,b){const [lo,hi]=[luminance(a),luminance(b)].sort((x,y)=>x-y);return (hi+.05)/(lo+.05);}
function readable(color,background,minimum=4.5){
  const solid=opaque(color,background);if(contrastRatio(solid,background)>=minimum)return solid;
  const target=contrastRatio('#000000',background)>contrastRatio('#ffffff',background)?[0,0,0]:[255,255,255],original=rgb(solid);let low=0,high=1;
  for(let n=0;n<16;n++){const mid=(low+high)/2,result=hex(original.map((c,i)=>c+(target[i]-c)*mid));if(contrastRatio(result,background)>=minimum)high=mid;else low=mid;}
  return hex(original.map((c,i)=>c+(target[i]-c)*high));
}
export function themePalette(theme) {
  const colors=Object.fromEntries(Object.entries(theme.data?.colors||{}).filter(([,v])=>typeof v==='string'&&/^#(?:[\da-f]{3,4}|[\da-f]{6}|[\da-f]{8})$/i.test(v)).map(([k,v])=>[k,v.length<6?'#'+[...v.slice(1)].map(c=>c+c).join(''):v]));
  const dark=theme.uiTheme!=='vs'&&theme.uiTheme!=='hc-light';
  const pick=(keys,fallback)=>keys.split('|').map(k=>colors[k]).find(Boolean)||fallback;
  const bg=pick('editor.background',dark?'#1e1e1e':'#ffffff'),text=pick('editor.foreground|foreground',dark?'#d4d4d4':'#242424');
  const surface=pick('sideBar.background|editorWidget.background',bg),fallback=dark?'#8eabff':'#405dde';
  // focusBorder is often explicitly transparent. It is not an icon/text colour.
  const accent=['textLink.foreground','button.background','activityBarBadge.background','focusBorder'].map(k=>colors[k]).find(c=>c&&(c.length!==9||parseInt(c.slice(7),16)>=32)&&contrastRatio(opaque(c,opaque(surface,dark?'#1e1e1e':'#ffffff')),opaque(surface,dark?'#1e1e1e':'#ffffff'))>=3)||fallback;
  const border=pick('panel.border|widget.border|sideBar.border',dark?'#444444':'#d4d4d4');
  const palette={bg:pick('workbench.background|editorGroup.emptyBackground',bg),surface,editor:bg,header:pick('titleBar.activeBackground',surface),rail:pick('activityBar.background',surface),card:surface,field:pick('input.background',surface),text,secondary:pick('sideBar.foreground|foreground',text),muted:pick('descriptionForeground|editorLineNumber.foreground',text),accent,'accent-bright':accent,'accent-soft':pick('list.inactiveSelectionBackground',surface),selected:pick('list.activeSelectionBackground|tab.activeBackground',surface),hover:pick('list.hoverBackground',surface),line:pick('editor.lineHighlightBackground',bg),border,'border-strong':pick('focusBorder',border),selection:pick('editor.selectionBackground',accent.slice(0,7)+'33'),'terminal-bg':pick('terminal.background',bg),'terminal-text':pick('terminal.foreground',text),folder:pick('symbolIcon.folderForeground',accent),'logo-light':accent,'logo-dark':accent,success:pick('terminal.ansiGreen','#70aa78'),danger:pick('errorForeground|editorError.foreground','#de5967'),warning:pick('editorWarning.foreground','#c9a05a'),glass:surface.slice(0,7)+'af','glass-edge':border,'inset':'inset 0 1px 0 '+border.slice(0,7)+'55'};
  for(const [token,scopes] of Object.entries({keyword:['keyword','storage'],type:['entity.name.type','support.type'],string:['string'],number:['constant.numeric'],comment:['comment'],function:['entity.name.function','support.function']})){
    const entry=themeEntries(theme).reverse().find(e=>(Array.isArray(e.scope)?e.scope:String(e.scope||'').split(',')).some(s=>typeof s==='string'&&scopes.some(x=>s.trim()===x))&&/^#[\da-f]{6}$/i.test(e.settings?.foreground||''));
    palette['syntax-'+token]=entry?.settings.foreground||text;
  }
  // Transparent foregrounds and barely visible theme labels must not wash out
  // the entire shell. Preserve usable colours; adjust only failing text pairs.
  const base=dark?'#1e1e1e':'#ffffff';
  for(const key of ['bg','surface','editor','header','rail','card','field','selected','hover','terminal-bg'])palette[key]=opaque(palette[key],base);
  for(const key of ['text','secondary','muted'])palette[key]=readable(palette[key],palette.surface);
  palette.accent=readable(accent,palette.surface);palette['accent-bright']=palette.accent;
  palette['accent-soft']=opaque(palette['accent-soft'],palette.surface);
  // Keep accent chips subtly separated even when a theme makes them identical.
  if(palette['accent-soft']===palette.surface)palette['accent-soft']=hex(rgb(palette.surface).map((c,i)=>c*.92+rgb(palette.accent)[i]*.08));
  palette['soft-text']=readable(palette.accent,palette['accent-soft']);
  palette['soft-secondary']=readable(palette.secondary,palette['accent-soft']);
  palette['button-start']=palette['button-end']=opaque(pick('button.background',palette.accent),palette.surface);
  palette['button-text']=readable(pick('button.foreground','#ffffff'),palette['button-end']);
  palette['field-text']=readable(pick('input.foreground',palette.text),palette.field);
  palette['field-muted']=readable(pick('input.placeholderForeground',palette.muted),palette.field);
  for(const [token,background] of [['chrome','header'],['rail','rail'],['canvas','bg']]){
    palette[token+'-text']=readable(palette.text,palette[background]);palette[token+'-secondary']=readable(palette.secondary,palette[background]);palette[token+'-accent']=readable(palette.accent,palette[background]);
  }
  palette.overlay=palette.bg+'88';palette.focus=readable(pick('focusBorder',palette.accent),palette.surface,3);
  palette['chrome-halo']=palette.bg;palette['selection-halo']=palette.selected;
  palette['logo-light']=palette['logo-dark']=palette['chrome-accent'];
  for(const key of ['success','danger','warning'])palette[key]=readable(palette[key],palette.surface);
  palette['positive-bg']=palette['accent-soft'];palette['positive-text']=readable(palette.success,palette['positive-bg']);
  palette['terminal-text']=readable(palette['terminal-text'],palette['terminal-bg']);
  palette['selected-text']=readable(pick('list.activeSelectionForeground',palette.text),palette.selected);
  for(const key of Object.keys(palette).filter(k=>k.startsWith('syntax-')))palette[key]=readable(palette[key],palette.editor);
  return {palette,colors,dark};
}
export function restoreShellAppearance(root=document.documentElement,storage=localStorage){return globalThis.ZenitThemeAppearance.restore(root,storage);}
export function applyShellTheme(theme,root=document.documentElement,baseTheme='day'){
  const resolved=theme?themePalette(theme):null,palette=resolved?.palette||{};if(theme)palette.glass=palette.surface.slice(0,7)+'f0';
  for(const key of (root.dataset.extensionTokens||'').split(' ').filter(Boolean))if(!(key in palette))root.style.removeProperty('--'+key);
  for(const [key,value] of Object.entries(palette))if(root.style.getPropertyValue('--'+key)!==value)root.style.setProperty('--'+key,value);
  if(theme){root.dataset.extensionTokens=Object.keys(palette).join(' ');root.dataset.extensionTheme=theme.id;root.dataset.theme=resolved.dark?'dark':'day';}
  else{delete root.dataset.extensionTheme;delete root.dataset.extensionTokens;root.dataset.theme=baseTheme;}
  try{if(theme)localStorage.setItem('zenit.themeAppearance',JSON.stringify({id:theme.id,base:root.dataset.theme,palette}));else localStorage.removeItem('zenit.themeAppearance');}catch{}
}
