import json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from backend.server import Application
from backend.workspace import ConflictError
from tests.test_hilo_tern import wait

ROOT=Path(__file__).resolve().parents[1]


class EditorDepthTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='zenit-editor-depth-');self.base=Path(self.tmp.name);self.root=self.base/'project';self.root.mkdir()
  self.app=Application(ROOT,self.root,data_dir=self.base/'profile');self.ws=self.app.workspace;self.ws.trusted=True;self.f=self.app.features
 def tearDown(self):self.f.shutdown();self.app.runner.shutdown();self.tmp.cleanup()
 def source(self,path,text):
  file=self.root/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text,encoding='utf-8',newline='');return file
 def git(self,*args):
  from backend.runtime_paths import find_tool
  result=subprocess.run([find_tool('git'),'-c','core.hooksPath='+os.devnull,*args],cwd=self.root,capture_output=True,timeout=15)
  if result.returncode:raise AssertionError(result.stderr.decode('utf-8','replace'))
  return result.stdout
 def init_git(self):
  self.git('init','-q');self.git('config','user.name','Fixture');self.git('config','user.email','fixture@example.invalid');self.git('config','core.autocrlf','false')
 def commit(self):self.git('add','-A');self.git('commit','-qm','fixture')
 def test_search_uses_unsaved_text_utf16_and_filters(self):
  self.source('src/a.py','old saved text\n');self.source('other.py','value\n');r=self.ws.read('src/a.py')
  result=self.f.editor_changes.search(self.ws,{'query':'value','case':True,'include':'src/**','buffers':[{'path':'src/a.py','content':'😀 value value\n','revision':r['revision']}]})
  self.assertEqual(len(result['results']),1);hit=result['results'][0];self.assertTrue(hit['buffer']);self.assertEqual(hit['column'],4);self.assertEqual(hit['endColumn'],9);self.assertEqual(self.root.joinpath('src/a.py').read_text(),'old saved text\n')
 def test_replacement_is_literal_reviewed_and_never_writes_sources(self):
  a=self.source('a.py','Value value valuables (a)\n');self.source('b.py','value\n');revision=self.ws.read('a.py')['revision']
  plan=self.f.editor_changes.preview(self.ws,{'query':'value','replacement':'$1\nnew','word':True,'buffers':[{'path':'a.py','content':'Value value unsaved\n','revision':revision}]})
  self.assertEqual(plan['occurrences'],3);self.assertIn('$1\nnew',plan['files'][0]['after']);self.assertTrue(self.f.editor_changes.verify(self.ws,{'plan':plan['id']})['valid']);self.assertEqual(a.read_text(),'Value value valuables (a)\n')
  a.write_text('external');
  with self.assertRaises(ConflictError):self.f.editor_changes.verify(self.ws,{'plan':plan['id']})
 def test_replacement_bounds_and_paths(self):
  self.source('main.py','x '*10001)
  plan=self.f.editor_changes.preview(self.ws,{'query':'x','replacement':'y'})
  self.assertTrue(plan['limited'])
  with self.assertRaises(ValueError):self.f.editor_changes.verify(self.ws,{'plan':plan['id']})
  with self.assertRaises(PermissionError):self.f.editor_changes.search(self.ws,{'query':'x','buffers':[{'path':'../outside','content':'x'}]})
  self.ws.trusted=False
  with self.assertRaises(PermissionError):self.f.editor_changes.preview(self.ws,{'query':'x','replacement':'y'})
 def test_git_stage_and_unstage_preserve_working_bytes_and_other_staged_changes(self):
  self.init_git();file=self.source('main.py','print(1)\n');self.source('other.py','print(2)\n');self.commit()
  file.write_text('print(3)\n');self.source('other.py','print(4)\n');self.git('add','other.py');before=file.read_bytes();work=self.f.git_workbench
  self.assertTrue(work.snapshot(self.ws)['available']);plan=work.preview(self.ws,{'path':'main.py'});self.assertIn('print(1)',plan['before']);self.assertIn('print(3)',plan['after'])
  work.apply(self.ws,{'plan':plan['id'],'consent':True});self.assertEqual(self.git('show',':main.py'),before);self.assertEqual(self.git('show',':other.py'),b'print(4)\n')
  plan=work.preview(self.ws,{'path':'main.py','scope':'staged'});work.apply(self.ws,{'plan':plan['id'],'consent':True});self.assertEqual(file.read_bytes(),before);self.assertEqual(self.git('show',':main.py'),b'print(1)\n');self.assertEqual(self.git('show',':other.py'),b'print(4)\n')
 def test_git_rejects_stale_files_and_busy_index_without_removing_external_lock(self):
  self.init_git();file=self.source('name with spaces.py','one\n');self.commit();file.write_text('two\n');work=self.f.git_workbench;plan=work.preview(self.ws,{'path':file.name});index=self.root/'.git/index';before=index.read_bytes();file.write_text('three\n')
  with self.assertRaises(ConflictError):work.apply(self.ws,{'plan':plan['id'],'consent':True})
  self.assertEqual(index.read_bytes(),before)
  plan=work.preview(self.ws,{'path':file.name});lock=self.root/'.git/index.lock';lock.write_bytes(b'external owner')
  with self.assertRaises(ConflictError):work.apply(self.ws,{'plan':plan['id'],'consent':True})
  self.assertEqual(lock.read_bytes(),b'external owner');self.assertEqual(index.read_bytes(),before)
 def test_git_unborn_head_and_deletion(self):
  self.init_git();file=self.source('new.py','new\n');work=self.f.git_workbench
  plan=work.preview(self.ws,{'path':'new.py'});work.apply(self.ws,{'plan':plan['id'],'consent':True});file.write_text('later draft\n');plan=work.preview(self.ws,{'path':'new.py','scope':'staged'});work.apply(self.ws,{'plan':plan['id'],'consent':True});self.assertEqual(self.git('ls-files'),b'');self.assertEqual(file.read_text(),'later draft\n')
  self.commit();file.unlink();plan=work.preview(self.ws,{'path':'new.py'});work.apply(self.ws,{'plan':plan['id'],'consent':True});self.assertFalse(file.exists());self.assertEqual(self.git('diff','--cached','--name-only'),b'new.py\n')
 def test_git_does_not_stage_an_unsaved_shared_buffer(self):
  self.init_git();self.source('main.py','one\n');self.commit();self.source('main.py','two\n');plan=self.f.git_workbench.preview(self.ws,{'path':'main.py'});self.f.buffers.update(self.ws,{'path':'main.py','text':'unsaved','saved':False})
  with self.assertRaises(ConflictError):self.f.git_workbench.apply(self.ws,{'plan':plan['id'],'consent':True})
  self.assertEqual(self.git('show',':main.py'),b'one\n')
 def test_git_rename_can_be_reviewed_and_unstaged_without_moving_files(self):
  self.init_git();self.source('old name.py','content\n');self.commit();self.git('mv','old name.py','new name.py');work=self.f.git_workbench
  plan=work.preview(self.ws,{'path':'new name.py','scope':'staged'});self.assertEqual(plan['oldPath'],'old name.py');self.assertEqual(plan['before'],plan['after']);work.apply(self.ws,{'plan':plan['id'],'consent':True})
  self.assertEqual(self.git('show',':old name.py'),b'content\n');self.assertFalse((self.root/'old name.py').exists());self.assertEqual((self.root/'new name.py').read_text(),'content\n')
 def test_failed_tests_rerun_only_failures_and_detect_later_dependency_change(self):
  self.source('calc.py','VALUE=7\n');self.source('tests/test_calc.py','import unittest\nfrom calc import VALUE\nclass Cases(unittest.TestCase):\n def test_ok(self): self.assertEqual(VALUE,7)\n def test_bad(self): self.assertEqual(VALUE,8)\n')
  service=self.f.tests;task=service.start(self.ws,{'framework':'unittest','consent':True});wait(self.f.hilo,task['job']);run=service.snapshot(self.ws,task['run'])['runs'][0];self.assertEqual(run['result']['summary']['failed'],1)
  plan=service.plan(self.ws,{'framework':'unittest','failedRun':task['run']});self.assertEqual(plan['selections'],['tests/test_calc.py::Cases.test_bad'])
  repeat=service.start(self.ws,{'framework':'unittest','failedRun':task['run'],'consent':True});wait(self.f.hilo,repeat['job']);rerun=service.snapshot(self.ws,repeat['run'])['runs'][0];self.assertEqual(len(rerun['result']['results']),1);self.assertEqual(rerun['result']['results'][0]['selector'],'tests/test_calc.py::Cases.test_bad')
  self.source('calc.py','VALUE=8\n');self.assertTrue(service.snapshot(self.ws,repeat['run'])['runs'][0]['stale']);self.assertIn('calc.py',service.snapshot(self.ws,repeat['run'])['runs'][0]['changedSinceRun'])
 def test_test_discovery_reuses_ast_and_invalidates_on_change(self):
  self.source('test_one.py','def test_one(): pass\n')
  with patch('backend.project_tests.ast.parse',wraps=__import__('ast').parse) as parse:
   self.assertEqual(len(self.f.tests.discover(self.ws)['tests']),1);self.f.tests.discover(self.ws);self.assertEqual(parse.call_count,1)
   self.source('test_one.py','def test_one(): pass\ndef test_two(): pass\n');self.assertEqual(len(self.f.tests.discover(self.ws)['tests']),2);self.assertEqual(parse.call_count,2)
 def test_pytest_repeats_multiple_failures_and_keeps_parameter_ids(self):
  self.source('tests/test_values.py','import pytest\n@pytest.mark.parametrize("value",[7,8],ids=["ok.v","bad.v"])\ndef test_value(value): assert value==7\nclass TestOther:\n def test_bad(self): assert False\n')
  with patch('backend.project_tests.python_command',return_value=[sys.executable]),patch.dict(os.environ,{'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}):
   service=self.f.tests;task=service.start(self.ws,{'framework':'pytest','consent':True});wait(self.f.hilo,task['job']);plan=service.plan(self.ws,{'framework':'pytest','failedRun':task['run']})
   self.assertEqual(len(plan['selections']),2);self.assertIn('tests/test_values.py::test_value[bad.v]',plan['selections']);self.assertEqual(plan['commands'][0].count('--selection'),2)
   repeat=service.start(self.ws,{'framework':'pytest','failedRun':task['run'],'consent':True});wait(self.f.hilo,repeat['job']);report=service.snapshot(self.ws,repeat['run'])['runs'][0]['result'];self.assertEqual(len(report['results']),2);self.assertEqual(report['summary']['failed'],2)


if __name__=='__main__':unittest.main()
