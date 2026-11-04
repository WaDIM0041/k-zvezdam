(function(){
  'use strict';
  var intro=document.querySelector('#chapterOpening[data-chapter-id="2"]');
  var pause=document.getElementById('chapterOnePause');
  var skip=document.getElementById('chapterOneSkip');
  var text=document.getElementById('chapterText');
  if(!intro||!pause||!skip||!text)return;
  var rain=intro.querySelector('.chapter-one-rain');
  if(rain){
    var seed=31;
    function random(){seed=(seed*16807)%2147483647;return (seed-1)/2147483646;}
    for(var i=0;i<42;i++){
      var drop=document.createElement('span');
      drop.className='chapter-one-rain__drop';
      drop.style.setProperty('--left',(random()*100).toFixed(1)+'%');
      drop.style.setProperty('--top',(random()*75).toFixed(1)+'%');
      drop.style.setProperty('--width',(2+random()*4).toFixed(1)+'px');
      drop.style.setProperty('--height',(5+random()*8).toFixed(1)+'px');
      drop.style.setProperty('--travel',(35+random()*130).toFixed(0)+'px');
      drop.style.setProperty('--trail',(10+random()*35).toFixed(0)+'px');
      drop.style.setProperty('--duration',(8+random()*13).toFixed(1)+'s');
      drop.style.setProperty('--delay',(-random()*20).toFixed(1)+'s');
      rain.appendChild(drop);
    }
  }
  var reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
  if(reduced.matches){pause.disabled=true;pause.textContent='Без анимации';}
  pause.addEventListener('click',function(){
    var paused=intro.classList.toggle('intro-paused');
    pause.setAttribute('aria-pressed',String(paused));
    pause.textContent=paused?'Продолжить':'Пауза';
  });
  skip.addEventListener('click',function(){text.scrollIntoView({behavior:reduced.matches?'auto':'smooth'});});
})();
