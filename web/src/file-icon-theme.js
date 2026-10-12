const esc=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const MAPS=['fileNames','fileExtensions','languageIds','folderNames','folderNamesExpanded','rootFolderNames','rootFolderNamesExpanded'];

/** VS Code association priority; each variant overlays, rather than replaces, its base. */
export function iconAssociations(theme,kind='dark'){
  const variant=kind==='light'?theme.light:kind==='contrast'?theme.highContrast:null,result={...theme,...variant};
  for(const key of MAPS)result[key]={...theme[key],...variant?.[key]};
  return result;
}
export function resolveIcon(theme,path,{folder=false,expanded=false,root=false,language='',kind='dark'}={}){
  if(!theme||theme==='none')return null;
  const a=iconAssociations(theme,kind),parts=String(path).replaceAll('\\','/').toLowerCase().split('/').filter(Boolean),name=parts.at(-1)||'',parent=parts.at(-2),specific=parent?parent+'/'+name:null;
  const match=map=>specific&&map?.[specific]||map?.[name];let id;
  if(folder){
    if(root)id=expanded?(match(a.rootFolderNamesExpanded)||match(a.rootFolderNames)||a.rootFolderExpanded||a.rootFolder):(match(a.rootFolderNames)||a.rootFolder);
    id ||= expanded?(match(a.folderNamesExpanded)||match(a.folderNames)||a.folderExpanded||a.folder):(match(a.folderNames)||a.folder);
  }else{
    id=match(a.fileNames);const suffixes=name.split('.').slice(1).map((_,i)=>name.split('.').slice(i+1).join('.'));
    for(const suffix of suffixes)if(!id&&parent)id=a.fileExtensions?.[parent+'/'+suffix];
    for(const suffix of suffixes)if(!id)id=a.fileExtensions?.[suffix];
    id ||= a.languageIds?.[language.toLowerCase()]||a.file;
  }
  return theme.definitions?.[id]||null;
}
export function themeIcon(theme,path,options={}){
  let value=resolveIcon(theme,path,options);
  if(value?.fontCharacter){const fallback=theme.definitions?.[iconAssociations(theme,options.kind).file];value={...(typeof fallback==='object'?fallback:{}),...value};}
  if(typeof value==='string'&&/^data:image\/(?:svg\+xml|png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+$/.test(value))return `<span class="file-type extension-file-icon"><img src="${esc(value)}" alt="" draggable="false"></span>`;
  if(value?.fontCharacter){const index=theme.fonts?.findIndex(f=>f.id===value.fontId);if(index<0||index===undefined)return '';const family=fontFamily(theme,index),color=/^#[a-fA-F0-9]{3,8}$/.test(value.fontColor)?value.fontColor:'currentColor',requestedSize=value.fontSize||theme.fonts[index].size,size=/^(?:[5-9][0-9]|1[0-9]{2}|200)%$/.test(requestedSize)?requestedSize:'100%';return `<span class="file-type extension-font-icon" aria-hidden="true" style="font-family:${family};color:${color};font-size:${size}">${esc(value.fontCharacter)}</span>`;}
  return '';
}
function fontFamily(theme,index){let hash=2166136261;for(const c of String(theme.id))hash=Math.imul(hash^c.charCodeAt(0),16777619);return 'zenitIcons'+(hash>>>0).toString(16)+'_'+index;}
let faces=[],generation=0;
export function installIconFonts(theme){
  const epoch=++generation;if(typeof document==='undefined'||typeof FontFace==='undefined')return;
  for(const face of faces)document.fonts.delete(face);faces=[];
  for(const [index,font] of (theme?.fonts||[]).entries()){
    if(!/^data:font\/(?:woff2?|otf|ttf);base64,[A-Za-z0-9+/=]+$/.test(font.data))continue;
    const descriptors={};if(['normal','bold','100','200','300','400','500','600','700','800','900'].includes(font.weight))descriptors.weight=font.weight;if(['normal','italic','oblique'].includes(font.style))descriptors.style=font.style;
    const face=new FontFace(fontFamily(theme,index),`url("${font.data}")`,descriptors);faces.push(face);
    face.load().then(()=>{if(epoch===generation)document.fonts.add(face);}).catch(()=>{});
  }
}
