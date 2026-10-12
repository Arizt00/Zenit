import test from 'node:test';
import assert from 'node:assert/strict';
import {themePalette,contrastRatio} from '../web/src/extension-theme.js';
test('An extension cannot make shell labels disappear through alpha or low contrast',()=>{
 const {palette:p}=themePalette({uiTheme:'vs',data:{colors:{'editor.background':'#ffffff','editor.foreground':'#fafaff11','sideBar.foreground':'#fafaff','descriptionForeground':'#eeeaff','sideBar.background':'#fff1','terminal.foreground':'#ffffff','list.activeSelectionBackground':'#7744cc','list.activeSelectionForeground':'#aa77dd'},tokenColors:[{scope:'keyword',settings:{foreground:'#fffefe'}}]}});
 for(const key of ['text','secondary','muted'])assert.ok(contrastRatio(p[key],p.surface)>=4.5,key);
 assert.ok(contrastRatio(p['terminal-text'],p['terminal-bg'])>=4.5);assert.ok(contrastRatio(p['selected-text'],p.selected)>=4.5);assert.ok(contrastRatio(p['syntax-keyword'],p.editor)>=4.5);
});
test('A readable theme keeps its intended colours and rejects arbitrary CSS',()=>{
 const {palette:p}=themePalette({uiTheme:'vs',data:{colors:{'editor.background':'#ffffff','editor.foreground':'#123456','sideBar.background':'#fafafa','sideBar.foreground':'#334455','descriptionForeground':'url(https://invalid.example)','button.background':'#6540db'}}});
 assert.equal(p.text,'#123456');assert.equal(p.secondary,'#334455');assert.equal(p.accent,'#6540db');assert.ok(!Object.values(p).some(x=>x.includes('url(')));
});
