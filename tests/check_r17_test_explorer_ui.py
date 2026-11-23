"""Real interpreter, unittest/pytest, coverage and Monaco result navigation."""
import argparse,json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'qa-output/r17-test-explorer-ui');out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
 with tempfile.TemporaryDirectory(prefix='zenit-r17-tests-ui-') as tmp:
  base=Path(tmp);ws=base/'project';ws.mkdir();(ws/'tests').mkdir();(ws/'calc.py').write_text('def total():\n return 42\n')
  (ws/'tests/test_calc.py').write_text('import unittest\nfrom calc import total\nclass CalcTests(unittest.TestCase):\n def test_ok(self):\n  self.assertEqual(total(),42)\n def test_failure(self):\n  self.assertEqual(total(),41)\ndef test_pytest_function():\n assert total()==42\n')
  app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.runtimes.config['tools']['python']=sys.executable;app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'security.confirmRoutineActions':False})
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1700,'height':1050});page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady');page.locator('.project-tests-toggle').click();expect(page.locator('.test-inventory-row')).to_have_count(2);assert not app.runner.jobs;checks.append('Test explorer discovers unittest methods without running project code')
    page.locator('[name=coverage]').check();page.locator('.test-run-form >button').click();expect(page.locator('.test-command-review pre')).to_contain_text('test_bridge.py');page.locator('[data-tests-confirm]').click();expect(page.locator('.test-result-row[data-test-status=failed]')).to_have_count(1,timeout=20000);expect(page.locator('.test-result-row[data-test-status=passed]')).to_have_count(1)
    page.locator('[data-tests-coverage]').click();expect(page.locator('.test-coverage-report')).to_contain_text('calc.py');page.screenshot(path=str(out/'unittest-coverage.png'));checks.append('Real unittest failure/pass results and actual coverage appear with reviewed commands')
    page.locator('.test-result-row[data-test-status=failed] [data-result-source]').click();page.wait_for_function('window.lumen.activeFile==="tests/test_calc.py"');expect(page.locator('.test-line-fail')).to_be_visible();page.screenshot(path=str(out/'failure-line.png'));checks.append('Selecting a failure opens its exact source line and a test gutter annotation')
    page.locator('.project-tests-toggle').click();page.locator('[name=framework]').select_option('pytest');expect(page.locator('.test-inventory-row')).to_have_count(3);page.locator('.test-inventory-row').filter(has_text='test_pytest_function').locator('[data-test-single]').click();expect(page.locator('.test-command-review pre')).to_contain_text('test_calc.py::test_pytest_function');page.locator('[data-tests-confirm]').click();expect(page.locator('.test-result-summary strong')).to_have_text('pytest',timeout=15000);expect(page.locator('.test-result-row')).to_have_count(1);expect(page.locator('.test-result-row[data-test-status=passed]')).to_have_count(1);checks.append('Selecting one discovered pytest function runs only that actual test')
    assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8');print('PASS',checks,flush=True)
if __name__=='__main__':main()
