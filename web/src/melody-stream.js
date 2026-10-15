/** Append-only text at display cadence; never drag a reader back to the bottom. */
export class MelodyStream {
  constructor(element,scroller){
    this.element=element;this.scroller=scroller;this.target='';this.shown=0;this.frame=0;this.follow=true;
    this.node=document.createTextNode('');element.replaceChildren(this.node);
    this.onScroll=()=>{this.follow=scroller.scrollHeight-scroller.scrollTop-scroller.clientHeight<56;};
    scroller.addEventListener('scroll',this.onScroll,{passive:true});
  }
  update(value){
    if(!value.startsWith(this.target)){this.node.data='';this.shown=0;}
    this.target=value;
    if(!this.frame)this.frame=requestAnimationFrame(()=>this.paint());
  }
  paint(){
    this.frame=0;if(!this.element.isConnected)return;
    const reduced=document.documentElement.dataset.motion==='off'||matchMedia('(prefers-reduced-motion: reduce)').matches;
    const remaining=this.target.length-this.shown;
    // Catch up within a few frames even when providers return large chunks.
    let end=reduced?this.target.length:Math.min(this.target.length,this.shown+Math.max(12,Math.ceil(remaining*.45)));
    if(end<this.target.length&&/[\uD800-\uDBFF]/.test(this.target[end-1]))end++;
    this.node.appendData(this.target.slice(this.shown,end));this.shown=end;
    if(this.follow)this.scroller.scrollTop=this.scroller.scrollHeight;
    if(end<this.target.length)this.frame=requestAnimationFrame(()=>this.paint());
  }
  finish(){cancelAnimationFrame(this.frame);this.frame=0;this.node.appendData(this.target.slice(this.shown));this.shown=this.target.length;}
  dispose(){this.finish();this.scroller.removeEventListener('scroll',this.onScroll);}
}
