/** Editing needs the complete file; a question respects the selected scope. */
export function melodyContext({file='',selection='',scope='selection',editing=false}={}) {
  if(editing)return {content:file,kind:'file'};
  if(scope==='none')return {content:'',kind:'none'};
  if(scope==='selection'&&selection)return {content:selection,kind:'selection'};
  return {content:file,kind:'file'};
}
