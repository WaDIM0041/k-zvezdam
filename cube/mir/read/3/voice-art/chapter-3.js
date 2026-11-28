const opening = document.getElementById('chapterOpening');
const pause = opening.querySelector('.static-voice-pause');
const motion = matchMedia('(prefers-reduced-motion: no-preference)');

function syncMotion() {
  pause.hidden = !motion.matches;
  opening.classList.toggle('static-voice-active', motion.matches);
}

pause.addEventListener('click', () => {
  const paused = opening.classList.toggle('static-voice-paused');
  pause.setAttribute('aria-pressed', String(paused));
});
motion.addEventListener('change', syncMotion);
syncMotion();
