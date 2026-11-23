import test from 'node:test';
import assert from 'node:assert/strict';
import {languageConfiguration} from '../web/src/language-configuration.js';
import {SemanticStyles} from '../web/src/semantic-styles.js';
import {fileIcon,setFileIcons} from '../web/src/icons.js';

test('Declared bracket pairs, comments and Enter indentation reach Monaco as usable rules',()=>{
 const config=languageConfiguration({brackets:[['{','}'],['[',']'],['(',')']],comments:{lineComment:'//'},indentationRules:{increaseIndentPattern:'\\{$',decreaseIndentPattern:'^\\s*\\}'},onEnterRules:[{beforeText:'\\{$',afterText:'^\\}',action:{indent:'indentOutdent'}}]});
 assert.deepEqual(config.brackets,[['{','}'],['[',']'],['(',')']]);assert.equal(config.comments.lineComment,'//');assert.ok(config.indentationRules.increaseIndentPattern.test('main {'));assert.equal(config.onEnterRules[0].action.indentAction,2);assert.ok(config.onEnterRules[0].afterText.test('}'));
 assert.equal(languageConfiguration({wordPattern:'[',onEnterRules:[{beforeText:'[',action:{indent:'indent'}}]}).onEnterRules.length,0);
});

test('Custom nC semantic categories use scope mappings and language-specific modifier overrides',()=>{
 const styles=new SemanticStyles();styles.configure({semanticTokenTypes:[{id:'pointerType',superType:'type'}],semanticTokenScopes:[{language:'nc',scopes:{pointerType:['support.type.nc.pointer'],modeKernel:['keyword.other.nc.mode.kernel']}}]});
 styles.setTheme({data:{tokenColors:[{scope:'support.type',settings:{foreground:'#123456'}},{scope:'keyword',settings:{foreground:'#987654'}}],semanticTokenColors:{'pointerType.readonly:nc':{foreground:'#abcdef',bold:true},'*.deprecated':{strikethrough:true}}}},{editor:'#fff',keyword:'#112233'});
 assert.equal(styles.resolve('pointerType',[],'nc').foreground,'#123456');assert.deepEqual(styles.resolve('pointerType',['readonly','deprecated'],'nc'),{foreground:'#abcdef',fontStyle:'bold strikethrough'});assert.equal(styles.resolve('modeKernel',[],'nc').foreground,'#987654');assert.equal(styles.resolve('unknown',[],'nc'),null);
});

test('Semantic rewriting keeps offsets after unmapped tokens and recolours existing slots on theme changes',()=>{
 let changes=0;const styles=new SemanticStyles(()=>changes++),legend={tokenTypes:['keyword','unknown','number'],tokenModifiers:[]};styles.setTheme(null,{keyword:'#ff0000',number:'#0000ff',text:'#111111'});
 const tokens=styles.rewrite([0,1,2,0,0,0,4,1,1,0,1,3,2,2,0],legend,'nc');assert.deepEqual([...tokens],[0,1,2,0,0,1,3,2,1,0]);assert.equal(changes,1);
 styles.setTheme(null,{keyword:'#00ff00',number:'#ff00ff',text:'#eee'});assert.equal(styles.rules[0].foreground,'00ff00');assert.equal(styles.rules[1].foreground,'ff00ff');assert.deepEqual([...styles.rewrite([0,1,2,0,0],legend,'nc')],[0,1,2,0,0]);assert.equal(changes,1);
});

test('Language-owned JetBrains colour pairs follow light/dark mode without affecting other languages',()=>{
 const styles=new SemanticStyles();styles.configure({languageStyles:[{light:{semanticTokenColors:{'printFunction:nc':'#0284c7'}},dark:{semanticTokenColors:{'printFunction:nc':'#22d3ee'}}}]});
 styles.setTheme(null,{editor:'#fff'},'light');assert.equal(styles.resolve('printFunction',[],'nc').foreground,'#0284c7');assert.equal(styles.resolve('printFunction',[],'python'),null);
 styles.setTheme(null,{editor:'#111'},'dark');assert.equal(styles.resolve('printFunction',[],'nc').foreground,'#22d3ee');assert.equal(styles.resolve('printFunction',[],'python'),null);
});

test('nC file variants retain the package-specific icons with an unrelated global icon theme',()=>{
 const extensions=['n','nm','nb','nbb','ncp','nbo','init'],native={id:'nc:icons',definitions:Object.fromEntries(extensions.map((e,i)=>[e,'data:image/svg+xml;base64,'+Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg"><text>${i}</text></svg>`).toString('base64')])),fileExtensions:Object.fromEntries(extensions.map(e=>[e,e]))};
 setFileIcons({id:'other',definitions:{}},'light',p=>p.endsWith('.init')?'nc-target-init':'nc',native);const icons=extensions.map(e=>fileIcon('file.'+e));assert.equal(new Set(icons).size,7);assert.ok(icons.every(x=>x.includes('data:image/svg+xml')));
 setFileIcons('none','dark',()=>'',native);assert.equal(fileIcon('file.n'),'');setFileIcons(null);
});
