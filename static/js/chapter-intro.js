/* Existing page -> chapter intro -> existing reader. No replacement router. */
(function () {
  'use strict';
  var dialog = document.getElementById('chapterIntro');
  if (!dialog || !dialog.showModal || !window.KZChapterScenes || !window.KZChapterScenes[dialog.dataset.scene]) return;
  var createScene = window.KZChapterScenes[dialog.dataset.scene];
  var motion = matchMedia('(prefers-reduced-motion: reduce)');
  var stage = dialog.querySelector('.chapter-intro__stage'), scene = null, opener = null;
  var pause = dialog.querySelector('[data-intro-action="pause"]'), skip = dialog.querySelector('[data-intro-action="skip"]');
  var status = dialog.querySelector('.chapter-intro__status'), closing = false, closeTimer = 0, openRaf = 0, activeHash = '#/intro/' + dialog.dataset.chapterId;
  var duration = Number(dialog.dataset.duration) || 14;
  var previousHash = '', ownsHistory = false;
  function clamp(v) { return Math.max(0, Math.min(1, v)); }
  function smooth(a, b, v) { v = clamp((v - a) / (b - a));return v * v * (3 - 2 * v); }
  function changed(state) {
    dialog.classList.toggle('is-webgl', state.ready);
    dialog.classList.toggle('is-loading', state.mode === 'loading');
    dialog.style.setProperty('--intro-title', smooth(6.8, 8.2, state.time));
    dialog.style.setProperty('--intro-line1', smooth(8, 9.3, state.time));
    dialog.style.setProperty('--intro-line2', smooth(9, 10.4, state.time));
    dialog.style.setProperty('--intro-progress', clamp(state.time / duration));
    dialog.querySelector('.chapter-intro__time').textContent = '00 : ' + String(Math.floor(state.time)).padStart(2, '0');
    pause.disabled = state.held;skip.disabled = state.held;
    pause.textContent = state.paused ? 'Продолжить' : 'Пауза';pause.setAttribute('aria-pressed', String(state.paused));
    status.textContent = state.mode === 'static' ? 'Неподвижный вид. Чтение доступно.' : state.held ? 'Можно читать или повторить заставку.' : '';
  }
  function dispose() { if (scene) scene.dispose();scene = null; }
  function start() {
    dispose();var old = stage.querySelector('canvas'), canvas = old.cloneNode(false);old.replaceWith(canvas);
    changed({time: motion.matches ? duration : 0, mode: motion.matches ? 'static' : 'loading', paused: false, ready: false, held: motion.matches});
    var still = dialog.querySelector('.chapter-intro__still');
    var cutout = dialog.querySelector('.chapter-intro__mask');
    var gas = dialog.querySelector('.chapter-intro__gas');
    scene = createScene(canvas, stage, {image: still.currentSrc || still.src, cutout: cutout.currentSrc || cutout.src, gas: gas.currentSrc || gas.src, duration: duration, reduced: motion.matches}, changed);
  }
  function open(link, fromHistory) {
    if (dialog.open && !closing) return;
    if (closing) finishClose();
    clearTimeout(closeTimer);closing = false;
    opener = link || document.querySelector('[data-chapter-intro="' + dialog.dataset.chapterId + '"]');
    if (!fromHistory) { previousHash = location.hash;history.pushState({kzChapterIntro: dialog.dataset.chapterId}, '', activeHash);ownsHistory = true; }
    else ownsHistory = Boolean(history.state && history.state.kzChapterIntro);
    dialog.showModal();document.body.classList.add('chapter-intro-open');start();
    openRaf = requestAnimationFrame(function () { openRaf = 0;if (dialog.open && !closing) dialog.classList.add('is-visible'); });
  }
  function finishClose() {
    clearTimeout(closeTimer);dispose();dialog.classList.remove('is-visible', 'is-webgl', 'is-loading');
    if (dialog.open) dialog.close();document.body.classList.remove('chapter-intro-open');closing = false;
    if (opener && document.contains(opener)) opener.focus({preventScroll: true});
  }
  function close(fromHistory) {
    if (!dialog.open || closing) return;
    closing = true;cancelAnimationFrame(openRaf);openRaf = 0;dispose();dialog.classList.remove('is-visible');
    if (!fromHistory && location.hash === activeHash) {
      if (ownsHistory) history.back();else history.replaceState(null, '', location.pathname + location.search + previousHash);
    }
    closeTimer = setTimeout(finishClose, motion.matches ? 0 : 350);
  }
  // Capture before the existing decorative read-button transition.
  document.addEventListener('click', function (e) {
    var link = e.target.closest && e.target.closest('a[data-chapter-intro]');
    if (!link || link.dataset.chapterIntro !== dialog.dataset.chapterId || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || link.hasAttribute('download') || (link.target && link.target !== '_self')) return;
    e.preventDefault();e.stopImmediatePropagation();open(link, false);
  }, true);
  dialog.addEventListener('click', function (e) {
    var button = e.target.closest('[data-intro-action]');if (!button) return;
    var action = button.dataset.introAction;
    if (action === 'close') close(false);
    if (action === 'pause' && scene) scene.pause(pause.getAttribute('aria-pressed') !== 'true');
    if (action === 'skip' && scene) scene.skip();
    if (action === 'replay' && !closing) start();
  });
  dialog.addEventListener('cancel', function (e) { e.preventDefault();close(false); });
  dialog.addEventListener('close', function () { if (scene) finishClose(); });
  dialog.querySelector('.chapter-intro__read').addEventListener('click', function (e) { if (e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey && !e.defaultPrevented) dispose(); });
  function syncRoute() { if (location.hash === activeHash) open(null, true);else close(true); }
  window.addEventListener('hashchange', syncRoute);
  window.addEventListener('popstate', syncRoute);
  window.addEventListener('pagehide', dispose);
  window.addEventListener('pageshow', function (e) { if (e.persisted && dialog.open) start(); });
  motion.addEventListener('change', function () { if (dialog.open && scene && motion.matches) scene.static(); });
  window.KZChapterIntro = {ready: true, diagnostics: function () {return {open: dialog.open, closing: closing, scene: scene ? scene.diagnostics() : null};}};
  if (location.hash === activeHash) open(null, true);
})();
