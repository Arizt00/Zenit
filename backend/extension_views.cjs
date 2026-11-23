// Real TreeDataProvider storage: opaque handles retain the extension's own objects.
module.exports=function createViews(vscode,host,extensionOptions){
  const views=new Map(),focusCommands=new Map();let next=0;
  const declarations=new Map(Object.values(extensionOptions?.manifest?.contributes?.views||{}).flat().filter(view=>view.type!=='webview').map(view=>[view.id,view]));
  function registerFocus(id,title){
    if(focusCommands.has(id))return;
    const focus=()=>host.effect({treeView:id});focus.vscodeCommand=true;
    focusCommands.set(id,host.registerCommand(id+'.focus',focus,'Abrir '+title));
  }
  // VS Code contributes the focus command before a lazy provider is created.
  // Keep it available even when a conditional view has no provider yet.
  for(const [id,view] of declarations)registerFocus(id,view.name||id);
  function register(id,provider,options={}){
    if(views.has(id))views.get(id).dispose();
    const tree={id,provider,revision:0,elements:new Map(),ids:new Map(),selection:[],visible:true};
    const expand=new vscode.EventEmitter(),collapse=new vscode.EventEmitter(),select=new vscode.EventEmitter(),visibility=new vscode.EventEmitter(),checkbox=new vscode.EventEmitter();
    const subscription=provider.onDidChangeTreeData?.(()=>{tree.revision++;});
    tree.title=declarations.get(id)?.name||id;registerFocus(id,tree.title);
    const view={onDidChangeCheckboxState:checkbox.event,onDidExpandElement:expand.event,onDidCollapseElement:collapse.event,onDidChangeSelection:select.event,onDidChangeVisibility:visibility.event,get selection(){return tree.selection;},get visible(){return tree.visible;},reveal:async element=>{if(!tree.ids.has(element))throw Error('Carga el elemento de la vista antes de revelarlo.');tree.selection=[element];select.fire({selection:tree.selection});},dispose(){subscription?.dispose();if(!declarations.has(id)){focusCommands.get(id)?.dispose();focusCommands.delete(id);}expand.dispose();collapse.dispose();select.dispose();visibility.dispose();checkbox.dispose();views.delete(id);}};
    Object.assign(tree,{view,expand,collapse,select,visibility,checkbox,dispose:view.dispose});views.set(id,tree);return view;
  }
  async function children(id,parent){
    const tree=views.get(id);if(!tree)throw Error('Vista de extensión no registrada: '+id);
    const element=parent?tree.elements.get(parent):undefined;if(parent&&!tree.elements.has(parent))throw Error('El elemento de la vista ya no existe. Actualiza la vista.');
    if(element)tree.expand.fire({element});
    const children=await tree.provider.getChildren(element)||[];if(children.length>5000)throw Error('La vista contiene demasiados elementos.');
    const items=[];
    for(const child of children){const item=await tree.provider.getTreeItem(child);let key=tree.ids.get(child);if(!key){key='tree-'+(++next);tree.ids.set(child,key);tree.elements.set(key,child);}const command=item.command?{...item.command,arguments:(item.command.arguments||[]).map(a=>a===child?{$lumenTreeElement:{view:id,key}}:a)}:undefined;items.push({key,label:typeof item.label==='object'?item.label.label:item.label||item.resourceUri?.fsPath||'',description:item.description===true?item.resourceUri?.fsPath:item.description,tooltip:typeof item.tooltip==='object'?item.tooltip.value:item.tooltip,collapsibleState:item.collapsibleState||0,checkboxState:item.checkboxState,contextValue:item.contextValue,command});}
    return {items,revision:tree.revision};
  }
  vscode.TreeItemCheckboxState={Unchecked:0,Checked:1};
  const checkbox=(id,key,state)=>{const tree=views.get(id),element=tree?.elements.get(key);if(!tree?.elements.has(key)||![0,1].includes(state))throw Error('Checkbox unavailable.');tree.checkbox.fire({items:[[element,state]]});tree.revision++;return {changed:true};};
  vscode.window.registerTreeDataProvider=(id,p)=>register(id,p);
  vscode.window.createTreeView=(id,options)=>register(id,options.treeDataProvider,options);
  return {snapshot:()=>[...new Set([...views.keys(),...declarations.keys()])].map(id=>({id,title:views.get(id)?.title||declarations.get(id)?.name||id,revision:views.get(id)?.revision||0,registered:views.has(id)})),children,checkbox,arguments:values=>values.map(v=>{const ref=v?.$lumenTreeElement;if(!ref)return v;const tree=views.get(ref.view);if(!tree?.elements.has(ref.key))throw Error('Elemento de la vista caducado.');return tree.elements.get(ref.key);})};
};
