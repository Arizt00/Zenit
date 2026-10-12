// Real extension status items: setters update the shared IDE service, not a stub.
module.exports=function(v,host){
  let sequence=0;
  function item(kind,id,selector,alignment=1,priority=0){
    const key=kind+':'+(++sequence),state={id:id||key,selector,alignment,priority,visible:kind==='language',text:'',severity:0,busy:false};
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
    const key='output:'+(++sequence),log=options?.log===true,state={key,name:String(name),text:'',log,logLevel:v.LogLevel.Info,visible:false};
    let disposed=false,scheduled=false;
    const changed=new v.EventEmitter(),send=()=>{if(scheduled||disposed)return;scheduled=true;queueMicrotask(()=>{scheduled=false;if(!disposed)host.service('output.update',state).catch(e=>console.error(e.message));});};
    const channel={name:state.name,append(value){state.text=(state.text+String(value)).slice(-64000);send();},appendLine(value){this.append(String(value)+'\n');},replace(value){state.text=String(value).slice(-64000);send();},clear(){state.text='';send();},show(preserveFocus=false){state.visible=true;state.preserveFocus=preserveFocus;state.reveal=(state.reveal||0)+1;send();},hide(){state.visible=false;send();},dispose(){disposed=true;changed.dispose();host.service('output.dispose',{key}).catch(e=>console.error(e.message));}};
    if(log){channel.logLevel=state.logLevel;channel.onDidChangeLogLevel=changed.event;for(const [method,level] of Object.entries({trace:1,debug:2,info:3,warn:4,error:5}))channel[method]=(...values)=>{if(level<state.logLevel)return;const message=values.map(x=>x instanceof Error?x.stack||x.message:typeof x==='object'?JSON.stringify(x):String(x)).join(' ');channel.appendLine(new Date().toISOString()+' ['+method+'] '+message);};}
    send();return channel;
  };
};
