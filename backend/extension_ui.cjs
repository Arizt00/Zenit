// Real extension status items: setters update the shared IDE service, not a stub.
module.exports=function(v,host){
  let sequence=0;const scope=require('node:crypto').randomUUID(),outputs=new Map();
  function item(kind,id,selector,alignment=1,priority=0){
    const key=kind+':'+scope+':'+(++sequence),state={id:id||key,selector,alignment,priority,visible:kind==='language',text:'',severity:0,busy:false};
    let disposed=false,scheduled=false;
    const send=()=>{if(scheduled||disposed)return;scheduled=true;queueMicrotask(()=>{scheduled=false;if(!disposed)host.service('status.update',{key,kind,...state}).catch(e=>console.error(e.message));});};
    const target={dispose(){disposed=true;host.service('status.dispose',{key}).catch(e=>console.error(e.message));}};
    if(kind==='bar'){target.show=()=>{state.visible=true;send();};target.hide=()=>{state.visible=false;send();};}
    for(const field of ['name','text','detail','tooltip','command','severity','busy','selector','color','backgroundColor','accessibilityInformation'])Object.defineProperty(target,field,{enumerable:true,get:()=>state[field],set:value=>{state[field]=value;send();}});
    Object.defineProperty(target,'id',{value:state.id});send();return target;
  }
  v.LanguageStatusSeverity={Information:0,Warning:1,Error:2};
  v.DebugConfigurationProviderTriggerKind={Initial:1,Dynamic:2};
  v.languages.createLanguageStatusItem=(id,selector)=>item('language',id,selector);
  v.window.createStatusBarItem=(id,alignment,priority)=>typeof id==='string'?item('bar',id,undefined,alignment,priority):item('bar',undefined,undefined,id,alignment);
  v.window.createOutputChannel=(name,options)=>{
    const key='output:'+scope+':'+(++sequence),log=options?.log===true,state={key,name:String(name),text:'',log,languageId:typeof options==='string'?options:undefined,logLevel:v.LogLevel.Info,visible:false};
    let disposed=false,scheduled=false;
    const changed=new v.EventEmitter(),send=()=>{if(scheduled||disposed)return;scheduled=true;queueMicrotask(()=>{scheduled=false;if(!disposed)host.service('output.update',state).catch(e=>console.error(e.message));});};
    const channel={name:state.name,append(value){if(disposed)return;state.text=(state.text+String(value)).slice(-64000);send();},appendLine(value){this.append(String(value)+'\n');},replace(value){if(disposed)return;state.text=String(value).slice(-64000);send();},clear(){if(disposed)return;state.text='';send();},show(preserveFocus=false){if(disposed)return;state.visible=true;state.preserveFocus=preserveFocus;state.reveal=(state.reveal||0)+1;send();},hide(){if(disposed)return;state.visible=false;state.dismiss=(state.dismiss||0)+1;send();},dispose(){disposed=true;outputs.delete(key);changed.dispose();host.service('output.dispose',{key}).catch(e=>console.error(e.message));}};
    if(log){Object.defineProperty(channel,'logLevel',{get:()=>state.logLevel});channel.onDidChangeLogLevel=changed.event;for(const [method,level] of Object.entries({trace:1,debug:2,info:3,warn:4,error:5}))channel[method]=(...values)=>{if(state.logLevel===v.LogLevel.Off||level<state.logLevel)return;const message=values.map(x=>x instanceof Error?x.stack||x.message:typeof x==='object'?JSON.stringify(x):String(x)).join(' ');channel.appendLine(new Date().toISOString()+' ['+method+'] '+message);};}
    outputs.set(key,{channel,state,changed,send});
    send();return channel;
  };
  return {event(name,value){if(name!=='output.control')return;const item=outputs.get(value.key);if(!item)return;if(value.action==='clear')item.channel.clear();else if(value.action==='show')item.channel.show(true);else if(value.action==='logLevel'&&item.state.log&&Number.isInteger(value.level)&&value.level>=0&&value.level<=5&&value.level!==item.state.logLevel){item.state.logLevel=value.level;item.changed.fire(value.level);item.send();}}};
};
