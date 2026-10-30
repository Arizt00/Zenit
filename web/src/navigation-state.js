export class NavigationHistory{
 constructor(limit=64){this.limit=limit;this.rows=[];this.index=-1;}
 push(value){if(!value?.path)return;const at=this.rows[this.index];if(at&&at.path===value.path&&at.line===value.line&&at.column===value.column)return;this.rows.splice(this.index+1);this.rows.push({...value});if(this.rows.length>this.limit)this.rows.shift();this.index=this.rows.length-1;}
 replace(value){if(!value?.path)return;if(this.index>=0)this.rows[this.index]={...value};else this.push(value);}
 move(direction){const next=this.index+direction;if(next<0||next>=this.rows.length)return null;this.index=next;return {...this.rows[next]};}
 removePaths(paths){const affected=row=>paths.some(path=>row.path===path||row.path.startsWith(path+'/')),before=this.rows.slice(0,this.index+1).filter(affected).length;this.rows=this.rows.filter(row=>!affected(row));this.index=Math.min(this.rows.length-1,Math.max(-1,this.index-before));}
}

export function projectURI(rootURI,uri){
 try{
  const root=new URL(rootURI),value=new URL(uri);if(value.protocol!=='file:'||!['','localhost'].includes(value.hostname)||value.search||value.hash)return null;
  const base=decodeURIComponent(root.pathname).replaceAll('\\','/').replace(/\/$/,''),path=decodeURIComponent(value.pathname).replaceAll('\\','/'),windows=/^\/[A-Za-z]:/.test(base),prefix=base+'/';
  if(!(windows?path.toLowerCase().startsWith(prefix.toLowerCase()):path.startsWith(prefix)))return null;
  const relative=path.slice(prefix.length);if(!relative||relative.split('/').some(part=>part==='..'||part==='.git'||part==='.lumen')||relative.includes('\0'))return null;
  return relative;
 }catch{return null;}
}
