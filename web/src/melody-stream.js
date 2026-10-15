/** Append-only text at display cadence; never drag a reader back to the bottom. */
export class MelodyStream {
  constructor(element,scroller){
    this.element=element;this.scroller=scroller;this.target='';this.shown=0;this.frame=0;this.follow=true;this.lastPaint=0;this.credit=0;this.disposed=false;
    this.node=document.createTextNode('');element.replaceChildren(this.node);
    this.onScroll=()=>{this.follow=scroller.scrollHeight-scroller.scrollTop-scroller.clientHeight<56;};
    scroller.addEventListener('scroll',this.onScroll,{passive:true});
  }
  update(value){
    if(this.disposed)return;
    if(!value.startsWith(this.target)){this.node.data='';this.shown=0;this.credit=0;}
    this.target=value;
    if(!this.frame){this.lastPaint=performance.now();this.frame=requestAnimationFrame(now=>this.paint(now));}
  }
  paint(now=performance.now()){
    this.frame=0;if(this.disposed||!this.element.isConnected)return;
    const reduced=document.documentElement.dataset.motion==='off'||matchMedia('(prefers-reduced-motion: reduce)').matches;
    const remaining=this.target.length-this.shown;
    // Time-based cadence is consistent on 60/120/144 Hz displays. Large bursts
    // catch up quickly without revealing half a paragraph in a single frame.
    const elapsed=Math.max(1,Math.min(32,now-this.lastPaint));this.lastPaint=now;
    this.credit+=Math.max(160,remaining/0.12)*elapsed/1000;
    const count=Math.floor(this.credit);this.credit-=count;
    let end=reduced?this.target.length:Math.min(this.target.length,this.shown+count);
    if(end<this.target.length&&/[\uD800-\uDBFF]/.test(this.target[end-1]))end++;
    this.node.appendData(this.target.slice(this.shown,end));this.shown=end;
    if(this.follow)this.scroller.scrollTop=this.scroller.scrollHeight;
    if(end<this.target.length)this.frame=requestAnimationFrame(time=>this.paint(time));
  }
  finish(){cancelAnimationFrame(this.frame);this.frame=0;this.node.appendData(this.target.slice(this.shown));this.shown=this.target.length;}
  dispose(){this.finish();this.disposed=true;this.scroller.removeEventListener('scroll',this.onScroll);}
}
