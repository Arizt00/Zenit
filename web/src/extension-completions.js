// VS Code and Monaco use different numeric values for completion kinds.
const kinds='Text Method Function Constructor Field Variable Class Interface Module Property Unit Value Enum Keyword Snippet Color File Reference Folder EnumMember Constant Struct Event Operator TypeParameter User Issue'.split(' ');

export function monacoCompletion(item,{monaco,range,mapRange}){
 const edit=item.textEdit,ownRange=item.range;
 const paired=ownRange?.inserting?{insert:mapRange(ownRange.inserting),replace:mapRange(ownRange.replacing)}:edit?.insert?{insert:mapRange(edit.insert),replace:mapRange(edit.replace)}:null;
 const insert=item.insertText,label=typeof item.label==='object'?item.label.label:item.label;
 const result={...item,kind:monaco.languages.CompletionItemKind[kinds[item.kind]]??monaco.languages.CompletionItemKind.Text,
  insertText:edit?.newText??(typeof insert==='object'?insert.value:insert??label),
  insertTextRules:typeof insert==='object'?monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet:item.insertTextRules,
  documentation:typeof item.documentation==='object'?{value:item.documentation.value,isTrusted:false}:item.documentation,
  range:paired||mapRange(edit?.range||edit?.replace||ownRange)||range,
  additionalTextEdits:item.additionalTextEdits?.map(e=>({range:mapRange(e.range),text:e.newText}))};
 delete result.textEdit;return result;
}

export function completionDetails(initial,resolved,options){
 // Resolving may enrich documentation, commands and extra edits, but must not
 // replace the sorting/filtering or primary edit of an already displayed item.
 const result={...initial};
 for(const key of ['detail','command'])if(resolved?.[key]!==undefined)result[key]=resolved[key];
 if(resolved?.documentation!==undefined)result.documentation=typeof resolved.documentation==='object'?{value:resolved.documentation.value,isTrusted:false}:resolved.documentation;
 if(resolved?.additionalTextEdits!==undefined)result.additionalTextEdits=resolved.additionalTextEdits.map(e=>({range:options.mapRange(e.range),text:e.newText}));
 return result;
}

export function completionProviders(providers){
 const grouped=new Map();
 return providers.flatMap(provider=>{
  if(provider.kind!=='completion')return [provider];
  const previous=grouped.get(provider.language);
  if(previous){previous.triggers=[...new Set([...previous.triggers,...provider.triggers||[]])];return [];}
  const value={...provider,triggers:[...provider.triggers||[]]};grouped.set(provider.language,value);return [value];
 });
}
