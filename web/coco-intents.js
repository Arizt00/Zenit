/** Keep unacknowledged execution identities across reloads of this browser tab.
 * No invitation, credential, source or output is stored here. */
export class CoCoRunIntents {
  constructor(storage=globalThis.sessionStorage){this.storage=storage;this.items=new Map();this.key=null;}
  configure(room){
    const key='coco:run-intents:'+room;if(key===this.key)return;this.items.clear();this.key=key;
    try{const rows=JSON.parse(this.storage?.getItem(key)||'[]');if(Array.isArray(rows))for(const [path,requestId] of rows.slice(-128))if(typeof path==='string'&&path.length<=600&&typeof requestId==='string'&&requestId.length<=120)this.items.set(path,{requestId});}catch{}
  }
  persist(){try{this.storage?.setItem(this.key,JSON.stringify([...this.items].map(([path,item])=>[path,item.requestId])));}catch{}}
  get(path){return this.items.get(path);}
  set(path,intent){if(this.items.size>=128&&!this.items.has(path))throw Error('Hay demasiadas ejecuciones pendientes de confirmar. Reconecta antes de iniciar otras.');this.items.set(path,intent);this.persist();return this;}
  delete(path){const deleted=this.items.delete(path);this.persist();return deleted;}
  clear(){this.items.clear();if(this.key)try{this.storage?.removeItem(this.key);}catch{}this.key=null;}
}
