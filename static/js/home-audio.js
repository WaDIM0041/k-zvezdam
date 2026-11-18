(function () {
  'use strict';
  var player = document.getElementById('homeAudioPlayer');
  if (!player) return;
  var audio = player.querySelector('audio');
  var controls = player.querySelector('[data-audio-controls]');
  var play = player.querySelector('[data-audio-play]');
  var expand = player.querySelector('[data-audio-expand]');
  var panel = player.querySelector('[data-audio-panel]');
  var seek = player.querySelector('[data-audio-seek]');
  var elapsed = player.querySelector('[data-audio-elapsed]');
  var duration = player.querySelector('[data-audio-duration]');
  var volume = player.querySelector('[data-audio-volume]');
  var mute = player.querySelector('[data-audio-mute]');
  var status = player.querySelector('[data-audio-status]');

  // A transparent light field follows the player. Its canvas ends at the
  // viewport edges, so the outward waves never create horizontal scrolling.
  function createCosmicWaves() {
    var canvas = document.createElement('canvas');
    var context = canvas.getContext('2d');
    if (!context) return;
    canvas.className = 'home-audio__waves';
    canvas.setAttribute('aria-hidden', 'true');
    player.prepend(canvas);
    var reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    var width = 0, center = 0, frame = 0, previous = 0;
    var strength = 0, phase = 0, visible = true, sounding = false;
    var fieldHeight = 280;
    var timing = { arrival: 1.1, departure: .55, cycle: 6.8 };

    function resize() {
      var bounds = player.getBoundingClientRect();
      var nextWidth = document.documentElement.clientWidth;
      var ratio = Math.min(window.devicePixelRatio || 1, 1.5);
      width = nextWidth;
      center = bounds.left + bounds.width / 2;
      canvas.style.left = -bounds.left + 'px';
      canvas.style.width = width + 'px';
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(fieldHeight * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    }

    function isAudible() {
      return sounding && !audio.paused && !audio.ended && !audio.muted && audio.volume > 0;
    }

    // Cache soft optical brushes once; no blur filters or per-frame gradients.
    // Overlapping light samples make flowing volumes, with no outlined crests.
    function lightBrush(color) {
      var brush = document.createElement('canvas');
      brush.width = brush.height = 64;
      var ink = brush.getContext('2d');
      var light = ink.createRadialGradient(32, 32, 0, 32, 32, 32);
      light.addColorStop(0, 'rgba(' + color + ',1)');
      light.addColorStop(.25, 'rgba(' + color + ',.58)');
      light.addColorStop(.6, 'rgba(' + color + ',.12)');
      light.addColorStop(1, 'rgba(' + color + ',0)');
      ink.fillStyle = light;
      ink.fillRect(0, 0, 64, 64);
      return brush;
    }
    var brushes = [lightBrush('93,192,244'), lightBrush('155,121,234'), lightBrush('170,224,255')];

    function flowLight(side, layer) {
      var reach = Math.min(820, width * .65 + 160);
      var step = 8;
      for (var distance = 0; distance < reach; distance += step) {
        var spread = 1 - Math.exp(-distance / 110);
        var outward = distance / 100 - phase * Math.PI * 2 / timing.cycle;
        var swell = .5 + .5 * Math.sin(outward + layer * 1.8);
        var fade = Math.pow(1 - distance / reach, 1.35);
        var y = fieldHeight / 2 + spread * (
          Math.sin(outward * .72 + layer * 2.1) * 27 +
          Math.sin(distance / 190 - phase * .24) * 18 + (layer - 1) * 24);
        var thickness = 34 + spread * (35 + swell * 26);
        var x = center + side * distance;
        context.globalAlpha = strength * fade * (.09 + swell * .12);
        context.drawImage(brushes[layer], x - step * 2, y - thickness / 2, step * 4, thickness);
        // A soft, narrow caustic inside the mist gives the light depth.
        context.globalAlpha = strength * fade * (.04 + swell * .12);
        context.drawImage(brushes[2], x - step * 1.5, y - 7, step * 3, 14);
      }
    }

    function draw(now) {
      frame = 0;
      var delta = previous ? Math.min((now - previous) / 1000, .05) : 0;
      previous = now;
      var target = isAudible() ? 1 : 0;
      var fade = target ? timing.arrival : timing.departure;
      strength += (target - strength) * (1 - Math.exp(-delta * 3 / fade));
      phase += delta;
      context.clearRect(0, 0, width, fieldHeight);
      if (strength > .003) {
        context.globalCompositeOperation = 'lighter';
        for (var layer = 0; layer < 3; layer++) {
          flowLight(-1, layer);
          flowLight(1, layer);
        }
        context.globalAlpha = 1;
      }
      if (target || strength > .003) frame = requestAnimationFrame(draw);
      else strength = 0;
    }

    function sync() {
      if (reduced.matches || document.hidden || !visible) {
        cancelAnimationFrame(frame);
        frame = 0;
        previous = 0;
        strength = 0;
        context.clearRect(0, 0, width, fieldHeight);
        return;
      }
      if (!frame && (isAudible() || strength > .003)) {
        previous = 0;
        frame = requestAnimationFrame(draw);
      }
    }

    audio.addEventListener('playing', function () { sounding = true; sync(); });
    ['pause', 'ended', 'waiting', 'error', 'emptied', 'seeking'].forEach(function (event) {
      audio.addEventListener(event, function () { sounding = false; sync(); });
    });
    audio.addEventListener('volumechange', sync);
    document.addEventListener('visibilitychange', sync);
    if (reduced.addEventListener) reduced.addEventListener('change', sync);
    else reduced.addListener(sync);
    window.addEventListener('resize', resize, { passive: true });
    if (window.ResizeObserver) new ResizeObserver(resize).observe(player);
    if (window.IntersectionObserver) {
      new IntersectionObserver(function (entries) {
        visible = entries[0].isIntersecting;
        sync();
      }, { rootMargin: '140px' }).observe(player);
    }
    resize();
  }

  createCosmicWaves();

  function formatTime(seconds) {
    if (!Number.isFinite(seconds)) return '0:00';
    return Math.floor(seconds / 60) + ':' + String(Math.floor(seconds % 60)).padStart(2, '0');
  }

  function updatePlayback() {
    var playing = !audio.paused && !audio.ended;
    play.textContent = playing ? 'Ⅱ' : '▶';
    play.setAttribute('aria-label', playing ? 'Приостановить музыку' : 'Включить музыку');
    play.setAttribute('aria-pressed', String(playing));
  }

  function updateProgress() {
    elapsed.textContent = formatTime(audio.currentTime);
    duration.textContent = formatTime(audio.duration);
    seek.disabled = !Number.isFinite(audio.duration) || audio.duration <= 0;
    if (!seek.disabled) seek.value = audio.currentTime / audio.duration * 1000;
    seek.setAttribute('aria-valuetext', formatTime(audio.currentTime) + ' из ' + formatTime(audio.duration));
  }

  play.addEventListener('click', async function () {
    if (!audio.paused) {
      audio.pause();
      return;
    }
    status.textContent = 'Загружаем музыку…';
    try {
      if (audio.error) audio.load();
      await audio.play();
      status.textContent = '';
    } catch (error) {
      if (error.name !== 'AbortError') status.textContent = 'Музыка не загрузилась. Проверьте интернет и нажмите воспроизведение ещё раз.';
      updatePlayback();
    }
  });

  expand.addEventListener('click', function () {
    var opened = expand.getAttribute('aria-expanded') !== 'true';
    expand.setAttribute('aria-expanded', String(opened));
    expand.setAttribute('aria-label', opened ? 'Свернуть плеер' : 'Развернуть плеер');
    panel.classList.toggle('is-open', opened);
    panel.inert = !opened;
  });

  seek.addEventListener('input', function () {
    if (Number.isFinite(audio.duration)) audio.currentTime = Number(seek.value) / 1000 * audio.duration;
  });
  volume.addEventListener('input', function () {
    audio.volume = Number(volume.value);
    audio.muted = audio.volume === 0;
  });
  mute.addEventListener('click', function () {
    audio.muted = !audio.muted;
    if (!audio.muted && audio.volume === 0) audio.volume = .5;
  });
  audio.addEventListener('volumechange', function () {
    volume.value = audio.muted ? 0 : audio.volume;
    mute.textContent = audio.muted ? 'Без звука' : 'Звук';
    mute.setAttribute('aria-pressed', String(audio.muted));
    mute.setAttribute('aria-label', audio.muted ? 'Включить звук' : 'Выключить звук');
  });
  ['play', 'pause', 'ended'].forEach(function (event) {
    audio.addEventListener(event, updatePlayback);
  });
  ['loadedmetadata', 'durationchange', 'timeupdate', 'seeked'].forEach(function (event) {
    audio.addEventListener(event, updateProgress);
  });
  audio.addEventListener('playing', function () { status.textContent = ''; });
  audio.addEventListener('waiting', function () { status.textContent = 'Загружаем музыку…'; });
  audio.addEventListener('error', function () {
    status.textContent = 'Музыка не загрузилась. Проверьте интернет и нажмите воспроизведение ещё раз.';
    updatePlayback();
  });
  controls.hidden = false;
  audio.controls = false;
  audio.hidden = true;
  updatePlayback();
  updateProgress();
})();
