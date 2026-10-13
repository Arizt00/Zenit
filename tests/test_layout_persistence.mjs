import test from 'node:test';
import assert from 'node:assert/strict';
import {defaultLayout,persistedLayout} from '../web/src/layout-state.js';
test('Native detachment is temporary; explicitly hidden panes remain hidden',()=>{
 const state=defaultLayout();state.hidden=['project','console'];state.active.left=null;
 const saved=persistedLayout(state,['project']);assert.deepEqual(saved.hidden,['console']);assert.equal(saved.active.left,'project');
 assert.deepEqual(state.hidden,['project','console']);assert.equal(state.active.left,null);
});
test('Saved groups, floats, collapse and user sizes survive detachment cleanup',()=>{
 const state=defaultLayout();state.sizes={left:300,bottom:180};state.collapsed=['right'];state.hidden=['assistant'];
 state.floating.project={x:120,y:24,width:320,height:480};
 const saved=persistedLayout(state,['assistant']);assert.deepEqual(saved.sizes,state.sizes);assert.deepEqual(saved.groups,state.groups);assert.deepEqual(saved.floating,state.floating);assert.deepEqual(saved.collapsed,['right']);
});
