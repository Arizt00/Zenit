import {icon} from './icons.js';
import {hoverReveal} from './hover-reveal.js';

/** One launcher for the existing tools; each tool keeps its own entry point. */
export function installDevelopmentTools({platform,showMenu}){
  if(new URLSearchParams(location.search).has('panel'))return {refresh(){},dispose(){}};
  const bar=document.querySelector('.top-actions');
  const entries=[
    {selector:'.forge-toggle',label:'Forge',english:'Forge',glyph:'build'},
    {selector:'.debug-button',label:'Depurar',english:'Debug',glyph:'bug'},
    {selector:'.foundation-toggle',label:'Laboratorio',english:'Laboratory',glyph:'cpu'}
  ].map(entry=>({...entry,button:bar.querySelector(entry.selector)}));
  if(entries.some(entry=>!entry.button))return {refresh(){},dispose(){}};
  const originals=entries.map(entry=>({button:entry.button,hidden:entry.button.hidden}));
  const button=document.createElement('button');button.type='button';button.className='development-tools secondary-button';
  button.innerHTML=icon('build')+'<span></span>';button.setAttribute('aria-haspopup','menu');button.setAttribute('aria-expanded','false');button.setAttribute('aria-controls','popover');
  const first=[...bar.children].find(node=>entries.some(entry=>entry.button===node));bar.insertBefore(button,first);
  for(const entry of entries)entry.button.hidden=true;
  const refresh=()=>{
    const label=platform.t('Herramientas','Tools');button.querySelector('span').textContent=label;
    button.setAttribute('aria-label',platform.t('Herramientas · Forge, Depurar y Laboratorio','Tools · Forge, Debug and Laboratory'));
  };
  hoverReveal(button);refresh();
  button.onclick=()=>showMenu(button,entries.map(entry=>({
    label:platform.t(entry.label,entry.english),icon:entry.glyph,disabled:entry.button.disabled,
    run:()=>entry.button.click()
  })),platform.t('Herramientas de desarrollo','Development tools'));
  return {refresh,dispose(){button.remove();for(const original of originals)original.button.hidden=original.hidden;}};
}
