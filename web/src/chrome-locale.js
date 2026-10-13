import {ENGLISH_CHROME} from './chrome-strings.js';

/** Translate legacy chrome labels only. Documents, chat and user identity are excluded. */
export function installChromeLocale(platform){
  const ignore='script,style,svg,code,pre,textarea,input,[contenteditable],.monaco-editor,.xterm,.chat-message,.melody-plan-files,.file-tabs,.file-tree,.tree-row,.tree-name,.file-name,.forge-file,.forge-session-name,.activity-row,.activity-path,.profile-activity-identity,.activity-file-name,.profile-name,.profile-initial,.avatar,.welcome-profile-avatar,#home-name';
  const originals=new WeakMap(),attributes=new WeakMap();
  const translate=root=>{
    if(root.nodeType===Node.TEXT_NODE){
      if(root.parentElement?.closest(ignore))return;
      const value=root.textContent,key=value.trim(),english=ENGLISH_CHROME[key];
      if(platform.prefs['general.locale']==='en'&&english&&english!==key){originals.set(root,key);root.textContent=value.replace(key,english);}
      else if(platform.prefs['general.locale']!=='en'&&originals.has(root)){const es=originals.get(root);if(key===ENGLISH_CHROME[es])root.textContent=value.replace(key,es);originals.delete(root);}
      return;
    }
    if(root.nodeType!==Node.ELEMENT_NODE||root.matches(ignore))return;
    for(const attr of ['title','aria-label','placeholder']){const value=root.getAttribute(attr);if(platform.prefs['general.locale']==='en'&&ENGLISH_CHROME[value]&&ENGLISH_CHROME[value]!==value){const saved=attributes.get(root)||{};saved[attr]=value;attributes.set(root,saved);root.setAttribute(attr,ENGLISH_CHROME[value]);}else if(platform.prefs['general.locale']!=='en'){const saved=attributes.get(root);if(saved?.[attr]&&value===ENGLISH_CHROME[saved[attr]]){root.setAttribute(attr,saved[attr]);delete saved[attr];}}}
    for(const child of root.childNodes)translate(child);
  };
  const observer=new MutationObserver(records=>{for(const record of records){if(record.type==='characterData')translate(record.target);else for(const node of record.addedNodes)translate(node);}});
  translate(document.body);observer.observe(document.body,{childList:true,subtree:true,characterData:true});
  const apply=platform.applyPreferences.bind(platform);platform.applyPreferences=(...args)=>{const result=apply(...args);translate(document.body);return result;};
  return {dispose(){observer.disconnect();}};
}
