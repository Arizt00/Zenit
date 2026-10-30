"""Installed nC/Jupyter packages, real compiler, real selected terminals and UI."""
import json,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from backend.runtime_paths import find_tool
from playwright.sync_api import sync_playwright,expect
profile=Path.home()/'AppData/Local/Temp/ze-audit-1022';ws=ROOT/'qa-output/installed-extension-audit/project';out=ROOT/'qa-output/installed-extension-audit/ui';out.mkdir(exist_ok=True)
app=Application(ROOT,ws,data_dir=profile);app.workspace.trusted=True;f=app.features
f.workbenches._write(app.workspace,{'schema':1,'workspace':str(app.workspace.root),'session':None,'spaces':[],'target':'local'})
f.studio.update({'onboarded':True});f.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'security.confirmRoutineActions':False})
review=f.extensions.inspect_file(ROOT/'qa-output/nc-language-1.0.0-21v.zenit.2.vsix');f.extensions.install(review['ticket'],True)
(ws/'one.py').write_text('print("ONE_OUTPUT_ONLY")\n');(ws/'two.py').write_text('print("TWO_OUTPUT_ONLY")\n')
f.extension_runtime.approvals={};f.extension_runtime.start(app.workspace,'nc-lang.nc-language',True);f.extension_runtime.start(app.workspace,'ms-toolsai.jupyter',True)
server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start();checks=[];errors=[]
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
  def inject(route):
   response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get platform(){return platformUI},get preview(){return previewUI},get editor(){return editor},get studio(){return studio},openFile};')
  page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady')
  page.locator('[data-file="main.n"]').click();page.wait_for_function('__qa.preview?.runtimeCommands?.has("nc-lang.nc-language:nc.showProjectGraph")')
  page.evaluate('__qa.platform.pluginCommand("nc-lang.nc-language:nc.showProjectGraph")');expect(page.locator('.code-detail-panel')).to_contain_text('Project graph',timeout=20000);page.screenshot(path=str(out/'nc-project-graph.png'));page.locator('[data-detail-close]').click();checks.append('Actual nC project graph opens in persistent code detail, without leaving the source')
  infos=[]
  for file,label in [('one.py','ONE_OUTPUT_ONLY'),('two.py','TWO_OUTPUT_ONLY')]:
   page.locator(f'[data-file="{file}"]').click();info=page.evaluate('async()=>{const p=__qa.platform,profiles=await p.api("/terminals/profiles");return p.openTerminal(profiles.profiles[0].id)}')
   infos.append(info['id']);page.locator('.pty-run-file').click();page.wait_for_function('(x)=>__qa.platform.terminals.get(x).execution?.running===false',arg=info['id'],timeout=30000)
   session=f.terminals.get(info['id']);assert label in session.output,session.output
   assert ('TWO_OUTPUT_ONLY' if label.startswith('ONE') else 'ONE_OUTPUT_ONLY') not in session.output
  checks.append('Each selected shell receives only its current file output through the visible Run button; both shells remain alive');page.screenshot(path=str(out/'selected-terminal.png'))
  page.evaluate('async(p)=>{await __qa.openFile("one.py");__qa.editor.models.get("one.py").model.setValue(p.code);__qa.platform.selectTerminal(p.ids[0]);}',{'ids':infos,'code':'import time\nprint("ONE_RUNNING",flush=True)\ntime.sleep(30)\n'})
  page.locator('.run-button').click();page.wait_for_function('(id)=>__qa.platform.terminals.get(id).execution?.running===true',arg=infos[0])
  page.evaluate('async(id)=>{await __qa.openFile("two.py");__qa.platform.selectTerminal(id)}',infos[1]);expect(page.locator('.run-button')).to_have_attribute('data-action','run');previous=page.evaluate('(id)=>__qa.platform.terminals.get(id).execution?.id',infos[1]);page.locator('.run-button').click();page.wait_for_function('(p)=>{const e=__qa.platform.terminals.get(p.id).execution;return e&&e.id!==p.previous&&e.running===false}',arg={'id':infos[1],'previous':previous});assert f.terminals.get(infos[0]).execution_channel.state['running']
  page.evaluate('(id)=>__qa.platform.selectTerminal(id)',infos[0]);page.locator('.pty-run-file').click();page.wait_for_function('(id)=>__qa.platform.terminals.get(id).execution?.running===false',arg=infos[0],timeout=10000);assert not f.terminals.get(infos[0]).closed
  checks.append('Main Run follows the selected terminal; a second file can execute while the first remains active and Stop preserves its shell')
  page.locator('[data-file="test.ipynb"]').click();page.wait_for_function('window.lumen.activeFile==="test.ipynb"');page.evaluate('__qa.platform.pluginCommand("ms-toolsai.jupyter:__zenit.notebook")');expect(page.locator('.extension-notebook')).to_be_visible(timeout=15000)
  page.locator('.extension-notebook select').select_option('zenit.local-python');page.locator('[data-notebook-run]').click();expect(page.locator('.extension-notebook-cells pre')).to_contain_text('42',timeout=20000)
  page.locator('[data-notebook-save]').click();page.wait_for_function('!document.querySelector(".extension-notebook header strong").textContent.endsWith(" ·")');saved=json.loads((ws/'test.ipynb').read_text());assert saved['cells'][0]['outputs'][0]['text']=='42\n'
  page.screenshot(path=str(out/'jupyter-cells.png'));page.locator('[data-notebook-cell="0"]').fill('import time; time.sleep(30)');page.locator('[data-notebook-run]').click();expect(page.locator('.extension-notebook-cells pre')).to_have_count(0);page.locator('[data-notebook-interrupt]').click();expect(page.locator('.extension-notebook-cells pre')).to_contain_text('Kernel',timeout=10000);checks.append('Interrupting the real Python kernel completes without blocking the extension host');page.locator('[data-notebook-close]').click();page.wait_for_timeout(600);expect(page.locator('.extension-notebook')).to_have_count(0);checks.append('Actual Jupyter package opens editable cells, runs Python locally, saves nbformat output and closes without reopening')
  page.evaluate('__qa.studio.desktop.handle("foundation")');expect(page.locator('#lab-tab-machines')).to_be_visible(timeout=30000);page.locator('#lab-tab-machines').click();expect(page.locator('.machine-readiness-summary')).to_contain_text('Motor preparado');page.locator('#lab-tab-sdk').click();expect(page.locator('.sdk-system-tools')).to_contain_text('qemu-img');page.screenshot(path=str(out/'qemu-detected.png'));checks.append('Installed QEMU and qemu-img are discovered outside PATH and visible in Machines and SDK');assert not errors,errors;browser.close()
finally:
 server.shutdown();server.server_close();f.shutdown();app.runner.shutdown();(out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':len(checks),'errors':errors},ensure_ascii=False))
