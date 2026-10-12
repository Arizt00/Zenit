// A bounded Markdown subset for model output. Never executes HTML or loads images.
export function markdownBlocks(text){
 const lines=String(text||'').replaceAll('\r\n','\n').split('\n'),blocks=[];let i=0;
 if(lines.length>5000)return [{kind:'paragraph',text:String(text)}];
 const cells=line=>line.trim().replace(/^\|/,'').replace(/\|$/,'').split(/(?<!\\)\|/).map(s=>s.trim().replaceAll('\\|','|'));
 while(i<lines.length){
  const line=lines[i];if(!line.trim()){i++;continue;}
  const fence=/^\s{0,3}(```+|~~~+)\s*([^\s]*)/.exec(line);
  if(fence){const body=[],mark=fence[1][0],size=fence[1].length;i++;while(i<lines.length&&!new RegExp('^\\s{0,3}'+mark+'{'+size+',}\\s*$').test(lines[i]))body.push(lines[i++]);if(i<lines.length)i++;blocks.push({kind:'code',language:fence[2],text:body.join('\n')});continue;}
  const heading=/^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$/.exec(line);if(heading){blocks.push({kind:'heading',level:heading[1].length,text:heading[2]});i++;continue;}
  if(i+1<lines.length&&line.includes('|')&&/^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[i+1])){
   const header=cells(line),rows=[];i+=2;while(i<lines.length&&lines[i].trim()&&lines[i].includes('|'))rows.push(cells(lines[i++]));blocks.push({kind:'table',header,rows});continue;
  }
  const list=/^\s{0,3}(?:([-+*])|(\d+)\.)\s+(.+)$/.exec(line);if(list){const ordered=!!list[2],items=[];let match;while(i<lines.length&&(match=/^\s{0,3}(?:([-+*])|(\d+)\.)\s+(.+)$/.exec(lines[i]))&&!!match[2]===ordered){items.push(match[3]);i++;}blocks.push({kind:'list',ordered,start:Number(list[2]||1),items});continue;}
  if(/^\s*>/.test(line)){const parts=[];while(i<lines.length&&/^\s*>/.test(lines[i]))parts.push(lines[i++].replace(/^\s*>\s?/,''));blocks.push({kind:'quote',text:parts.join('\n')});continue;}
  if(/^\s*(?:---+|\*\*\*+|___+)\s*$/.test(line)){blocks.push({kind:'rule'});i++;continue;}
  const parts=[line];i++;while(i<lines.length&&lines[i].trim()&&!/^\s{0,3}(?:#{1,6}\s|```|~~~|>|[-+*]\s|\d+\.\s)/.test(lines[i])&&!(i+1<lines.length&&lines[i].includes('|')&&/\|?\s*:?-{3,}/.test(lines[i+1])))parts.push(lines[i++]);blocks.push({kind:'paragraph',text:parts.join('\n')});
 }
 return blocks;
}
export function inlineMarkdown(text,parent){
 const pattern=/(`[^`\n]+`|\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\n]+\*|\[[^\]\n]+\]\([^\s)]+\))/g;let end=0;
 for(const match of String(text).matchAll(pattern)){
  parent.append(document.createTextNode(text.slice(end,match.index)));const value=match[0];let node;
  if(value[0]==='`'){node=document.createElement('code');node.textContent=value.slice(1,-1);}
  else if(value.startsWith('**')||value.startsWith('__')){node=document.createElement('strong');node.textContent=value.slice(2,-2);}
  else if(value[0]==='*'){node=document.createElement('em');node.textContent=value.slice(1,-1);}
  else{const [,label,url]=/^\[([^\]]+)\]\(([^)]+)\)$/.exec(value);try{const parsed=new URL(url);if(!['https:','http:'].includes(parsed.protocol))throw Error();node=document.createElement('a');node.href=parsed.href;node.target='_blank';node.rel='noopener noreferrer';node.textContent=label;}catch{node=document.createTextNode(value);}}
  parent.append(node);end=match.index+value.length;
 }
 parent.append(document.createTextNode(text.slice(end)));return parent;
}
export function renderMarkdown(text,{copy}={}){
 const root=document.createElement('div');root.className='message-rich';
 for(const block of markdownBlocks(text)){
  let node;
  if(block.kind==='code'){
   node=document.createElement('section');node.className='message-code';const header=document.createElement('header'),language=document.createElement('small');language.textContent=block.language||'Código';header.append(language);
   if(copy){const button=document.createElement('button');button.type='button';button.className='copy-code';button.textContent='Copiar';button.onclick=()=>copy(block.text,button);header.append(button);}
   const pre=document.createElement('pre'),code=document.createElement('code');code.textContent=block.text;pre.append(code);node.append(header,pre);
  }else if(block.kind==='table'){
   node=document.createElement('div');node.className='message-table';node.tabIndex=0;node.setAttribute('aria-label','Tabla de la respuesta');const table=document.createElement('table'),head=document.createElement('thead'),row=document.createElement('tr'),body=document.createElement('tbody');
   for(const value of block.header){const cell=document.createElement('th');cell.scope='col';inlineMarkdown(value,cell);row.append(cell);}head.append(row);table.append(head,body);
   for(const values of block.rows){const tr=document.createElement('tr');for(const value of values){const cell=document.createElement('td');inlineMarkdown(value,cell);tr.append(cell);}body.append(tr);}node.append(table);
  }else if(block.kind==='list'){node=document.createElement(block.ordered?'ol':'ul');if(block.ordered)node.start=block.start;for(const value of block.items){const item=document.createElement('li');inlineMarkdown(value,item);node.append(item);}}
  else if(block.kind==='rule')node=document.createElement('hr');
  else{node=document.createElement(block.kind==='heading'?'h'+Math.min(6,block.level+1):block.kind==='quote'?'blockquote':'p');inlineMarkdown(block.text,node);}
  root.append(node);
 }
 return root;
}
