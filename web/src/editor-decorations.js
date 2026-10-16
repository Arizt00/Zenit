/** Render extension decorations in the real Monaco model, including split views. */
export class EditorDecorations {
  constructor(host){this.host=host;this.items=new Map();this.counter=0;}
  sync(values=[]){
    const wanted=new Set();for(const value of values){const key=value.extension+':'+value.key+':'+value.path;wanted.add(key);const model=this.host.editor.models.get(value.path)?.model,signature=JSON.stringify(value);let old=this.items.get(key);if(old?.model===model&&old.signature===signature)continue;this.remove(key);if(!model||model.isDisposed())continue;
      const style=document.createElement('style'),className='zenit-decoration-'+(++this.counter),rules=[];
      const rule=(options,name)=>{const node=document.createElement('span'),theme=document.documentElement.dataset.theme,render={...options,...options[theme==='day'?'light':'dark']};
        for(const field of ['color','backgroundColor','borderColor','borderWidth','borderStyle','borderRadius','outlineColor','outlineWidth','outlineStyle','fontStyle','fontWeight','textDecoration','letterSpacing','opacity']){const value=render[field];if(typeof value==='string'&&!/[{};<>]|url\s*\(/i.test(value))node.style[field]=value;else if(value?.id){const color=this.host.editor.extensionTheme?.data?.colors?.[value.id];if(/^#[\da-f]{3,8}$/i.test(color||''))node.style[field]=color;}}
        rules.push('.'+name+'{'+node.style.cssText+'}');return render;};
      const base=rule(value.options||{},className),decorations=value.ranges.map((entry,i)=>{const range=entry.range||entry,options={className,isWholeLine:!!base.isWholeLine,stickiness:base.rangeBehavior??0};
        if(entry.hoverMessage)options.hoverMessage=(Array.isArray(entry.hoverMessage)?entry.hoverMessage:[entry.hoverMessage]).map(x=>({value:typeof x==='string'?x:x.value||'',isTrusted:false}));
        if(base.overviewRulerColor)options.overviewRuler={color:base.overviewRulerColor,lane:base.overviewRulerLane||7};
        if(entry.renderOptions){const name=className+'-'+i;rule({...base,...entry.renderOptions},name);options.className=name;}
        return {range:{startLineNumber:range.start.line+1,startColumn:range.start.character+1,endLineNumber:range.end.line+1,endColumn:range.end.character+1},options};});
      style.textContent=rules.join('\n');document.head.append(style);const ids=model.deltaDecorations([],decorations);this.items.set(key,{model,ids,style,signature});
    }
    for(const key of this.items.keys())if(!wanted.has(key))this.remove(key);
  }
  remove(key){const item=this.items.get(key);if(!item)return;if(!item.model.isDisposed())item.model.deltaDecorations(item.ids,[]);item.style.remove();this.items.delete(key);}
  dispose(){for(const key of this.items.keys())this.remove(key);}
}
