import test from 'node:test';
import assert from 'node:assert/strict';
import {commandAppearance} from '../web/src/extension-command-icon.js';
test('Extension leaves convey the actual action instead of a shared extension glyph',()=>{
 assert.equal(commandAppearance({id:'gl.cancelPipeline',title:'Cancel Pipeline'}).glyph,'stop');
 assert.equal(commandAppearance({id:'gl.retryJob',title:'Retry Job'}).glyph,'refresh');
 assert.equal(commandAppearance({id:'gl.downloadArtifacts'}).glyph,'download');
 assert.equal(commandAppearance({id:'gl.viewSecurityFinding'}).glyph,'shield');
 assert.equal(commandAppearance({id:'qa.unknown',icon:'$(debug-start)'}).glyph,'play');
});
test('Declared light/dark images are selected and remote or active markup is never inserted',()=>{
 const image='data:image/png;base64,AAAA';assert.match(commandAppearance({icon:{dark:image}},'forest').logo,/<img alt="" src="data:image\/png/);
 assert.equal(commandAppearance({icon:'https://example.test/icon.png'}).logo,undefined);
 assert.equal(commandAppearance({icon:'<svg onload="alert(1)"/>'}).logo,undefined);
});
