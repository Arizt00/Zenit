"""Bounded profiling of the real UI; headless samples are not monitor FPS."""
import time
def measure(page,seconds=2,sample_frames=True):
 session=page.context.new_cdp_session(page);session.send('Performance.enable');metrics=lambda:{x['name']:x['value'] for x in session.send('Performance.getMetrics')['metrics']};before=metrics();complete={}
 session.on('Tracing.tracingComplete',lambda event:complete.update(event));session.send('Tracing.start',{'categories':'devtools.timeline','transferMode':'ReturnAsStream'})
 result=page.evaluate('(options)=>zenitDiagnostics.measure(options.duration,{sampleFrames:options.frames})',{'duration':seconds*1000,'frames':sample_frames});result['animations']=page.evaluate('()=>document.getAnimations().map(a=>({target:a.effect?.target?.className||a.effect?.target?.id,name:a.animationName,state:a.playState}))');session.send('Tracing.end');deadline=time.monotonic()+10
 while not complete:
  if time.monotonic()>deadline:raise RuntimeError('Trace did not finish')
  page.wait_for_timeout(20)
 chunks=[]
 while True:
  part=session.send('IO.read',{'handle':complete['stream']});chunks.append(part['data'])
  if part.get('eof'):break
 session.send('IO.close',{'handle':complete['stream']});import json
 trace=json.loads(''.join(chunks));events=trace['traceEvents'];after=metrics();result['cdp']={key:after.get(key,0)-before.get(key,0) for key in ('LayoutCount','RecalcStyleCount','LayoutDuration','RecalcStyleDuration','ScriptDuration','TaskDuration')};result['timeline']={name:{'events':sum(e['name']==name for e in events),'totalMs':sum(e.get('dur',0) for e in events if e['name']==name)/1000} for name in ('Layout','Paint','UpdateLayoutTree','CompositeLayers')};session.detach();return result
