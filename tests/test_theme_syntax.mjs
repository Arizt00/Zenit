import test from 'node:test';import assert from 'node:assert/strict';
import {monacoThemeRules,tokenColor,terminalTheme} from '../web/src/theme-tokens.js';
import {textMateTheme} from '../web/src/textmate.js';
test('RGBA and short syntax colours composite over the actual editor background',()=>{
 assert.equal(tokenColor('#0008','#fff'),'#777777');assert.equal(tokenColor('#8fa2a0b3','#fdf6e3'),'#b0bbb4');assert.equal(tokenColor('url(x)','#ffffff'),null);
 assert.equal(monacoThemeRules({uiTheme:'vs-dark',data:{colors:{'editor.background':'#00000080'},tokenColors:[{scope:'comment',settings:{foreground:'#ffffff80'}}]}})[0].foreground,'878787');
 const t={uiTheme:'vs',data:{colors:{'editor.background':'#fdf6e3'},tokenColors:[{scope:'comment',settings:{foreground:'#8fa2a0b3',fontStyle:'italic'}}]}};const rule=monacoThemeRules(t)[0];assert.equal(rule.foreground,'b0bbb4');assert.equal(rule.fontStyle,'italic');assert.equal(textMateTheme({text:'#000000',editor:'#fdf6e3'},t.data.tokenColors).settings.at(-1).settings.foreground,'#b0bbb4');
});
test('All sixteen ANSI theme colours and terminal-specific cursor/selection reach xterm without CSS injection',()=>{
 const colors=Object.fromEntries(['Black','Red','Green','Yellow','Blue','Magenta','Cyan','White','BrightBlack','BrightRed','BrightGreen','BrightYellow','BrightBlue','BrightMagenta','BrightCyan','BrightWhite'].map((n,i)=>['terminal.ansi'+n,'#'+(i+100).toString(16).padStart(6,'0')]));Object.assign(colors,{'terminalCursor.foreground':'#abc','terminal.selectionBackground':'#12345677','terminalCursor.background':'url(x)'});const t=terminalTheme({data:{colors}},{background:'#010203',foreground:'#ffffff',cursorAccent:'#010203'});assert.equal(t.brightBlue,colors['terminal.ansiBrightBlue']);assert.equal(t.blue,colors['terminal.ansiBlue']);assert.equal(t.cursor,'#aabbcc');assert.equal(t.selectionBackground,'#12345677');assert.equal(t.cursorAccent,'#010203');assert.equal(t.background,'#010203');assert.equal(Object.keys(t).length,21);
});
test('Font-only rules clear inherited styles; basic semantic declarations preserve actual colours',()=>{
 const rules=monacoThemeRules({uiTheme:'vs-dark',data:{tokenColors:[null,{scope:'comment',settings:{fontStyle:''}},{scope:'source.python keyword',settings:{foreground:'#ff0000'}}],semanticTokenColors:{'class.declaration':{foreground:'#abc',bold:true},'parameter':{foreground:'#123456',italic:false},'variable:python':'#ff0000'}}});assert.deepEqual(rules,[{token:'comment',fontStyle:''},{token:'class.declaration',foreground:'aabbcc',fontStyle:'bold'},{token:'parameter',foreground:'123456',fontStyle:''}]);
});
