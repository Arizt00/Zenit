import test from 'node:test';
import assert from 'node:assert/strict';
import {fileIcon,setFileIcons} from '../web/src/icons.js';
test('Original nC identity does not replace the selected icons for other languages',()=>{
 const image='data:image/svg+xml;base64,PHN2Zy8+',theme={id:'existing',fileExtensions:{py:'p',js:'j',cpp:'c',java:'a'},definitions:{p:image,j:image,c:image,a:image}};
 setFileIcons(theme,'light');const files=['main.py','app.js','main.cpp','Main.java'],before=files.map(fileIcon);
 for(const name of ['main.nc','main.n','main.nm','main.nbb'])assert.match(fileIcon(name),/assets\/languages\/nc.png/);
 assert.deepEqual(files.map(fileIcon),before);setFileIcons('none');assert.equal(fileIcon('main.nc'),'');setFileIcons(null);
});
