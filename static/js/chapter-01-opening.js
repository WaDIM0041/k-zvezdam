(function(){
  'use strict';
  var intro=document.querySelector('#chapterOpening[data-chapter-id="2"]');
  var pause=document.getElementById('chapterOnePause');
  var skip=document.getElementById('chapterOneSkip');
  var text=document.getElementById('chapterText');
  if(!intro||!pause||!skip||!text)return;
  var reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
  if(reduced.matches){pause.disabled=true;pause.textContent='Без анимации';}
  pause.addEventListener('click',function(){
    var paused=intro.classList.toggle('intro-paused');
    pause.setAttribute('aria-pressed',String(paused));
    pause.textContent=paused?'Продолжить':'Пауза';
  });
  skip.addEventListener('click',function(){text.scrollIntoView({behavior:reduced.matches?'auto':'smooth'});});
})();
