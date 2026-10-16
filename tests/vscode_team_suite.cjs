// Executed by the installed VS Code Extension Test Runner, not a mock API.
const assert=require('node:assert/strict'),fs=require('node:fs'),v=require('vscode');
exports.run=async()=>{
  const {Client}=require('../integrations/team-vscode/extension.cjs');
  const config=JSON.parse(fs.readFileSync(process.env.ZENIT_TEAM_TEST,'utf8')),client=new Client(config.invitation,'VS Code real');
  try{
    await client.start();const entry=[...client.files.values()][0];assert.equal(entry.doc.uri.scheme,'zenit-team');assert.equal(entry.doc.languageId,'python');
    const editor=await v.window.showTextDocument(entry.doc);await editor.edit(builder=>builder.insert(new v.Position(0,0),'# VS Code 🙂\n'));await client.sync();
    const before=await client.request({peer:'native-fixture',vectors:{}}),Y=require('../integrations/team-vscode/vendor/yjs.cjs'),doc=new Y.Doc();Y.applyUpdate(doc,Buffer.from(before.updates[entry.path],'base64'));const vector=Y.encodeStateVector(doc);doc.getText('text').insert(0,'# Zénit λ\n');
    await client.request({peer:'native-fixture',vectors:{},updates:{[entry.path]:Buffer.from(Y.encodeStateAsUpdate(doc,vector)).toString('base64')}});await client.sync();
    assert(entry.doc.getText().includes('# Zénit λ'));assert(entry.doc.getText().includes('# VS Code 🙂'));assert(await entry.doc.save());
    await client.run();assert(entry.doc.getText().includes('print("team")'));fs.writeFileSync(config.report,JSON.stringify({checks:['Actual VS Code loads the VFS document with Python language','VS Code and host exchange concurrent Unicode Yjs edits','Ctrl+S saves the shared buffer on the host','VS Code runs the file in the host environment'],version:v.version},null,2));
  }finally{client.stop();}
};
