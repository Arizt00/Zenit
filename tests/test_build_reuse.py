import os,tempfile,time,unittest
from pathlib import Path
from backend.server import Application
from backend.runtime_paths import find_tool

ROOT=Path(__file__).resolve().parents[1]
class BuildReuseTests(unittest.TestCase):
    def test_real_compile_reuses_only_unchanged_inputs_and_always_runs_program(self):
        if not find_tool('gcc'):self.skipTest('GCC unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);ws=root/'project with spaces';ws.mkdir();(ws/'value.h').write_text('#define VALUE 42\n');(ws/'main.c').write_text('#include <stdio.h>\n#include "value.h"\nint main(void){printf("RUN_%d\\n",VALUE);return 0;}\n')
            app=Application(ROOT,ws,data_dir=root/'profile');app.workspace.trusted=True
            def run():
                plan=app.features.runtimes.plan(app.workspace,'main.c');job=app.runner.jobs[app.runner.start(plan['commands'],ws)['job']];deadline=time.monotonic()+30
                while not job.done and time.monotonic()<deadline:time.sleep(.03)
                self.assertTrue(job.done);self.assertEqual(job.code,0,job.output);return job,plan
            try:
                first,plan=run();self.assertFalse(first.reusedBuild);self.assertIn('RUN_42',first.output)
                cache=plan['commands'].build_reuse;self.assertTrue(cache.record.is_file(),str(cache.depfile.read_text())+str(cache.trace));second,_=run();self.assertTrue(second.reusedBuild,second.output);self.assertIn('RUN_42',second.output)
                (ws/'value.h').write_text('#define VALUE 43\n');third,_=run();self.assertFalse(third.reusedBuild);self.assertIn('RUN_43',third.output)
                fourth,_=run();self.assertTrue(fourth.reusedBuild)
                target=Path(plan['target']);target.write_bytes(b'tampered artifact');fifth,_=run();self.assertFalse(fifth.reusedBuild);self.assertIn('RUN_43',fifth.output)
                compile_only=app.features.runtimes.plan(app.workspace,'main.c',debug=True);self.assertTrue(hasattr(compile_only['commands'],'build_reuse'))
                # Flags differ for debug; they cannot reuse the release artifact.
                self.assertFalse(compile_only['commands'].build_reuse.hit(first.environment()))
            finally:app.features.shutdown();app.runner.shutdown()

if __name__=='__main__':unittest.main()
