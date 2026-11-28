const bunkerIntro = document.querySelector('[data-scene="bunker-night"]');
const motionButton = bunkerIntro.querySelector('#bunker-motion');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
function updateControl() {
  motionButton.hidden = reducedMotion.matches;
}
motionButton.addEventListener('click', () => {
  const paused = bunkerIntro.classList.toggle('paused');
  motionButton.textContent = paused ? 'Продолжить' : 'Пауза';
  motionButton.setAttribute('aria-pressed', String(paused));
});
updateControl();
reducedMotion.addEventListener('change', updateControl);