/** Bounded, opt-in measurement. No observers or animation loop exist while idle. */
const percentile=(items,p)=>items.length?items.toSorted((a,b)=>a-b)[Math.min(items.length-1,Math.floor(items.length*p))]:null;
export function installDiagnostics(){
  if(!new URLSearchParams(location.search).has('diagnostics'))return;
  let collecting=false;
  window.zenitDiagnostics=Object.freeze({
    async measure(milliseconds=3000,{sampleFrames=true}={}){
      if(collecting)throw Error('A measurement is already running.');
      collecting=true;const duration=Math.max(250,Math.min(10000,milliseconds));
      const start=performance.now(),frames=[],tasks=[],mutations={},renders=[],canvasEvents=[];
      let previous,raf;const frame=now=>{if(previous!=null)frames.push(now-previous);previous=now;raf=requestAnimationFrame(frame);};if(sampleFrames)raf=requestAnimationFrame(frame);
      const observer=new MutationObserver(records=>{for(const r of records){const node=r.target.nodeType===1?r.target:r.target.parentElement,key=(node?.id?'#'+node.id:node?.classList?.[0]||node?.tagName)+'/'+r.type+(r.attributeName?'/'+r.attributeName:'');mutations[key]=(mutations[key]||0)+1;}});observer.observe(document.body,{subtree:true,attributes:true,characterData:true,childList:true});
      let longTasks;try{longTasks=new PerformanceObserver(list=>tasks.push(...list.getEntries().map(x=>({start:x.startTime,duration:x.duration}))));longTasks.observe({type:'longtask',buffered:false});}catch(_){/* Engine may not expose Long Tasks. */}
      const engines=window.BABYLON?.EngineStore.Instances||[],hooks=engines.map(engine=>{let begin;const a=engine.onBeginFrameObservable.add(()=>begin=performance.now()),b=engine.onEndFrameObservable.add(()=>{if(begin!=null)renders.push(performance.now()-begin);});return ()=>{engine.onBeginFrameObservable.remove(a);engine.onEndFrameObservable.remove(b);};});
      const lost=e=>canvasEvents.push({event:e.type,time:performance.now()-start});document.addEventListener('webglcontextlost',lost,true);document.addEventListener('webglcontextrestored',lost,true);
      try{await new Promise(resolve=>setTimeout(resolve,duration));return {duration:performance.now()-start,frameInterval:{samples:frames.length,median:percentile(frames,.5),p95:percentile(frames,.95),max:frames.length?Math.max(...frames):null},longTasks:tasks,mutations,webgl:{renderSamples:renders.length,medianCpuMs:percentile(renders,.5),p95CpuMs:percentile(renders,.95),contextEvents:canvasEvents,engines:engines.length,surfaces:engines.map(e=>{const c=e.getRenderingCanvas(),gl=c?.getContext('webgl2')||c?.getContext('webgl'),info=gl?.getExtension('WEBGL_debug_renderer_info');return {kind:c?.dataset.glass,renderLoops:e._activeRenderLoops?.length??null,version:e.webGLVersion,renderer:info?gl.getParameter(info.UNMASKED_RENDERER_WEBGL):null,timerQueryAvailable:!!gl?.getExtension('EXT_disjoint_timer_query_webgl2')};})},memory:performance.memory?{used:performance.memory.usedJSHeapSize,total:performance.memory.totalJSHeapSize}:null,canvases:[...document.querySelectorAll('canvas')].map(c=>({kind:c.dataset.glass||c.className,width:c.width,height:c.height,visible:!!c.getClientRects().length})),editors:window.monaco?.editor.getEditors?.().length??null};}
      finally{collecting=false;cancelAnimationFrame(raf);observer.disconnect();longTasks?.disconnect();hooks.forEach(dispose=>dispose());document.removeEventListener('webglcontextlost',lost,true);document.removeEventListener('webglcontextrestored',lost,true);}
    }
  });
}
