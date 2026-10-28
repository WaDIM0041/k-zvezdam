/* Кинематографичный космический фон для главной.
   Three.js: звёздное поле + туманности + периодический пролёт корабля + параллакс.
   Бережно к мобильным: меньше частиц, уважение prefers-reduced-motion. */
(function () {
  document.querySelectorAll('.space-scene').forEach(function(canvas){
  var host=canvas.parentElement;
  function width(){return host.clientWidth;}
  function height(){return host.clientHeight;}
  var reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var small = innerWidth < 760;

  // Fallback, если Three.js не загрузился или отключены анимации
  if (typeof THREE === 'undefined' || reduced) {
    canvas.style.display = 'none';
    host.classList.add('hero-fallback');
    return;
  }

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(70, width() / height(), 0.1, 1000);
  camera.position.z = 60;

  var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: !small, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, small ? 1.5 : 2));
  renderer.setSize(width(), height());

  // --- Звёзды ---
  var starTexture = nebulaTexture('rgba(255,255,255,1)');
  function makeStars(count, spread, size, color) {
    var g = new THREE.BufferGeometry();
    var pos = new Float32Array(count * 3);
    for (var i = 0; i < count * 3; i++) pos[i] = (Math.random() - 0.5) * spread;
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    var m = new THREE.PointsMaterial({
      map: starTexture, alphaTest: 0.015,
      color: color, size: size, transparent: true, opacity: 0.9,
      blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true
    });
    return new THREE.Points(g, m);
  }
  var starsFar = makeStars(small ? 900 : 2400, 400, 1.1, 0xbcd6ff);
  var starsNear = makeStars(small ? 250 : 600, 320, 1.9, 0xc8e4ff);
  scene.add(starsFar); scene.add(starsNear);

  // --- Туманности (мягкие спрайты) ---
  function nebulaTexture(c1) {
    var s = 256, cv = document.createElement('canvas'); cv.width = cv.height = s;
    var ctx = cv.getContext('2d');
    var gr = ctx.createRadialGradient(s/2, s/2, 0, s/2, s/2, s/2);
    gr.addColorStop(0, c1); gr.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = gr; ctx.fillRect(0, 0, s, s);
    return new THREE.CanvasTexture(cv);
  }
  var nebs = [];
  [['rgba(90,150,255,0.55)', -40, 10, -60, 120],
   ['rgba(150,110,255,0.5)', 55, -20, -80, 150],
   ['rgba(60,200,230,0.4)', 10, 40, -120, 180]].forEach(function (n) {
    var sp = new THREE.Sprite(new THREE.SpriteMaterial({
      map: nebulaTexture(n[0]), blending: THREE.AdditiveBlending,
      transparent: true, depthWrite: false, opacity: 0.6
    }));
    sp.position.set(n[1], n[2], n[3]); sp.scale.set(n[4], n[4], 1);
    scene.add(sp); nebs.push(sp);
  });

  // Далёкие спиральные галактики: прозрачные текстуры без квадратных краёв.
  function galaxyTexture(){
    var cv=document.createElement('canvas');cv.width=cv.height=256;
    var ctx=cv.getContext('2d');
    ctx.translate(128,128);ctx.scale(1,.58);
    ctx.globalCompositeOperation='lighter';
    for(var arm=0;arm<3;arm++){
      for(var j=0;j<420;j++){
        var radius=8+j*.24,angle=arm*Math.PI*2/3+j*.022;
        var x=Math.cos(angle)*radius,y=Math.sin(angle)*radius;
        var glow=ctx.createRadialGradient(x,y,0,x,y,9);
        glow.addColorStop(0,'rgba(165,188,255,.07)');
        glow.addColorStop(1,'rgba(125,140,255,0)');
        ctx.fillStyle=glow;ctx.fillRect(x-9,y-9,18,18);
      }
    }
    var core=ctx.createRadialGradient(0,0,0,0,0,30);
    core.addColorStop(0,'rgba(255,243,218,.95)');
    core.addColorStop(.2,'rgba(225,220,255,.65)');
    core.addColorStop(1,'rgba(160,170,255,0)');
    ctx.fillStyle=core;ctx.fillRect(-30,-30,60,60);
    return new THREE.CanvasTexture(cv);
  }
  var galaxyMap=galaxyTexture();
  [[-75,28,-140,37,.35],[65,-25,-180,48,-.5],[20,55,-230,32,.7]].forEach(function(g,index){
    if(canvas.id==='space' && index===1)return;
    var galaxy=new THREE.Sprite(new THREE.SpriteMaterial({map:galaxyMap,transparent:true,opacity:.65,depthWrite:false,blending:THREE.AdditiveBlending,rotation:g[4]}));
    galaxy.position.set(g[0],g[1],g[2]);galaxy.scale.set(g[3],g[3],1);scene.add(galaxy);
  });
  // Несколько перекрывающихся облаков дают туманностям неоднородную глубину.
  for(var cloud=0;cloud<7;cloud++){
    var mist=new THREE.Sprite(new THREE.SpriteMaterial({map:nebulaTexture(cloud%2?'rgba(140,85,185,.25)':'rgba(65,140,190,.25)'),transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,opacity:.4}));
    mist.position.set(-100+cloud*32,Math.sin(cloud*1.7)*35,-170-cloud*8);
    mist.scale.set(100+cloud*9,60+cloud*8,1);scene.add(mist);
  }

  // --- Корабль ---
  var ship = new THREE.Group();
  var hull = new THREE.Mesh(
    new THREE.ConeGeometry(0.7, 4, 12),
    new THREE.MeshBasicMaterial({ color: 0x0a1424 })
  );
  hull.rotation.z = -Math.PI / 2;
  var glow = new THREE.Sprite(new THREE.SpriteMaterial({
    map: nebulaTexture('rgba(120,200,255,0.95)'), blending: THREE.AdditiveBlending,
    transparent: true, depthWrite: false
  }));
  glow.scale.set(7, 7, 1); glow.position.x = -2.6;
  var trail = new THREE.Sprite(new THREE.SpriteMaterial({
    map: nebulaTexture('rgba(120,200,255,0.6)'), blending: THREE.AdditiveBlending,
    transparent: true, depthWrite: false
  }));
  trail.scale.set(22, 3.4, 1); trail.position.x = -9;
  ship.add(trail); ship.add(glow); ship.add(hull);
  ship.position.set(-120, -18, -10); ship.visible = false;
  scene.add(ship);
  var shipT = -1, shipDelay = 3;

  // --- Параллакс мыши ---
  var mx = 0, my = 0, tmx = 0, tmy = 0;
  addEventListener('mousemove', function (e) {
    tmx = (e.clientX / innerWidth - 0.5); tmy = (e.clientY / innerHeight - 0.5);
  });

  var visible=true;
  var observer=new IntersectionObserver(function(entries){visible=entries[0].isIntersecting;});
  observer.observe(host);
  var clock = new THREE.Clock();
  function tick() {
    var dt = Math.min(clock.getDelta(),.05), t = clock.elapsedTime;
    if(!visible || document.hidden){requestAnimationFrame(tick);return;}
    starsFar.rotation.y += dt * 0.006; starsFar.rotation.x += dt * 0.002;
    starsNear.rotation.y += dt * 0.012;
    nebs.forEach(function (n, i) { n.material.opacity = 0.4 + 0.18 * Math.sin(t * 0.4 + i); });

    mx += (tmx - mx) * 0.04; my += (tmy - my) * 0.04;
    camera.position.x = mx * 14; camera.position.y = -my * 10;
    camera.lookAt(0, 0, 0);

    // пролёт корабля
    shipDelay -= dt;
    if (shipDelay <= 0 && shipT < 0) { shipT = 0; ship.visible = true; }
    if (shipT >= 0) {
      shipT += dt;
      var p = shipT / 7;
      ship.position.x = -120 + p * 240;
      ship.position.y = -18;
      if (p >= 1) { shipT = -1; ship.visible = false; shipDelay = 9 + Math.random() * 8; }
    }
    renderer.render(scene, camera);
    requestAnimationFrame(tick);
  }
  tick();

  addEventListener('resize', function () {
    camera.aspect = width() / height(); camera.updateProjectionMatrix();
    renderer.setSize(width(), height());
  });
  });
})();
