const opening = document.getElementById('chapterOpening');
const pause = opening.querySelector('.radio-room-pause');
const motion = matchMedia('(prefers-reduced-motion: no-preference)');

function syncMotion() {
  pause.hidden = !motion.matches;
  opening.classList.toggle('radio-room-active', motion.matches);
}

pause.addEventListener('click', () => {
  const paused = opening.classList.toggle('radio-room-paused');
  pause.setAttribute('aria-pressed', String(paused));
  pause.textContent = paused ? 'Продолжить' : 'Пауза';
});
motion.addEventListener('change', syncMotion);
syncMotion();
