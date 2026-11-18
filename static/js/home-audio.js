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
