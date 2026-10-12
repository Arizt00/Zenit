/** Zénit Glass: persistent Babylon rendering and shared optical materials. */
let engineScript;
let crystalGeometry;
function loadCrystalGeometry(){
  return crystalGeometry ||= (async()=>{
    const [info,response]=await Promise.all([fetch('/assets/zenit-crystal.mesh.json').then(r=>{if(!r.ok)throw Error('Metadatos del cristal no disponibles');return r.json();}),fetch('/assets/zenit-crystal.mesh.bin')]);
    if(!response.ok)throw Error('Geometría del cristal no disponible');const buffer=await response.arrayBuffer();if(buffer.byteLength!==info.byteLength||buffer.byteLength>2_000_000)throw Error('Geometría de cristal inválida');
    const digest=await crypto.subtle.digest('SHA-256',buffer),hash=[...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,'0')).join('');if(hash!==info.sha256)throw Error('La geometría del cristal no supera la comprobación de integridad');
    return info.meshes.map(mesh=>({name:mesh.name,positions:new Float32Array(buffer,mesh.positions.byteOffset,mesh.positions.count),normals:new Float32Array(buffer,mesh.normals.byteOffset,mesh.normals.count),indices:new Uint32Array(buffer,mesh.indices.byteOffset,mesh.indices.count)}));
  })().catch(error=>{console.warn('Zénit Glass:',error.message);return null;});
}
function loadBabylon() {
  if (window.BABYLON) return Promise.resolve(window.BABYLON);
  return engineScript ||= new Promise((resolve,reject)=>{
    const script=document.createElement('script');script.src='/vendor/babylon/babylon.js';
    script.onload=()=>resolve(window.BABYLON);script.onerror=()=>{engineScript=null;reject(new Error('Babylon no disponible'));};
    document.head.appendChild(script);
  });
}
export function glassArt(kind='orb', extra='') {
  return `<div class="glass-art ${kind} ${extra}" aria-hidden="true"><div class="glass-aura"></div><div class="glass-fallback"><i></i></div><canvas data-glass="${kind}" tabindex="-1"></canvas></div>`;
}
export async function createLumenScene(canvas, available=true, onStatus=()=>{}) {
  const fallback={kind:'css',setTheme(){},setMotion(){},dispose(){}};
  if(!canvas||!available)return fallback;
  let engine,scene,cleanup=()=>{};
  try {
    const B=await loadBabylon();
    if(!canvas.isConnected||!B.Engine.IsSupported)return fallback;
    engine=new B.Engine(canvas,true,{alpha:true,stencil:false,preserveDrawingBuffer:false,powerPreference:'default',disableWebGL2Support:false},false);
    // Decorative glass does not need to consume every refresh on a 240 Hz display.
    engine.maxFPS=60;
    canvas.dataset.engine=engine.webGLVersion>=2?'WebGL2':'WebGL';
    engine.setHardwareScalingLevel(1/Math.min(devicePixelRatio||1,1.5));
    scene=new B.Scene(engine);scene.useRightHandedSystem=true;scene.skipPointerMovePicking=true;scene.clearColor=new B.Color4(0,0,0,0);
    const hero=canvas.dataset.glass==='hero',welcome=canvas.dataset.glass==='welcome';
    const camera=new B.FreeCamera('glass-camera',new B.Vector3(0,0,8),scene);camera.setTarget(B.Vector3.Zero());
    camera.mode=B.Camera.ORTHOGRAPHIC_CAMERA;camera.minZ=.1;
    const vertexSource=`precision highp float;attribute vec3 position;attribute vec3 normal;
      uniform mat4 worldViewProjection;uniform mat4 world;varying vec3 n;varying vec3 p;
      void main(){n=normalize(mat3(world)*normal);p=position;gl_Position=worldViewProjection*vec4(position,1.);}`;
    const fragmentSource=`precision highp float;varying vec3 n;varying vec3 p;
      uniform float time;uniform float crystal;uniform float shell;
      #ifdef LENS
      uniform sampler2D refractionMap;uniform vec2 resolution;
      #endif
      void main(){
        vec3 N=normalize(vec3(n.x,n.y,abs(n.z)));
        vec2 uv=N.xy;float radius=length(uv),facing=N.z;
        float t=time*.32;float angle=atan(uv.y,uv.x);
        float fresnel=pow(1.-facing,2.4);
        // A thin film changes optical thickness locally; its colours flow without spinning.
        vec2 q=uv+vec2(sin(uv.y*3.+t*.7),cos(uv.x*2.7-t*.6))*.09;
        float thickness=.45+.15*sin(q.x*2.4+q.y*1.9+t*.55)+.065*sin(q.y*4.2-q.x*2.1-t*.4);
        vec3 spectrum=.5+.5*cos(6.2831853*(thickness*(1.2+facing*.3)+vec3(.0,.32,.64)));
        vec3 pearl=vec3(.73,.62,.96),pink=vec3(.99,.75,.91),ice=vec3(.69,.89,.99);
        vec3 mint=vec3(.83,.96,.92),gold=vec3(1.,.97,.82);
        // Advected light fields converge and separate; the shell reflection stays still.
        vec2 a=vec2(-.34+.28*sin(t*.93), .38+.22*cos(t*.73));
        vec2 b=vec2(-.38+.27*cos(t*.81),-.38+.24*sin(t*.89));
        vec2 c=vec2(.04+.14*sin(t*.79+2.),.12+.14*cos(t*.91+1.));
        vec2 d=vec2(.48+.25*cos(t*.87+1.),-.38+.26*sin(t*.67+3.));
        vec2 e=vec2(.40+.32*sin(t*.61+4.),.03+.30*cos(t*.83));
        float p1=exp(-dot(q-a,q-a)*5.5);
        float p2=exp(-dot(q-b,q-b)*4.3);
        float p3=1.65*exp(-dot(q-c,q-c)*7.);
        float p4=exp(-dot(q-d,q-d)*10.);
        float p5=exp(-dot(q-e,q-e)*9.);
        vec3 volume=mix(pearl,ice,clamp(p2*.88,0.,.88));
        volume=mix(volume,pink,clamp((p1*.6+p4)*.85,0.,.86));
        volume=mix(volume,mint,clamp(p5*.42,0.,.46));
        volume=mix(volume,gold,clamp(p3*.48,0.,.8));
        vec3 film=mix(volume,mix(vec3(.90,.88,1.),spectrum,.52),fresnel*.65);
        // Clear central window and a denser curved meniscus, rather than a filled gradient.
        float band=exp(-pow((radius-(.73+.055*sin(angle*2.+t*.32)))*9.,2.));
        float colourWeight=.38+.48*radius+.24*band+.19*fresnel;
        colourWeight+=.13*(p3+p4);
        vec3 color=mix(vec3(.967,.977,1.),film,clamp(colourWeight,0.,.97));
        #ifdef LENS
        vec2 screen=gl_FragCoord.xy/resolution;
        vec2 displacement=uv*(.012+.020*pow(radius,2.));
        vec2 chroma=uv*.0028*fresnel;
        vec4 behind=texture2D(refractionMap,screen-displacement);
        vec3 refracted=vec3(texture2D(refractionMap,screen-displacement-chroma).r,behind.g,texture2D(refractionMap,screen-displacement+chroma).b);
        refracted=clamp(refracted/max(behind.a,.05),0.,1.);
        color=mix(color,refracted,clamp(behind.a*.60,0.,.30));
        #endif
        // Double wall: a lit outer lip, separated from the inner reflected edge.
        float rim=exp(-pow((radius-.984)*95.,2.));
        float inner=exp(-pow((radius-.937)*60.,2.));
        float rimLight=.45+.55*pow(abs(sin(angle-.40)),2.);
        float wallShadow=exp(-pow((radius-.956)*46.,2.))*(.5+.5*sin(angle+.7));
        color-=vec3(.08,.055,.005)*wallShadow;
        color=mix(color,mix(vec3(.88,.85,1.),vec3(1.),rimLight),clamp(rim*.90+inner*.25,0.,.96));
        // Reflected softboxes: long curved highlight, sharp core and warm lower glint.
        vec2 h=uv-vec2(-.62,.65);vec2 hr=vec2(h.x*.76+h.y*.65,-h.x*.65+h.y*.76);
        float mainGlow=exp(-dot(hr*vec2(5.,7.),hr*vec2(5.,7.)));
        float mainSpec=exp(-dot(hr*vec2(24.,6.),hr*vec2(24.,6.)));
        vec2 l=uv-vec2(.52,-.56);vec2 lr=vec2(l.x*.8+l.y*.6,-l.x*.6+l.y*.8);
        float lowerGlow=exp(-dot(lr*vec2(5.,7.),lr*vec2(5.,7.)));
        float lowerSpec=exp(-dot(lr*vec2(22.,7.),lr*vec2(22.,7.)));
        float upperArc=exp(-pow((length((uv-vec2(.04,-.02))*vec2(.95,1.))-.90)*55.,2.))*smoothstep(.3,.8,uv.y)*(1.-smoothstep(-.6,.6,uv.x));
        float lowerArc=exp(-pow((length((uv-vec2(-.12,.07))*vec2(.96,1.05))-.78)*65.,2.))*(1.-smoothstep(-.8,-.15,uv.y))*.32;
        // Small reflected windows and caustic arcs keep the shell optically crisp.
        float sideSpec=exp(-pow((radius-.955)*95.,2.))*exp(-pow((angle+.10)*9.,2.));
        float pinSpec=exp(-dot((uv-vec2(.36,.33))*vec2(34.,80.),(uv-vec2(.36,.33))*vec2(34.,80.)));
        color=mix(color,vec3(1.,.95,.76),lowerGlow*.64+mainGlow*.28);
        float star=exp(-dot(hr*vec2(7.,95.),hr*vec2(7.,95.)))+exp(-dot(hr*vec2(90.,7.),hr*vec2(90.,7.)));
        float highlight=clamp(mainGlow*.40+mainSpec+star*.65+lowerSpec+upperArc*.92+lowerArc+sideSpec*.7+pinSpec*.8,0.,1.);
        color=mix(color,vec3(1.),highlight);
        // Reflected internal sheets sharpen the pearl without rotating its shell.
        float caustic=exp(-pow((length((uv-vec2(-.16,.03))*vec2(.93,1.08))-.82)*34.,2.));
        float sideFilm=exp(-pow((radius-.87)*16.,2.))*(.5+.5*sin(angle*3.+t*.12));
        color=mix(color,mix(pearl,ice,.45+.4*sin(angle+1.)),sideFilm*.48);
        float meniscus=exp(-pow((radius-.925)*28.,2.));
        color=mix(color,mix(pearl,ice,.3+.3*sin(angle*2.)),meniscus*.4);
        color=mix(color,vec3(1.,.98,1.),caustic*.35);
        // Reflection increases opacity only at the glass wall.
        float alpha=.72+fresnel*.13+rim*.10+inner*.04;
        alpha=mix(alpha,.36+fresnel*.22,crystal);
        alpha=max(alpha,highlight*.96);alpha=clamp(alpha,0.,.96);
        if(crystal>.5){
          // Flat face normals define separate optical planes and sharp white edges.
          float face=dot(N,normalize(vec3(-.55,.65,.75)));
          vec3 facet=mix(pearl,ice,clamp(N.x*.7+.4,0.,1.));
          facet=mix(facet,pink,clamp(N.y*.5+.2,0.,.65));
          color=mix(facet,vec3(1.),clamp(.12+face*.48,.0,.72));
          float split=exp(-pow((p.x+p.y*.13)*38.,2.));
          color=mix(color,vec3(1.),split*.52);
          alpha=.43+fresnel*.18+max(face,0.)*.15;
        }
        if(shell>.5){color=mix(ice,vec3(1.),highlight*.7);alpha=.012+pow(1.-facing,7.)*.17+highlight*.02;}
        gl_FragColor=vec4(color*alpha,alpha);
      }`;
    const material=(name,crystal=0)=>{
      const m=new B.ShaderMaterial(name,scene,{vertexSource,fragmentSource},{attributes:['position','normal'],uniforms:['worldViewProjection','world','time','crystal','shell','resolution'],samplers:crystal===0?['refractionMap']:[],defines:crystal===0?['#define LENS']:[],needAlphaBlending:true});
      m.alphaMode=B.Engine.ALPHA_PREMULTIPLIED_PORTERDUFF;m.setFloat('crystal',crystal);m.setFloat('shell',0);m.backFaceCulling=true;return m;
    };
    const geometry=await loadCrystalGeometry(),meshFrom=data=>{const mesh=new B.Mesh(data.name,scene),vertices=new B.VertexData();Object.assign(vertices,{positions:data.positions,normals:data.normals,indices:data.indices});vertices.applyToMesh(mesh);return mesh;};
    const pearl=geometry?meshFrom(geometry[0]):B.MeshBuilder.CreateSphere('melody',{diameter:2.75,segments:96},scene);canvas.dataset.geometry=geometry?'blender-double-wall':'procedural-fallback';
    const pearlMaterial=material('iridescence');pearl.material=pearlMaterial;pearl.alphaIndex=1;
    const materials=[pearlMaterial],crystals=[];let ribbon,innerShell;pearl.position.set(0,0,0);
    if(geometry?.[1]){innerShell=meshFrom(geometry[1]);innerShell.material=material('inner-glass');innerShell.material.setFloat('shell',1);innerShell.alphaIndex=0;materials.push(innerShell.material);}
    if(hero){
      // The floor carries an optical contact shadow and a reflected pool of light.
      const floor=B.MeshBuilder.CreatePlane('pearl-contact',{width:4.4,height:.56},scene);floor.position.set(.05,-1.66,-2.4);
      floor.material=new B.ShaderMaterial('pearl-contact-material',scene,{vertexSource:`precision highp float;attribute vec3 position;attribute vec2 uv;uniform mat4 worldViewProjection;varying vec2 v;void main(){v=uv;gl_Position=worldViewProjection*vec4(position,1.);}`,fragmentSource:`precision highp float;varying vec2 v;void main(){vec2 q=(v-.5)*vec2(2.8,3.4);float a=exp(-dot(q,q)*3.)*.19;vec3 color=vec3(.73,.66,.96);gl_FragColor=vec4(color*a,a);}`},{attributes:['position','uv'],uniforms:['worldViewProjection'],needAlphaBlending:true});floor.material.alphaMode=B.Engine.ALPHA_PREMULTIPLIED_PORTERDUFF;
      const starMaterial=new B.ShaderMaterial('ambient-stars-material',scene,{vertexSource:`precision highp float;attribute vec3 position;attribute vec2 uv;uniform mat4 worldViewProjection;varying vec2 v;void main(){v=uv;gl_Position=worldViewProjection*vec4(position,1.);}`,fragmentSource:`precision highp float;varying vec2 v;void main(){vec2 q=(v-.5)*2.;float a=exp(-dot(q,q)*8.)*.7+exp(-dot(q*vec2(3.,28.),q*vec2(3.,28.)))*.25+exp(-dot(q*vec2(28.,3.),q*vec2(28.,3.)))*.25;a=clamp(a,0.,1.);gl_FragColor=vec4(vec3(1.)*a,a);}`},{attributes:['position','uv'],uniforms:['worldViewProjection'],needAlphaBlending:true});starMaterial.alphaMode=B.Engine.ALPHA_PREMULTIPLIED_PORTERDUFF;
      for(const [x,y,size] of [[-3.65,1.45,.23],[-2.95,.84,.13],[-2.72,-.32,.11],[.22,1.96,.1],[2.76,.80,.09]]){const star=B.MeshBuilder.CreatePlane('ambient-star',{width:size,height:size},scene);star.position.set(x,y,-2.2);star.material=starMaterial;}
      const three=await import('/vendor/three/three.core.js');
      const positions=[[-2.00,1.10,.31],[2.30,-.12,.34],[-1.95,-.65,.25],[1.15,1.50,.20],[1.24,-1.45,.19],[-1.35,-1.48,.17]];
      positions.forEach(([x,y,size],i)=>{
        const geometry=new three.OctahedronGeometry(size,1);geometry.computeVertexNormals();const mesh=new B.Mesh('crystal-'+i,scene),data=new B.VertexData();
        data.positions=Array.from(geometry.attributes.position.array);data.normals=Array.from(geometry.attributes.normal.array);
        data.indices=Array.from({length:data.positions.length/3},(_,j)=>j);data.applyToMesh(mesh);geometry.dispose();
        mesh.position.set(x,y,.15);mesh.scaling.y=2.4;mesh.rotation.z=[-.28,.12,-.18,-.20,.14,-.20][i];mesh.material=material('crystal-glass-'+i,1);
        mesh.enableEdgesRendering(.98);mesh.edgesWidth=1.25;mesh.edgesColor=new B.Color4(1,1,1,.72);
        crystals.push({mesh,y,phase:i});materials.push(mesh.material);
      });
    }
    if(hero||welcome){
      // The compact welcome retains the glass lens and a single inclined orbit.
      const orbit=Array.from({length:181},(_,i)=>{const t=i/180*Math.PI*2,x=Math.cos(t)*(welcome?1.55:2.55);return new B.Vector3(x-(welcome?0:.25),Math.sin(t)*.38+x*.34,Math.sin(t)*.85);});
      ribbon=B.MeshBuilder.CreateTube('liquid-ribbon',{path:orbit,radius:.015,tessellation:12},scene);
      const orbitalGlass=new B.StandardMaterial('orbital-glass',scene);orbitalGlass.disableLighting=true;orbitalGlass.emissiveColor=new B.Color3(1,.99,1);orbitalGlass.alpha=.55;orbitalGlass.alphaMode=B.Engine.ALPHA_PREMULTIPLIED_PORTERDUFF;orbitalGlass.backFaceCulling=false;ribbon.material=orbitalGlass;
    }
    // An actual offscreen view of the scene behind the lens, never a screen capture.
    const backdrop=B.MeshBuilder.CreatePlane('light-field',{width:18,height:10},scene);backdrop.position.z=-2.8;
    backdrop.material=new B.ShaderMaterial('light-field-material',scene,{vertexSource:`precision highp float;attribute vec3 position;attribute vec2 uv;uniform mat4 worldViewProjection;varying vec2 v;void main(){v=uv;gl_Position=worldViewProjection*vec4(position,1.);}`,fragmentSource:`precision highp float;varying vec2 v;void main(){float a=exp(-pow((v.y-.52-sin(v.x*8.)*.13)*45.,2.));float b=exp(-pow((v.y-.40+sin(v.x*7.)*.08)*60.,2.));gl_FragColor=vec4(mix(vec3(.88,.83,1.),vec3(.75,.92,1.),v.x),.055+a*.20+b*.13);}`},{attributes:['position','uv'],uniforms:['worldViewProjection'],needAlphaBlending:true});
    const refraction=new B.RenderTargetTexture('lens-background',{width:Math.max(1,engine.getRenderWidth()),height:Math.max(1,engine.getRenderHeight())},scene,false);
    refraction.clearColor=new B.Color4(0,0,0,0);refraction.activeCamera=camera;refraction.renderList=scene.meshes.filter(m=>m!==pearl&&m!==innerShell&&!['liquid-ribbon','orbit'].includes(m.name));refraction.ignoreCameraViewport=true;
    if(!hero)refraction.refreshRate=0;scene.customRenderTargets.push(refraction);pearlMaterial.setTexture('refractionMap',refraction);innerShell?.material.setTexture('refractionMap',refraction);
    let enabled=document.documentElement.dataset.motion!=='off',visible=false,disposed=false,ready=false,elapsed=0,last=performance.now();
    const reduced=matchMedia('(prefers-reduced-motion: reduce)');
    function render(){
      if(disposed||!ready||document.hidden||!visible)return;
      // Stop even if the host delivers its media change event after this frame.
      if(!enabled||reduced.matches)engine.stopRenderLoop(render);
      if(!canvas.isConnected){engine.stopRenderLoop(render);return;}
      const now=performance.now();if(enabled&&!reduced.matches)elapsed+=Math.min(now-last,45)/1000;last=now;
      materials.forEach(m=>m.setFloat('time',elapsed));
      pearl.position.y=Math.sin(elapsed*.36)*.035;
      if(innerShell)innerShell.position.y=pearl.position.y;
      for(const {mesh,y,phase} of crystals){mesh.position.y=y+Math.sin(elapsed*.22+phase)*.12;mesh.rotation.y=elapsed*.055+.35+phase*.6;}
      if(ribbon)ribbon.rotation.z=Math.sin(elapsed*.12)*.07;
      scene.render();
    }
    function schedule(){engine.stopRenderLoop(render);last=performance.now();const painted=visible&&canvas.isConnected&&canvas.getClientRects().length&&!canvas.closest('[hidden],[inert]')&&getComputedStyle(canvas).visibility!=='hidden';if(ready&&painted&&!document.hidden){render();if(enabled&&!reduced.matches)engine.runRenderLoop(render);}}
    let dimensions='';
    function resize(){const rect=canvas.getBoundingClientRect();if(rect.width<1||rect.height<1)return;const key=rect.width+':'+rect.height+':'+devicePixelRatio;if(key===dimensions)return;dimensions=key;engine.setHardwareScalingLevel(1/Math.min(devicePixelRatio||1,1.5));engine.resize();const width=engine.getRenderWidth(),height=engine.getRenderHeight();pearlMaterial.setVector2('resolution',new B.Vector2(width,height));innerShell?.material.setVector2('resolution',new B.Vector2(width,height));const textureSize=refraction.getSize();if(textureSize.width!==width||textureSize.height!==height)refraction.resize({width,height});const half=hero?2.20:1.70;camera.orthoTop=half;camera.orthoBottom=-half;camera.orthoLeft=-half*rect.width/rect.height;camera.orthoRight=half*rect.width/rect.height;render();}
    const appearance=new MutationObserver(records=>{if(records.some(record=>record.target.contains(canvas)))schedule();});appearance.observe(document.documentElement,{attributes:true,attributeFilter:['data-screen','data-motion','data-editor-covered']});appearance.observe(document.body,{subtree:true,attributes:true,attributeFilter:['hidden','inert']});
    const observer=new ResizeObserver(resize);observer.observe(canvas);
    const intersection=new IntersectionObserver(entries=>{visible=!!entries[0]?.isIntersecting;schedule();});intersection.observe(canvas);
    document.addEventListener('visibilitychange',schedule);reduced.addEventListener('change',schedule);
    const lost=()=>{canvas.parentElement.classList.remove('gpu-ready');};canvas.addEventListener('webglcontextlost',lost);
    const restored=engine.onContextRestoredObservable.add(()=>{canvas.parentElement.classList.add('gpu-ready');resize();schedule();});
    cleanup=()=>{disposed=true;appearance.disconnect();observer.disconnect();intersection.disconnect();document.removeEventListener('visibilitychange',schedule);reduced.removeEventListener('change',schedule);canvas.removeEventListener('webglcontextlost',lost);engine.onContextRestoredObservable.remove(restored);engine.stopRenderLoop(render);};
    let readyTimer;try{await Promise.race([scene.whenReadyAsync(),new Promise((_,reject)=>{readyTimer=setTimeout(()=>reject(new Error('El motor gráfico no respondió a tiempo')),12000);})]);}finally{clearTimeout(readyTimer);}if(!canvas.isConnected){cleanup();scene.dispose();engine.dispose();return fallback;}ready=true;resize();visible=canvas.getClientRects().length>0;render();
    canvas.parentElement.classList.add('gpu-ready');schedule();onStatus(`${geometry?'Blender + ':''}Babylon.js · ${canvas.dataset.engine} · Zénit Glass`);
    return {kind:'babylon',renderer:canvas.dataset.engine,setTheme(){render();},setMotion(value){enabled=value;schedule();},dispose(){const gl=engine._gl;cleanup();scene.dispose();engine.dispose();gl?.getExtension('WEBGL_lose_context')?.loseContext();}};
  }catch(error){cleanup();scene?.dispose();engine?.dispose();canvas.dataset.graphicsError=error.message;onStatus('Cristal CSS · '+error.message);return fallback;}
}

