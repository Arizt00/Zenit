"""Measure independent backend starts with disposable profiles; never boots tools."""
import argparse,json,os,statistics,subprocess,sys,tempfile,time
from pathlib import Path


def sample():
    started=time.perf_counter()
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]));sys.path.insert(0,str(root))
    import cProfile,pstats,threading
    before_import=time.perf_counter()
    from backend.server import Application
    imported=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='zenit-startup-metric-') as directory:
        base=Path(directory);workspace=base/'project';workspace.mkdir();(workspace/'main.py').write_text('print(42)\n')
        profiler=cProfile.Profile();profiler.enable();app=Application(root,workspace,data_dir=base/'profile');profiler.disable()
        ready=time.perf_counter();stats=pstats.Stats(profiler)
        slow=sorted([{'file':Path(file).name,'function':name,'calls':value[1],'cumulativeMs':round(value[3]*1000,3)}
                     for (file,line,name),value in stats.stats.items() if '/backend/' in file.replace('\\','/')],key=lambda item:item['cumulativeMs'],reverse=True)[:20]
        result={'importsMs':round((imported-before_import)*1000,3),'applicationMs':round((ready-imported)*1000,3),
                'totalMs':round((ready-started)*1000,3),'threads':[t.name for t in threading.enumerate()],
                'constructors':slow,'backendTimings':getattr(app,'timings',None).snapshot() if getattr(app,'timings',None) else None}
        app.features.shutdown()
    print(json.dumps(result),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');parser.add_argument('--samples',type=int,default=5);parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.sample:return sample()
    if not 1<=args.samples<=10:parser.error('--samples must be between 1 and 10')
    if not args.output:parser.error('--output is required')
    command=[sys.executable,*(['--python-child'] if getattr(sys,'frozen',False) else []),str(Path(__file__).resolve()),'--sample']
    records=[]
    for _ in range(args.samples):
        result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=45,creationflags=0x08000000 if os.name=='nt' else 0,check=True)
        records.append(json.loads(result.stdout))
    report={'method':'Independent Python processes, disposable empty profiles, OS filesystem caches may be warm; no compiler, language server, guest or model is started.',
            'samples':records,'median':{key:round(statistics.median(r[key] for r in records),3) for key in ('importsMs','applicationMs','totalMs')}}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['median']),flush=True)


if __name__=='__main__':main()
