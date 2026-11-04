/* Real sphere/atmosphere/stars + a masked, fixed-view station. */
(function(){
  'use strict';
  var clamp=function(v){return Math.max(0,Math.min(1,v));};
  function smooth(a,b,v){v=clamp((v-a)/(b-a));return v*v*(3-2*v);}
  window.KZChapterScenes=window.KZChapterScenes||{};
  window.KZChapterScenes.prologue=function(canvas,host,config,changed){
    var T=window.THREE,renderer,scene,camera,station,planet,atmosphere,stars,resizeObserver;
    var geometries=[],materials=[],textures=[],raf=0,timer=0,last=0,lastDraw=0,time=0,frames=0;
    var disposed=false,ready=false,paused=false,held=false,mode='loading',duration=config.duration||14;
    var pointer={x:0,y:0},camX=0,camY=0,small=false;
    function update(){changed({time:time,mode:mode,paused:paused,ready:ready,held:held});}
    function stop(){if(raf)cancelAnimationFrame(raf);raf=0;last=0;}
    function release(){
      stop();clearTimeout(timer);ready=false;if(resizeObserver)resizeObserver.disconnect();
      geometries.forEach(function(g){g.dispose();});materials.forEach(function(m){m.dispose();});textures.forEach(function(t){t.dispose();});geometries=[];materials=[];textures=[];
      if(renderer){var gl=renderer.getContext();renderer.dispose();if(!gl.isContextLost())renderer.forceContextLoss();}
      renderer=scene=camera=station=planet=atmosphere=stars=null;
    }
    function fallback(){if(disposed)return;mode='static';time=duration;held=true;release();update();}
    function geo(g){geometries.push(g);return g;}function mat(m){materials.push(m);return m;}
    function draw(){
      if(!ready||disposed)return;
      var k=smooth(0,duration,time),r=smooth(1.8,7,time),env=smooth(0,2,time);
      station.material.uniforms.reveal.value=r;station.position.z=-1.7*(1-r);
      stars.material.opacity=env*.85;planet.material.opacity=env;atmosphere.material.uniforms.reveal.value=env;
      var amplitude=small?.11:.48;
      camX+=((-.26+.52*k+pointer.x*amplitude)-camX)*.08;
      camY+=((pointer.y*(small?.05:.16))-camY)*.08;
      camera.position.set(camX,camY,16-.5*k);camera.lookAt(0,0,0);renderer.render(scene,camera);frames++;
    }
    function resize(){
      if(!renderer||!station||disposed)return;
      var w=host.clientWidth,h=host.clientHeight;if(!w||!h)return;
      var aspect=w/h;small=aspect<1;renderer.setPixelRatio(Math.min(devicePixelRatio||1,small?1.25:1.5));renderer.setSize(w,h,false);
      camera.aspect=aspect;camera.updateProjectionMatrix();
      var height=2*15.5*Math.tan(48*Math.PI/360),width=height*aspect;
      var planeWidth=small?width*1.13:Math.min(width*1.08,height*1.95);
      station.scale.set(planeWidth,planeWidth/(2752/1536),1);station.position.y=small?height*.19:height*.055;
      planet.position.set(small?-15:0,small?-104:-100,-140);atmosphere.position.copy(planet.position);draw();
    }
    function tick(now){
      raf=0;if(disposed||paused||document.hidden||!ready||held){last=0;return;}
      if(last)time=Math.min(duration,time+Math.min((now-last)/1000,.1));last=now;
      if(now-lastDraw>=1000/30||time>=duration){draw();update();lastDraw=now;}
      if(time>=duration){held=true;mode='held';update();}else raf=requestAnimationFrame(tick);
    }
    function start(){if(!raf&&!disposed&&ready&&!paused&&!held&&!document.hidden)raf=requestAnimationFrame(tick);}
    function visibility(){document.hidden?stop():start();}
    function lost(e){e.preventDefault();if(!disposed&&mode!=='static')fallback();}
    function settle(){raf=0;if(!ready||disposed||paused||document.hidden||!held)return;draw();var target=.26+pointer.x*(small?.11:.48);if(Math.abs(target-camX)>.002||Math.abs(pointer.y*(small?.05:.16)-camY)>.002)raf=requestAnimationFrame(settle);}
    function nudge(){if(held&&!paused&&!raf&&ready)raf=requestAnimationFrame(settle);}
    function move(e){var b=host.getBoundingClientRect();pointer.x=clamp((e.clientX-b.left)/b.width)*2-1;pointer.y=1-clamp((e.clientY-b.top)/b.height)*2;nudge();}
    function leave(){pointer.x=pointer.y=0;nudge();}
    canvas.addEventListener('webglcontextlost',lost);document.addEventListener('visibilitychange',visibility);host.addEventListener('pointermove',move,{passive:true});host.addEventListener('pointerleave',leave);
    if(!T||config.reduced||!config.cutout||!config.gas)fallback();
    else try{
      renderer=new T.WebGLRenderer({canvas:canvas,antialias:true,alpha:false,powerPreference:'low-power'});renderer.setClearColor(0x03070c,1);renderer.outputEncoding=T.sRGBEncoding;
      scene=new T.Scene();camera=new T.PerspectiveCamera(48,1,.1,600);camera.position.z=16;
      var seed=127;function random(){seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;}
      var positions=new Float32Array((host.clientWidth<650?700:1500)*3);
      for(var i=0;i<positions.length;i+=3){positions[i]=(random()-.5)*460;positions[i+1]=(random()-.5)*280;positions[i+2]=-140-random()*210;}
      var sg=geo(new T.BufferGeometry());sg.setAttribute('position',new T.BufferAttribute(positions,3));
      stars=new T.Points(sg,mat(new T.PointsMaterial({color:0xd6e4f3,size:1.1,sizeAttenuation:false,transparent:true,opacity:0,depthWrite:false})));scene.add(stars);
      planet=new T.Mesh(geo(new T.SphereGeometry(95,96,64)),mat(new T.MeshStandardMaterial({roughness:1,metalness:0,transparent:true,opacity:0})));planet.rotation.z=-.28;planet.rotation.y=.4;scene.add(planet);
      atmosphere=new T.Mesh(geo(new T.SphereGeometry(95.45,64,40)),mat(new T.ShaderMaterial({uniforms:{reveal:{value:0}},vertexShader:'varying vec3 n;varying vec3 view;void main(){vec4 p=modelViewMatrix*vec4(position,1.);n=normalize(normalMatrix*normal);view=normalize(-p.xyz);gl_Position=projectionMatrix*p;}',fragmentShader:'uniform float reveal;varying vec3 n;varying vec3 view;void main(){float f=pow(1.-abs(dot(normalize(n),normalize(view))),4.);gl_FragColor=vec4(1.,.55,.22,f*.32*reveal);}',transparent:true,side:T.BackSide,depthWrite:false})));scene.add(atmosphere);
      scene.add(new T.AmbientLight(0xb8c6d5,.45));var sun=new T.DirectionalLight(0xffdfb7,2.1);sun.position.set(-40,60,85);scene.add(sun);
      var loader=new T.TextureLoader();
      function load(url){return new Promise(function(resolve,reject){loader.load(url,function(t){if(disposed||mode==='static'){t.dispose();resolve(null);return;}textures.push(t);resolve(t);},undefined,reject);});}
      timer=setTimeout(fallback,10000);
      Promise.all([load(config.image),load(config.cutout),load(config.gas)]).then(function(loaded){
        if(disposed||mode==='static'||loaded.some(function(t){return!t;}))return;clearTimeout(timer);
        loaded[2].encoding=T.sRGBEncoding;loaded[2].anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());planet.material.map=loaded[2];planet.material.needsUpdate=true;
        // AI supplies only the alpha mask. RGB comes from the original reference.
        // The dark central recess is protected, not made into a through-hole.
        station=new T.Mesh(geo(new T.PlaneGeometry(1,1)),mat(new T.ShaderMaterial({uniforms:{original:{value:loaded[0]},mask:{value:loaded[1]},reveal:{value:0}},vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:'uniform sampler2D original;uniform sampler2D mask;uniform float reveal;varying vec2 vUv;void main(){float a=smoothstep(.06,.94,texture2D(mask,vUv).a);float recess=step(.399,vUv.x)*(1.-step(.452,vUv.x))*step(.465,vUv.y)*(1.-step(.557,vUv.y));a=max(a,recess);if(a<.01)discard;gl_FragColor=vec4(texture2D(original,vUv).rgb,a*reveal);}',transparent:true,depthWrite:true,side:T.FrontSide})));scene.add(station);ready=true;mode=held?'held':'layered';resize();update();start();resizeObserver=new ResizeObserver(resize);resizeObserver.observe(host);
      }).catch(fallback);
    }catch(e){fallback();}
    return{pause:function(value){paused=value;paused?stop():start();update();},skip:function(){held=true;time=duration;mode=ready?'held':mode;stop();draw();update();},static:fallback,dispose:function(){if(disposed)return;disposed=true;canvas.removeEventListener('webglcontextlost',lost);document.removeEventListener('visibilitychange',visibility);host.removeEventListener('pointermove',move);host.removeEventListener('pointerleave',leave);release();},diagnostics:function(){return{mode:mode,time:time,paused:paused,frames:frames,rafActive:!!raf,ready:ready,disposed:disposed,layers:ready?['stars-3D','planet-sphere-3D','atmosphere-3D','station-alpha-2.5D']:[],memory:renderer?renderer.info.memory:null};}};
  };
})();
