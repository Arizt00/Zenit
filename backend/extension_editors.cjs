// Actual viewport/selection snapshots from Monaco; no invented visible ranges.
const path=require('node:path');
module.exports=function(v,options,event,makeDocument,documents,setCurrent,decorateEditor=editor=>editor,host){
  const fallback=Object.getOwnPropertyDescriptor(v.window,'activeTextEditor').get;
  const editors=new Map();let visible=[],active,managed=false;
  const range=x=>new v.Range(x.start.line,x.start.character,x.end.line,x.end.character);
  const groupMap=new Map(),tabMap=new Map();let groups=[];
  v.window.tabGroups={get all(){return groups;},get activeTabGroup(){return groups.find(g=>g.isActive)||groups[0];},onDidChangeTabs:event('tabs').event,onDidChangeTabGroups:event('tabGroups').event,close:async values=>{const entries=(Array.isArray(values)?values:[values]).flatMap(x=>x.tabs||[x]);const result=await host.service('editor.closeTabs',{uris:entries.map(t=>t.input.uri)});return result===true;}};
  function updateTabs(state){
    const before=[...tabMap.values()],beforeGroups=[...groups],next=[],seen=new Set(),changed=[];
    const source=state.tabs||state.editors.map(x=>({path:x.path,column:x.column,active:x.active,dirty:x.dirty}));
    for(const item of source){const column=item.column||1;let group=groupMap.get(column);if(!group){group={viewColumn:column,tabs:[],isActive:false};groupMap.set(column,group);}if(!next.includes(group)){group.tabs=[];group.isActive=false;next.push(group);}const uri=v.Uri.file(path.resolve(options.workspace,item.path)),key=column+':'+uri.toString();let tab=tabMap.get(key);if(!tab){tab={label:path.basename(item.path),input:new v.TabInputText(uri),isPreview:false,isPinned:false,group};tabMap.set(key,tab);}const active=!!item.active,dirty=!!item.dirty;if(tab.isActive!==active||tab.isDirty!==dirty)changed.push(tab);tab.isActive=active;tab.isDirty=dirty;group.tabs.push(tab);if(active){group.activeTab=tab;group.isActive=true;}seen.add(key);}
    if(!next.length){let group=groupMap.get(1)||{viewColumn:1,tabs:[],isActive:true};group.tabs=[];group.activeTab=undefined;next.push(group);groupMap.set(1,group);}
    for(const [key,tab] of tabMap)if(!seen.has(key))tabMap.delete(key);groups=next;
    const opened=[...tabMap.values()].filter(t=>!before.includes(t)),closed=before.filter(t=>![...tabMap.values()].includes(t));if(opened.length||closed.length||changed.length)event('tabs').fire({opened,closed,changed});
    const added=groups.filter(g=>!beforeGroups.includes(g)),removed=beforeGroups.filter(g=>!groups.includes(g));if(added.length||removed.length)event('tabGroups').fire({opened:added,closed:removed,changed:groups});
  }
  v.window.onDidChangeTextEditorVisibleRanges=event('visibleRanges').event;
  v.window.onDidChangeTextEditorOptions=event('editorOptions').event;
  v.window.onDidChangeTextEditorViewColumn=event('editorColumn').event;
  Object.defineProperty(v.window,'activeTextEditor',{get:()=>managed?active:fallback.call(v.window)});
  Object.defineProperty(v.window,'visibleTextEditors',{get:()=>managed?[...visible]:fallback.call(v.window)?[fallback.call(v.window)]:[]});
  function update(state){
    const oldActive=active,oldVisible=visible;managed=true;const next=[];const changes=[];
    for(const item of state.editors||[]){
      const uri=v.Uri.file(path.resolve(options.workspace,item.path)),key=uri.toString();
      const old=documents.get(key);
      if(!old||old.getText()!==item.text){
        const doc=makeDocument({uri,text:item.text,language:item.language,dirty:item.dirty,version:(old?.version||0)+1});documents.set(key,doc);
        if(!old)event('open').fire(doc);
        else event('change').fire({document:doc,contentChanges:[{range:new v.Range(new v.Position(0,0),old.positionAt(old.getText().length)),rangeOffset:0,rangeLength:old.getText().length,text:doc.getText()}]});
      }
      let editor=editors.get(item.id);
      if(!editor||editor._uri!==key){
        editor={_uri:key,_state:{},get document(){return documents.get(this._uri);},get visibleRanges(){return this._state.ranges||[];},get selections(){return this._state.selections||[];},get selection(){return this.selections[0];},get options(){return this._state.options||{};},get viewColumn(){return this._state.column;},edit:async callback=>{const edit=new v.WorkspaceEdit();callback({replace:(r,t)=>edit.replace(uri,r,t),insert:(p,t)=>edit.insert(uri,p,t),delete:r=>edit.delete(uri,r)});return v.workspace.applyEdit(edit);}};
        decorateEditor(editor);editors.set(item.id,editor);
      }
      const before=editor._state;
      const selections=item.selections.map(x=>{const s=new v.Selection(x.anchor.line,x.anchor.character,x.active.line,x.active.character);s.anchor=new v.Position(x.anchor.line,x.anchor.character);s.active=new v.Position(x.active.line,x.active.character);if(s.start.isAfter(s.end))[s.start,s.end]=[s.end,s.start];return s;});
      editor._state={ranges:item.visibleRanges.map(range),selections,options:item.options,column:item.column};next.push(editor);
      if(JSON.stringify(before.ranges)!==JSON.stringify(editor._state.ranges))changes.push(['visibleRanges',{textEditor:editor,visibleRanges:editor.visibleRanges}]);
      if(JSON.stringify(before.selections)!==JSON.stringify(selections))changes.push(['selection',{textEditor:editor,selections}]);
      if(JSON.stringify(before.options)!==JSON.stringify(editor.options))changes.push(['editorOptions',{textEditor:editor,options:editor.options}]);
      if(before.column!==editor.viewColumn)changes.push(['editorColumn',{textEditor:editor,viewColumn:editor.viewColumn}]);
    }
    visible=next;active=visible.find((_,i)=>state.editors[i].active);setCurrent(active?.document||null);
    for(const [id,editor] of editors)if(!visible.includes(editor))editors.delete(id);
    if(oldVisible.length!==visible.length||oldVisible.some((x,i)=>x!==visible[i]))event('visibleEditors').fire([...visible]);
    if(oldActive!==active)event('activeEditor').fire(active);
    for(const [name,value] of changes)event(name).fire(value);
    updateTabs(state);
  }
  if(options.editorState)update(options.editorState);else updateTabs({editors:[]});
  return update;
};
