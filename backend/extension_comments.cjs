// Extension-owned comment threads, synchronized as plain text with the editor.
module.exports=function(v,host,event){
 const controllers=new Map();let sequence=0;
 v.CommentThreadCollapsibleState={Collapsed:0,Expanded:1};v.CommentMode={Editing:0,Preview:1};v.CommentThreadState={Unresolved:0,Resolved:1};
 function publish(controller){
  clearTimeout(controller.timer);controller.timer=setTimeout(()=>{
   const threads=[...controller.threads.values()].map(t=>({id:t.id,uri:t.uri.toString(),range:t.range,label:t.label||controller.label,collapsibleState:t.collapsibleState,comments:(t.comments||[]).map(c=>({body:typeof c.body==='string'?c.body:c.body?.value||'',author:c.author?.name||'',mode:c.mode}))}));
   host.service?.('comments.update',{id:controller.id,label:controller.label,threads}).catch(error=>console.error(error.message));
  },0);
 }
 v.comments={createCommentController(id,label){
  if(controllers.has(id))throw Error('CommentController duplicado: '+id);
  const controller={id,label,threads:new Map(),createCommentThread(uri,range,comments){
   const identity=String(++sequence),state={uri,range,comments,label:'',collapsibleState:1},thread={id:identity,dispose(){controller.threads.delete(identity);publish(controller);}};
   for(const key of Object.keys(state))Object.defineProperty(thread,key,{enumerable:true,get:()=>state[key],set:value=>{state[key]=value;publish(controller);}});
   controller.threads.set(identity,thread);publish(controller);return thread;
  },dispose(){clearTimeout(controller.timer);controllers.delete(id);host.service?.('comments.update',{id,label,threads:[],disposed:true}).catch(error=>console.error(error.message));}};
  controllers.set(id,controller);return controller;
 }};
 event('commentControl').event(({controller,thread,action})=>{const item=controllers.get(controller)?.threads.get(thread);if(!item)return;if(action==='collapse')item.collapsibleState=0;else if(action==='dispose')item.dispose();});
};
