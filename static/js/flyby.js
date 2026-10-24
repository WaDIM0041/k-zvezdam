/* Один пролёт над всей страницей и короткая вспышка гиперперехода. */
(function(){
  var reduced=matchMedia('(prefers-reduced-motion: reduce)');
  var title=document.getElementById('heroContent');
  var titleTimer;
  function scheduleTitleFlash(delay){
    titleTimer=setTimeout(function(){
      if(!title)return;
      var hero=title.closest('.hero');
      var rect=hero.getBoundingClientRect();
      if(reduced.matches||document.hidden||rect.bottom<=0){scheduleTitleFlash(4000);return;}
      title.classList.remove('flash-active');
      title.style.setProperty('--flash-x',(15+Math.random()*100)+'%');
      title.style.setProperty('--flash-y',(5+Math.random()*85)+'%');
      void title.offsetWidth;
      title.classList.add('flash-active');
      scheduleTitleFlash(9000+Math.random()*10000);
    },delay);
  }
  if(title)scheduleTitleFlash(3500);
  var contents=document.querySelector('.list-s');
  if(!contents)return;
  var canvas=document.createElement('canvas');
  canvas.className='site-flyby';
  canvas.setAttribute('aria-hidden','true');
  contents.appendChild(canvas);
  var ctx=canvas.getContext('2d');
  if(!ctx)return;
  var width,height,start=0,next=performance.now()+3500;
  function resize(){
    width=contents.clientWidth;height=contents.clientHeight;
    var ratio=Math.min(devicePixelRatio||1,2);
    canvas.width=width*ratio;canvas.height=height*ratio;
    ctx.setTransform(ratio,0,0,ratio,0,0);
  }
  resize();addEventListener('resize',resize);
  new ResizeObserver(resize).observe(contents);
  var visible=false,triggered=false;
  var contentsObserver=new IntersectionObserver(function(entries){
    visible=entries[0].isIntersecting;
    if(visible&&!triggered){triggered=true;next=performance.now()+1500;contentsObserver.disconnect();}
  },{threshold:.15});
  contentsObserver.observe(contents);
  function glow(x,y,r,alpha){
    var g=ctx.createRadialGradient(x,y,0,x,y,r);
    g.addColorStop(0,'rgba(235,250,255,'+alpha+')');
    g.addColorStop(.18,'rgba(130,215,255,'+(alpha*.8)+')');
    g.addColorStop(.55,'rgba(87,130,255,'+(alpha*.25)+')');
    g.addColorStop(1,'rgba(87,130,255,0)');
    ctx.fillStyle=g;ctx.fillRect(x-r,y-r,r*2,r*2);
  }
  function tick(now){
    ctx.clearRect(0,0,width,height);
    if(reduced.matches)return;
    if(document.hidden||!triggered){requestAnimationFrame(tick);return;}
    if(!start&&now>=next)start=now;
    if(start){
      var elapsed=(now-start)/1000;
      var endX=width*.88,endY=height*.28;
      if(elapsed<5){
        var p=elapsed/5,x=-100+(endX+100)*p,y=height*.8+(endY-height*.8)*p;
        ctx.save();ctx.translate(x,y);ctx.rotate(Math.atan2(endY-height*.8,endX+100));
        ctx.globalCompositeOperation='lighter';
        var trail=ctx.createLinearGradient(-125,0,-12,0);
        trail.addColorStop(0,'rgba(105,175,255,0)');trail.addColorStop(1,'rgba(140,225,255,.8)');
        ctx.fillStyle=trail;ctx.beginPath();ctx.moveTo(-125,0);ctx.lineTo(-15,-4);ctx.lineTo(-15,4);ctx.fill();
        glow(-18,0,19,.65);ctx.globalCompositeOperation='source-over';
        ctx.fillStyle='#bad2e6';ctx.beginPath();ctx.moveTo(22,0);ctx.lineTo(-20,-6);ctx.lineTo(-12,0);ctx.lineTo(-20,6);ctx.closePath();ctx.fill();
        ctx.fillStyle='#5c86aa';ctx.beginPath();ctx.moveTo(8,0);ctx.lineTo(-19,-15);ctx.lineTo(-13,0);ctx.lineTo(-19,15);ctx.closePath();ctx.fill();
        ctx.restore();
      }else if(elapsed<6.2){
        var t=(elapsed-5)/1.2,alpha=Math.pow(1-t,2);
        ctx.save();ctx.globalCompositeOperation='lighter';
        glow(endX,endY,30+100*Math.sqrt(t),alpha*.9);
        ctx.strokeStyle='rgba(150,220,255,'+(alpha*.65)+')';ctx.lineWidth=1.5;
        ctx.beginPath();ctx.ellipse(endX,endY,10+t*90,5+t*45,0,0,Math.PI*2);ctx.stroke();
        ctx.fillStyle='rgba(215,245,255,'+alpha+')';
        ctx.fillRect(endX-65*(1-t),endY-.7,130*(1-t),1.4);
        ctx.restore();
      }else{return;}
    }
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
})();
