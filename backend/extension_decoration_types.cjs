// Decoration handles are owned by one extension; updates coalesce per editor.
module.exports=function(v,host){
  const scope=require('node:crypto').randomUUID(),types=new Map(),pending=new Map();let next=0,scheduled=false;
  function publish(value){pending.set(value.key+':'+(value.uri?.toString()||''),value);if(scheduled)return;scheduled=true;queueMicrotask(()=>{scheduled=false;for(const value of pending.values())host.service('editor.decorations',value).catch(e=>console.error(e.message));pending.clear();});}
  v.DecorationRangeBehavior={OpenOpen:0,ClosedClosed:1,OpenClosed:2,ClosedOpen:3};
  v.OverviewRulerLane={Left:1,Center:2,Right:4,Full:7};
  v.TextEditorRevealType={Default:0,InCenter:1,InCenterIfOutsideViewport:2,AtTop:3};
  v.TextEditorCursorStyle={Line:1,Block:2,Underline:3,LineThin:4,BlockOutline:5,UnderlineThin:6};
  v.TextEditorLineNumbersStyle={Off:0,On:1,Relative:2,Interval:3};
  v.window.createTextEditorDecorationType=options=>{
    const key='decoration:'+scope+':'+(++next),type={key,dispose(){if(!types.delete(key))return;publish({key,dispose:true});}};types.set(key,{type,options});return type;
  };
  const decorate=editor=>{
    editor.setDecorations=(type,ranges)=>{const entry=types.get(type?.key);if(!entry)throw Error('Decoration type disposed or owned by another extension.');if(!Array.isArray(ranges)||ranges.length>10000)throw Error('Too many editor decorations.');publish({key:type.key,uri:editor.document.uri,options:entry.options,ranges});};
    editor.revealRange=(range,revealType=0)=>host.service('editor.reveal',{uri:editor.document.uri,range,revealType}).catch(e=>console.error(e.message));return editor;
  };
  return decorate;
};
