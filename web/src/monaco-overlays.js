// Monaco renders context menus in a ShadowRoot. Its menu stylesheet cannot
// inherit document rules, but CSS custom properties still cross that boundary.
import {icon} from './icons.js';
const css = `body>.monaco-menu-container{z-index:140!important}
.monaco-menu{font-family:var(--font-ui,"Segoe UI",sans-serif)!important}
.monaco-menu .monaco-action-bar.vertical{box-sizing:border-box;background:var(--surface)!important;border:1px solid var(--border)!important;border-radius:var(--radius-control,10px)!important;padding:5px!important;color:var(--text)!important;box-shadow:var(--shadow-menu,0 8px 26px #0002)!important;max-width:min(360px,calc(100vw - 16px));max-height:calc(100vh - 24px);overflow-y:auto;scrollbar-width:thin}
.monaco-menu .monaco-action-bar.vertical .action-item{border-radius:5px!important;margin:1px 0}
.monaco-menu .monaco-action-bar.vertical .action-menu-item{color:var(--text)!important;min-height:27px;gap:9px;padding:1px 8px!important;line-height:23px!important}
.monaco-menu .monaco-action-bar.vertical .action-item.focused{background:var(--hover)!important;color:var(--text)!important}
.monaco-menu .monaco-action-bar.vertical .action-label{font-family:var(--font-ui,"Segoe UI",sans-serif)!important;font-size:12px;max-width:240px;overflow:hidden;text-overflow:ellipsis}
.monaco-menu .monaco-action-bar.vertical .keybinding{font-family:var(--font-ui,"Segoe UI",sans-serif)!important;color:var(--secondary)!important;font-size:10px!important;margin-left:12px!important}
.monaco-menu .zenit-menu-glyph{display:grid;place-items:center;flex:none;width:16px;height:16px;color:var(--secondary);pointer-events:none}
.monaco-menu .zenit-menu-glyph .icon{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:1.75;stroke-linecap:round;stroke-linejoin:round}
.monaco-menu .monaco-action-bar.vertical .action-label.separator{border-bottom-color:var(--border)!important;margin:3px 0!important;padding:0!important;height:1px!important;min-height:0!important}
.monaco-menu .monaco-action-bar.vertical .action-menu-item:has(.separator){min-height:0!important;height:7px!important;padding:0 5px!important}
.monaco-menu .monaco-action-bar.vertical .action-item:has(.separator){margin:0!important}
:root[data-motion=off] .monaco-menu,:host-context([data-motion=off]) .monaco-menu{animation:none!important}
@media(prefers-reduced-motion:no-preference){.monaco-menu{animation:zenit-menu-in var(--motion-fast,120ms) ease-out}}@keyframes zenit-menu-in{from{opacity:0;translate:0 2px}to{opacity:1;translate:0 0}}`;

export function installMonacoOverlays(){
  const decorate=root=>{for(const row of root.querySelectorAll('.monaco-menu .action-menu-item')){
    if(row.querySelector('.separator')||row.querySelector('.zenit-menu-glyph'))continue;
    const label=row.querySelector('.action-label')?.textContent?.trim()||'',glyph=/^(Copiar|Copy)$/.test(label)?'copy':/^(Cortar|Cut)$/.test(label)?'cut':/^(Pegar|Paste)$/.test(label)?'clipboard':/^Guardar|^Save/.test(label)?'download':/^Abrir en otra|^Open in/.test(label)?'arrow-up-right':/^Lantern/.test(label)?'sparkles':/^Preguntar|^Ask/.test(label)?'bulb':/^Paleta|^Command Palette/.test(label)?'keyboard':null;
    const node=document.createElement('span');node.className='zenit-menu-glyph';node.setAttribute('aria-hidden','true');if(glyph)node.innerHTML=icon(glyph);row.prepend(node);
  }};
  const sheet=document.createElement('style');sheet.textContent=css;sheet.dataset.zenitEditorMenus='';document.head.append(sheet);
  const shadows=new Map(),relevant=records=>records.some(r=>[...r.addedNodes].some(n=>n.nodeType===1&&!n.matches('.zenit-menu-glyph')&&(n.matches('.shadow-root-host,.monaco-menu,.action-item,.action-menu-item')||n.querySelector('.shadow-root-host,.monaco-menu,.action-item,.action-menu-item'))));
  const apply=()=>{decorate(document);for(const [host,observer] of shadows)if(!host.isConnected){observer.disconnect();shadows.delete(host);}for(const host of document.querySelectorAll('.shadow-root-host')){const root=host.shadowRoot;if(!root)continue;if(!root.querySelector('[data-lumen-menu-style]')){const style=document.createElement('style');style.dataset.lumenMenuStyle='';style.textContent=css;root.append(style);}if(!shadows.has(host)){const observer=new MutationObserver(records=>{if(relevant(records))decorate(root);});observer.observe(root,{childList:true,subtree:true});shadows.set(host,observer);}decorate(root);}};
  const observer=new MutationObserver(records=>{if(relevant(records)||[...shadows.keys()].some(host=>!host.isConnected))apply();});observer.observe(document.body,{childList:true,subtree:true});apply();
  return {dispose(){observer.disconnect();for(const observer of shadows.values())observer.disconnect();shadows.clear();sheet.remove();}};
}
