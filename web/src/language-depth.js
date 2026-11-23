/** Additional native LSP providers, with per-session requests and stale-result guards. */
export function registerLanguageDepth(p,s){
 const m=window.monaco,ed=p.host.editor;if(!m)return;
 const range=r=>r?new m.Range(r.start.line+1,r.start.character+1,r.end.line+1,r.end.character+1):undefined;
 const position=pos=>({line:pos.lineNumber-1,character:pos.column-1});
 const pathOf=model=>ed.pathFor(model);
 const request=async(method,model,extra={},token)=>{
  if(token?.isCancellationRequested)return null;
  const version=model.getVersionId(),path=pathOf(model);await p.syncLSP(s);
  const value=(await p.api('/lsp/request',{id:s.id,method,params:{textDocument:{uri:p.uriFor(s,path)},...extra}})).result;
  return token?.isCancellationRequested||model.isDisposed()||model.getVersionId()!==version?null:value;
 };
 const locations=rows=>(rows||[]).flatMap(row=>{const path=p.relativeURI(s,row.uri||row.targetUri),r=range(row.range||row.targetSelectionRange||row.targetRange);return path&&r?[{uri:ed.models.get(path)?.model?.uri||m.Uri.parse('file:///'+path),range:r}]:[];});
 for(const language of s.languages){
  if(s.capabilities.referencesProvider)s.disposables.push(m.languages.registerReferenceProvider(language,{provideReferences:async(model,pos,context,token)=>locations(await request('textDocument/references',model,{position:position(pos),context:{includeDeclaration:context.includeDeclaration}},token))}));
  for(const [flag,method,register] of [['implementationProvider','textDocument/implementation','registerImplementationProvider'],['typeDefinitionProvider','textDocument/typeDefinition','registerTypeDefinitionProvider'],['declarationProvider','textDocument/declaration','registerDeclarationProvider']]){
   const member={registerImplementationProvider:'provideImplementation',registerTypeDefinitionProvider:'provideTypeDefinition',registerDeclarationProvider:'provideDeclaration'}[register];
   if(s.capabilities[flag])s.disposables.push(m.languages[register](language,{[member]:async(model,pos,token)=>{const value=await request(method,model,{position:position(pos)},token);return locations(Array.isArray(value)?value:value?[value]:[]);}}));
  }
  if(s.capabilities.documentSymbolProvider)s.disposables.push(m.languages.registerDocumentSymbolProvider(language,{provideDocumentSymbols:async(model,token)=>{
   const value=await request('textDocument/documentSymbol',model,{},token),convert=sym=>({name:sym.name,detail:sym.detail||'',kind:Math.max(0,(sym.kind||1)-1),tags:sym.tags||[],range:range(sym.range||sym.location?.range),selectionRange:range(sym.selectionRange||sym.range||sym.location?.range),children:(sym.children||[]).map(convert)});
   return (value||[]).map(convert).filter(sym=>sym.range);
  }}));
  if(s.capabilities.documentHighlightProvider)s.disposables.push(m.languages.registerDocumentHighlightProvider(language,{provideDocumentHighlights:async(model,pos,token)=>(await request('textDocument/documentHighlight',model,{position:position(pos)},token)||[]).map(h=>({range:range(h.range),kind:Math.max(0,(h.kind||1)-1)}))}));
  if(s.capabilities.foldingRangeProvider)s.disposables.push(m.languages.registerFoldingRangeProvider(language,{provideFoldingRanges:async(model,context,token)=>(await request('textDocument/foldingRange',model,{},token)||[]).map(r=>({start:r.startLine+1,end:r.endLine+1,kind:r.kind==='comment'?m.languages.FoldingRangeKind.Comment:r.kind==='imports'?m.languages.FoldingRangeKind.Imports:undefined}))}));
  const formatting=(method,params)=>async(model,options,token)=>(await request(method,model,{...params(model),options},token)||[]).map(e=>({range:range(e.range),text:e.newText}));
  if(s.capabilities.documentFormattingProvider)s.disposables.push(m.languages.registerDocumentFormattingEditProvider(language,{provideDocumentFormattingEdits:formatting('textDocument/formatting',()=>({}))}));
  if(s.capabilities.renameProvider)s.disposables.push(m.languages.registerRenameProvider(language,{
   resolveRenameLocation:async(model,pos,token)=>{
    if(s.capabilities.renameProvider.prepareProvider){const r=await request('textDocument/prepareRename',model,{position:position(pos)},token);if(!r)return {rejectReason:'El servidor no permite renombrar este símbolo.'};const selected=range(r.range||r);return {range:selected,text:r.placeholder||model.getValueInRange(selected)};}
    const word=model.getWordAtPosition(pos);return word?{range:new m.Range(pos.lineNumber,word.startColumn,pos.lineNumber,word.endColumn),text:word.word}:{rejectReason:'Sitúa el cursor sobre un símbolo.'};
   },
   provideRenameEdits:async(model,pos,newName,token)=>{
    const version=model.getVersionId(),guards=[...ed.models.values()].filter(r=>r.model).map(r=>[r.model,r.model.getVersionId()]);
    const edit=await request('textDocument/rename',model,{position:position(pos),newName},token);if(!edit)return {edits:[]};
    if(guards.some(([m,v])=>m.isDisposed()||m.getVersionId()!==v))throw Error('Un archivo abierto cambió durante el renombrado. Solicítalo de nuevo.');
    return p.reviewedEdits.reviewWorkspace(edit,model,version,'Renombrar símbolo · revisar cambios');
   }
  }));
  if(s.capabilities.codeActionProvider)s.disposables.push(m.languages.registerCodeActionProvider(language,{provideCodeActions:async(model,r,context,token)=>{
   const version=model.getVersionId(),value=await request('textDocument/codeAction',model,{range:{start:position({lineNumber:r.startLineNumber,column:r.startColumn}),end:position({lineNumber:r.endLineNumber,column:r.endColumn})},context:{only:context.only?[context.only]:undefined,diagnostics:(context.markers||[]).map(d=>({message:d.message,source:d.source,code:d.code,severity:({8:1,4:2,2:3,1:4})[d.severity]||3,range:{start:{line:d.startLineNumber-1,character:d.startColumn-1},end:{line:d.endLineNumber-1,character:d.endColumn-1}}}))}},token);
   return {actions:(value||[]).map(action=>({title:action.title,kind:action.kind,isPreferred:action.isPreferred,disabled:action.disabled?.reason,command:{id:'zenit.language.review',title:action.title,arguments:[s.id,action,pathOf(model),version]}})),dispose(){}};
  }}));
 }
}
