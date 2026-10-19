"""Runs in the selected project's interpreter, only after an explicit test action."""
import argparse,inspect,json,os,sys,time,traceback,unittest
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',required=True);parser.add_argument('--output',required=True);parser.add_argument('--framework',choices=('unittest','pytest'),required=True);parser.add_argument('--selection',default='');parser.add_argument('--coverage',action='store_true');args=parser.parse_args()
    root=Path(args.workspace).resolve();output=Path(args.output).resolve();sys.path.insert(0,str(root));os.chdir(root);items=[];started=time.monotonic();coverage=None;data={'results':items,'framework':args.framework,'coverage':None,'error':None}
    def location(test,error=None):
        path=None;line=1
        try:
            method=getattr(test,test._testMethodName);path=Path(inspect.getsourcefile(method)).resolve();line=inspect.getsourcelines(method)[1]
        except (AttributeError,OSError,TypeError):pass
        if error:
            for frame in traceback.extract_tb(error[2]):
                candidate=Path(frame.filename).resolve()
                if candidate.is_relative_to(root):path=candidate;line=frame.lineno
        return {'path':path.relative_to(root).as_posix() if path and path.is_relative_to(root) else None,'line':line}
    class Result(unittest.TextTestResult):
        def startTest(self,test):super().startTest(test);test._zenit_started=time.monotonic()
        def record(self,test,status,error=None,message=''):
            if len(items)>=5000:raise RuntimeError('Se superaron 5000 resultados de pruebas.')
            items.append({'id':test.id(),'name':str(test),'status':status,'seconds':round(time.monotonic()-getattr(test,'_zenit_started',time.monotonic()),4),**location(test,error),'message':(''.join(traceback.format_exception(*error)) if error else message)[-12000:]})
        def addSuccess(self,test):super().addSuccess(test);self.record(test,'passed')
        def addError(self,test,error):super().addError(test,error);self.record(test,'error',error)
        def addFailure(self,test,error):super().addFailure(test,error);self.record(test,'failed',error)
        def addSkip(self,test,reason):super().addSkip(test,reason);self.record(test,'skipped',message=reason)
        def addExpectedFailure(self,test,error):super().addExpectedFailure(test,error);self.record(test,'skipped',error,'Expected failure')
        def addUnexpectedSuccess(self,test):super().addUnexpectedSuccess(test);self.record(test,'failed',message='Unexpected success')
        def addSubTest(self,test,subtest,error):
            super().addSubTest(test,subtest,error)
            if error:self.record(test,'failed',error)
    code=2
    try:
        if args.coverage:
            import coverage as module
            coverage=module.Coverage(data_file=str(output.with_suffix('.coverage')),source=[str(root)],omit=[str(root/'.lumen/*'),str(root/'.venv/*')]);coverage.start()
        if args.framework=='unittest':
            start=root/'tests' if (root/'tests').is_dir() else root;loader=unittest.TestLoader();suite=loader.discover(str(start),pattern='test*.py',top_level_dir=str(root) if (start/'__init__.py').is_file() else str(start))
            def flatten(value):
                for test in value:
                    if isinstance(test,unittest.TestSuite):yield from flatten(test)
                    else:yield test
            if args.selection:
                file,name=args.selection.split('::',1);target=(root/file).resolve();selected=[]
                for test in flatten(suite):
                    loc=location(test)
                    if loc['path']==file and test.id().endswith('.'+name):selected.append(test)
                if not selected:raise ValueError('La prueba seleccionada no se encontró después de descubrir la suite.')
                suite=unittest.TestSuite(selected)
            result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite);code=0 if result.wasSuccessful() and result.testsRun else 1
        else:
            import pytest
            class Reports:
                def pytest_runtest_logreport(self,report):
                    if report.when!='call' and not report.failed and not report.skipped:return
                    if len(items)>=5000:raise RuntimeError('Se superaron 5000 resultados de pruebas.')
                    file,line,name=report.location
                    items.append({'id':report.nodeid,'name':name,'path':file,'line':line+1,'status':'failed' if report.failed else 'skipped' if report.skipped else 'passed','seconds':round(report.duration,4),'message':str(report.longrepr)[-12000:] if report.longrepr else ''})
            selection=args.selection if args.selection else 'tests' if (root/'tests').is_dir() else '.'
            code=int(pytest.main(['-q','--color=no',selection],plugins=[Reports()]))
    except BaseException as error:
        data['error']=str(error)[:2000];traceback.print_exc();code=2
    finally:
        if coverage:
            try:
                coverage.stop();coverage.save();path=output.with_suffix('.coverage.json');coverage.json_report(outfile=str(path));data['coverage']=path.name
            except Exception as error:data['coverageError']=str(error)[:500]
        data.update(code=code,seconds=round(time.monotonic()-started,4),summary={status:sum(i['status']==status for i in items) for status in ('passed','failed','error','skipped')})
        temp=output.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');os.replace(temp,output)
    return code

if __name__=='__main__':raise SystemExit(main())
