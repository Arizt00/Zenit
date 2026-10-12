import test from 'node:test';
import assert from 'node:assert/strict';
import {themePalette,contrastRatio,applyShellTheme} from '../web/src/extension-theme.js';
test('An extension cannot make shell labels disappear through alpha or low contrast',()=>{
 const {palette:p}=themePalette({uiTheme:'vs',data:{colors:{'editor.background':'#ffffff','editor.foreground':'#fafaff11','sideBar.foreground':'#fafaff','descriptionForeground':'#eeeaff','sideBar.background':'#fff1','terminal.foreground':'#ffffff','list.activeSelectionBackground':'#7744cc','list.activeSelectionForeground':'#aa77dd'},tokenColors:[{scope:'keyword',settings:{foreground:'#fffefe'}}]}});
 for(const key of ['text','secondary','muted'])assert.ok(contrastRatio(p[key],p.surface)>=4.5,key);
 assert.ok(contrastRatio(p['terminal-text'],p['terminal-bg'])>=4.5);assert.ok(contrastRatio(p['selected-text'],p.selected)>=4.5);assert.ok(contrastRatio(p['syntax-keyword'],p.editor)>=4.5);
});
test('A readable theme keeps its intended colours and rejects arbitrary CSS',()=>{
 const {palette:p}=themePalette({uiTheme:'vs',data:{colors:{'editor.background':'#ffffff','editor.foreground':'#123456','sideBar.background':'#fafafa','sideBar.foreground':'#334455','descriptionForeground':'url(https://invalid.example)','button.background':'#6540db'}}});
 assert.equal(p.text,'#123456');assert.equal(p.secondary,'#334455');assert.equal(p.accent,'#6540db');assert.ok(!Object.values(p).some(x=>x.includes('url(')));
});
test('Vira transparent focus borders never become transparent controls; theme button foreground is preserved',()=>{
 const {palette:p}=themePalette({uiTheme:'vs-dark',data:{colors:{'focusBorder':'#FFFFFF00','editor.background':'#263238','editor.foreground':'#D8DFDF','sideBar.background':'#192227','sideBar.foreground':'#5f7a87','input.background':'#303C41','button.foreground':'#000000','button.background':'#80CBC4','list.activeSelectionBackground':'#192227ff','list.activeSelectionForeground':'#80CBC4'}}});
 for(const key of ['accent','focus','logo-light','logo-dark','selected-text','button-text'])assert.match(p[key],/^#[a-f0-9]{6}$/i,key);
 assert.equal(p['button-text'],'#000000');assert.ok(contrastRatio(p.accent,p.surface)>=4.5);assert.ok(contrastRatio(p.focus,p.surface)>=3);assert.ok(contrastRatio(p['soft-text'],p['accent-soft'])>=4.5);assert.ok(contrastRatio(p['button-text'],p['button-end'])>=4.5);assert.ok(contrastRatio(p['selected-text'],p['selection-halo'])>=4.5);
});
test('Each field and chrome foreground uses its actual theme surface, including translucent One Dark Pro values',()=>{
 const {palette:p}=themePalette({uiTheme:'vs-dark',data:{colors:{'editor.background':'#282c34','editor.foreground':'#abb2bf','focusBorder':'#3e4452c3','sideBar.background':'#21252b','sideBar.foreground':'#abb2bfc4','titleBar.activeBackground':'#21252b','input.background':'#1d1f23','button.background':'#404754','list.activeSelectionBackground':'#2c313a','list.activeSelectionForeground':'#d7dae0'}}});
 for(const [fg,bg] of [['field-text','field'],['field-muted','field'],['chrome-accent','header'],['chrome-text','header'],['rail-accent','rail'],['button-text','button-start'],['selected-text','selected']])assert.ok(contrastRatio(p[fg],p[bg])>=4.5,fg);
});
test('Removing an external theme restores the requested native theme and removes only its tokens',()=>{
 const values=new Map([['--unrelated','stable']]),root={dataset:{theme:'forest'},style:{getPropertyValue:key=>values.get(key)||'',setProperty:(key,value)=>values.set(key,value),removeProperty:key=>values.delete(key)}};
 applyShellTheme({id:'one',uiTheme:'vs',data:{}},root,'forest');assert.equal(root.dataset.theme,'day');applyShellTheme(null,root,'forest');assert.equal(root.dataset.theme,'forest');assert.equal(root.dataset.extensionTheme,undefined);assert.deepEqual([...values],[['--unrelated','stable']]);
});
