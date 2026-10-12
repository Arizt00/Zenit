// Classic script: restores the last rendered colours before CSS or Monaco loads.
// Only these semantic colour tokens and one constrained inset may be restored.
globalThis.ZenitThemeAppearance=Object.freeze({restore(root,storage){
 const allowed=new Set('bg surface editor header rail card field text secondary muted accent accent-bright accent-soft selected hover line border border-strong selection terminal-bg terminal-text folder logo-light logo-dark success danger warning glass glass-edge inset syntax-keyword syntax-type syntax-string syntax-number syntax-comment syntax-function soft-text soft-secondary button-start button-end button-text field-text field-muted chrome-text chrome-secondary chrome-accent rail-text rail-secondary rail-accent canvas-text canvas-secondary canvas-accent overlay focus chrome-halo selection-halo positive-bg positive-text selected-text'.split(' '));
 try{
  const raw=storage.getItem('zenit.themeAppearance');if(!raw||raw.length>20000)return false;const saved=JSON.parse(raw);
  if(!saved||typeof saved.id!=='string'||saved.id.length>500||!['day','dark'].includes(saved.base)||!saved.palette||typeof saved.palette!=='object')return false;
  const entries=Object.entries(saved.palette);if(!entries.length||entries.length>100||entries.some(([key,value])=>!allowed.has(key)||typeof value!=='string'||!(key==='inset'?/^inset 0 1px 0 #[\da-f]{8}$/i:/^#[\da-f]{6}(?:[\da-f]{2})?$/i).test(value)))return false;
  for(const [key,value] of entries)root.style.setProperty('--'+key,value);
  root.dataset.extensionTokens=entries.map(([key])=>key).join(' ');root.dataset.extensionTheme=saved.id;root.dataset.theme=saved.base;return true;
 }catch{return false;}
}});
