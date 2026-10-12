import test from 'node:test';import assert from 'node:assert/strict';
import {resolveIcon,themeIcon} from '../web/src/file-icon-theme.js';
const t={id:'qa:icons',definitions:Object.fromEntries(['name','parent-name','long','short','parent-ext','language','base','folder','expanded','root','root-expanded','special','light','hc'].map(k=>[k,k])),file:'base',folder:'folder',folderExpanded:'expanded',rootFolder:'root',rootFolderExpanded:'root-expanded',fileNames:{'index.d.ts':'name','src/index.d.ts':'parent-name'},fileExtensions:{'d.ts':'long','ts':'short','src/ts':'parent-ext'},languageIds:{python:'language'},folderNames:{src:'special'},folderNamesExpanded:{},light:{file:'light'},highContrast:{file:'hc'}};
test('Icon precedence includes direct parent, filename, longest suffix, language and default',()=>{
 assert.equal(resolveIcon(t,'SRC/INDEX.D.TS'),'parent-name');assert.equal(resolveIcon(t,'lib/index.d.ts'),'name');assert.equal(resolveIcon(t,'src/other.d.ts'),'parent-ext');assert.equal(resolveIcon(t,'lib/other.d.ts'),'long');assert.equal(resolveIcon(t,'lib/other.ts'),'short');assert.equal(resolveIcon(t,'script',{language:'python'}),'language');assert.equal(resolveIcon(t,'unknown'),'base');
});
test('Folder expansion and roots retain fallbacks and specific names',()=>{
 assert.equal(resolveIcon(t,'src',{folder:true}),'special');assert.equal(resolveIcon(t,'lib',{folder:true,expanded:true}),'expanded');assert.equal(resolveIcon(t,'project',{folder:true,root:true}),'root');assert.equal(resolveIcon(t,'project',{folder:true,root:true,expanded:true}),'root-expanded');assert.equal(resolveIcon({...t,rootFolderExpanded:undefined},'project',{folder:true,root:true,expanded:true}),'root');assert.equal(resolveIcon({...t,rootFolder:undefined},'project',{folder:true,root:true}),'folder');
});
test('Light and high contrast override associations without dropping base maps',()=>{
 assert.equal(resolveIcon(t,'unknown',{kind:'light'}),'light');assert.equal(resolveIcon(t,'unknown',{kind:'contrast'}),'hc');assert.equal(resolveIcon(t,'index.d.ts',{kind:'light'}),'name');assert.equal(resolveIcon({...t,light:{fileNames:{'index.d.ts':'light'}}},'index.d.ts',{kind:'light'}),'light');
});
test('Images and glyphs cannot inject markup, remote loaders or CSS',()=>{
 assert.equal(themeIcon({...t,definitions:{base:'https://example.com/a.svg'}},'x'),'');assert.equal(themeIcon({...t,definitions:{base:'data:image/svg+xml;base64,PHN2Zy8+'}},'x').includes('<img'),true);
 const fonts=[{id:'glyphs'}],value={fontCharacter:'<',fontId:'glyphs',fontColor:'url(https://x)',fontSize:'100%;display:none'};const html=themeIcon({...t,fonts,definitions:{base:value}},'x');assert.ok(html.includes('&lt;'));assert.ok(html.includes('color:currentColor'));assert.ok(!html.includes('https://'));assert.equal(themeIcon('none','x'),'');
});
