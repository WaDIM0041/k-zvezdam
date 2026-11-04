/* Chapter opening stays in the reading flow; the story begins directly below it. */
(function () {
  'use strict';

  var legacy = location.hash.match(/^#\/intro\/(\d+)$/);
  if (legacy) {
    var brand = document.querySelector('#nav .brand');
    var root = brand ? new URL(brand.href, location.href) : new URL('/', location.href);
    var target = new URL('read/' + legacy[1] + '/', root);
    target.hash = 'chapterOpening';
    location.replace(target.href);
    return;
  }

  var intro = document.getElementById('chapterOpening');
  if (!intro) return;

  if (intro.dataset.scene === 'poster') {
    var firstArt = document.querySelector('#readBody .scene-media img, #readBody .c-img img, #readBody video[poster]');
    if (firstArt) {
      var artUrl = firstArt.tagName === 'VIDEO' ? firstArt.poster : (firstArt.currentSrc || firstArt.src);
      if (artUrl) intro.querySelector('.chapter-intro__poster').style.backgroundImage =
        'linear-gradient(0deg,#04080cf5,transparent 68%),linear-gradient(90deg,#04080cc0,transparent 65%),linear-gradient(180deg,#03070c90,transparent 25%),url(' + JSON.stringify(artUrl) + ')';
    }
    return;
  }

  if (intro.dataset.scene !== 'prologue' || !window.KZChapterScenes || !window.KZChapterScenes.prologue) return;

  var createScene = window.KZChapterScenes.prologue;
  var motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var stage = intro.querySelector('.chapter-intro__stage');
  var canvas = intro.querySelector('.chapter-intro__canvas');
  var pause = intro.querySelector('[data-intro-action="pause"]');
  var skip = intro.querySelector('[data-intro-action="skip"]');
  var status = intro.querySelector('.chapter-intro__status');
  var time = intro.querySelector('.chapter-intro__time');
  var scene = null;
  var duration = Number(intro.dataset.duration) || 14;
  var finished = false;

  function clamp(value) { return Math.max(0, Math.min(1, value)); }
  function smooth(a, b, value) { value = clamp((value - a) / (b - a)); return value * value * (3 - 2 * value); }
  function changed(state) {
    intro.classList.toggle('is-webgl', state.ready);
    intro.classList.toggle('is-loading', state.mode === 'loading');
    intro.style.setProperty('--intro-title', smooth(1.2, 2.4, state.time));
    intro.style.setProperty('--intro-line1', smooth(2.2, 3.4, state.time));
    intro.style.setProperty('--intro-line2', smooth(3.2, 4.4, state.time));
    intro.style.setProperty('--intro-progress', clamp(state.time / duration));
    time.textContent = '00 : ' + String(Math.floor(state.time)).padStart(2, '0');
    pause.disabled = state.held || finished;
    skip.disabled = state.held || finished;
    pause.textContent = state.paused ? 'Продолжить' : 'Пауза';
    pause.setAttribute('aria-pressed', String(state.paused));
    if (state.mode === 'static') status.textContent = 'Неподвижная заставка. Текст главы — ниже.';
    else if (state.held) status.textContent = 'Заставка завершена. Текст главы — ниже.';
    else status.textContent = '';
    if (state.held && !finished) finishScene();
  }
  function finishScene() {
    if (finished) return;
    finished = true;
    if (scene) scene.dispose();
    scene = null;
    intro.classList.remove('is-webgl', 'is-loading');
    pause.disabled = true;
    skip.disabled = true;
  }
  function start() {
    if (scene) scene.dispose();
    canvas.replaceWith(canvas.cloneNode(false));
    canvas = intro.querySelector('.chapter-intro__canvas');
    changed({time: motion.matches ? duration : 0, mode: motion.matches ? 'static' : 'loading', paused: false, ready: false, held: motion.matches});
    var still = intro.querySelector('.chapter-intro__still');
    var cutout = intro.querySelector('.chapter-intro__mask');
    var gas = intro.querySelector('.chapter-intro__gas');
    scene = createScene(canvas, stage, {image: still.currentSrc || still.src, cutout: cutout.currentSrc || cutout.src, gas: gas.currentSrc || gas.src, duration: duration, reduced: motion.matches}, changed);
  }

  if (!canvas || !pause || !skip || !status || !time) return;
  pause.addEventListener('click', function () { if (scene) scene.pause(pause.getAttribute('aria-pressed') !== 'true'); });
  skip.addEventListener('click', function () { if (scene) { scene.skip(); finishScene(); } });
  window.addEventListener('pagehide', function () { if (scene) scene.dispose(); scene = null; });
  motion.addEventListener('change', function () { if (scene && motion.matches) { scene.static(); finishScene(); } });
  start();
})();
