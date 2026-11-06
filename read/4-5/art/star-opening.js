const stage = document.querySelector('.star-stage');
const canvas = stage.querySelector('canvas');
const ctx = canvas.getContext('2d');
const photo = stage.querySelector('img');
const toggle = document.querySelector('#starToggle');
const replay = document.querySelector('#starReplay');
const touch = document.querySelector('#starTouch');
const motion = matchMedia('(prefers-reduced-motion: reduce)');
const W = 1774, H = 887, CX = 891, CY = 355;
const duration = 7200;
const clamp = n => Math.min(1, Math.max(0, n));
const ease = n => clamp(n) ** 2 * (3 - 2 * clamp(n));
let frame = 0, time = 0, previous = 0, paused = false;

const wall = document.createElement('canvas');
wall.width = 470;
wall.height = 640;
const texture = wall.getContext('2d');
const ash = Array.from({ length: 540 }, (_, i) => {
  const x = 670 + (i % 18) * 25 + Math.random() * 20;
  const y = 55 + Math.floor(i / 18) * 20 + Math.random() * 16;
  return { x, y, delay: Math.hypot(x - CX, y - CY) * 1.4,
    dx: (x - CX) * .8 + (Math.random() - .5) * 320,
    depth: Math.random(), size: 1 + Math.random() ** 2 * 10, turn: Math.random() * 9 };
});

function glow(x, y, radius, color) {
  const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
  gradient.addColorStop(0, color);
  gradient.addColorStop(1, 'transparent');
  ctx.fillStyle = gradient;
  ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
}

function star(power) {
  ctx.save();
  ctx.translate(CX, CY);
  ctx.globalCompositeOperation = 'screen';
  ctx.globalAlpha = power * .68;
  glow(0, 0, 250, '#c6dc61');
  for (let i = 0; i < 7; i++) {
    ctx.save();
    ctx.rotate(i * Math.PI * 2 / 7);
    const length = 75 + power * 105;
    const ray = ctx.createLinearGradient(0, 0, 0, -length);
    ray.addColorStop(0, '#f9ffc9');
    ray.addColorStop(.56, '#d7ee7d');
    ray.addColorStop(1, 'transparent');
    ctx.fillStyle = ray;
    ctx.shadowBlur = 22;
    ctx.shadowColor = '#cce64e';
    ctx.beginPath();
    ctx.moveTo(-8, 4);
    ctx.quadraticCurveTo(-13, -length * .47, 0, -length);
    ctx.quadraticCurveTo(10, -length * .55, 8, 4);
    ctx.fill();
    ctx.restore();
  }
  ctx.restore();
}

function draw(t) {
  const fall = t - 1880;
  const reveal = ease(fall / 620);
  const zoom = 1 + .19 * ease(t / 4200);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, W, H);
  ctx.save();
  ctx.translate(CX, CY);
  ctx.scale(zoom, zoom);
  ctx.translate(-CX, -CY);
  ctx.drawImage(photo, 0, 0, W, H);
  if (fall < 0) {
    ctx.save();
    ctx.globalCompositeOperation = 'screen';
    ctx.globalAlpha = .37;
    glow(CX + 440 * (1 - ease(t / 1680)), CY, 255, '#e6efc8');
    ctx.restore();
  }
  ctx.save();
  ctx.globalAlpha = reveal;
  ctx.drawImage(wall, 660, 42);
  ctx.restore();
  const flash = Math.max(0, 1 - Math.abs(fall - 120) / 320);
  if (flash) {
    ctx.save();
    ctx.globalAlpha = flash * .57;
    glow(CX, CY, 295, '#fffde2');
    ctx.restore();
  }
  if (fall > 0) {
    star(ease((fall - 350) / 1150));
    for (const p of ash) {
      const age = (fall - p.delay) / (1250 + p.depth * 1150);
      if (age < 0 || age >= 1) continue;
      const x = p.x + p.dx * age;
      const y = p.y + age * age * (H * (.29 + p.depth * .52));
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(age * p.turn);
      ctx.globalAlpha = (1 - age) * (.3 + p.depth * .65);
      ctx.fillStyle = p.depth > .75 ? '#a6a291' : '#676963';
      const size = p.size * (1 + age * p.depth * 1.4);
      ctx.beginPath();
      ctx.moveTo(-size / 2, 0);
      ctx.lineTo(size * .24, -size * .34);
      ctx.lineTo(size * .48, size * .12);
      ctx.lineTo(-size * .12, size * .31);
      ctx.fill();
      ctx.restore();
    }
  }
  ctx.restore();
  ctx.fillStyle = 'rgba(2,7,9,' + (.16 + .84 * ease((t - 5600) / 1600)) + ')';
  ctx.fillRect(0, 0, W, H);
}

function tick(now) {
  if (previous) time += Math.min(50, now - previous);
  previous = now;
  draw(Math.min(time, duration));
  if (time < duration) frame = requestAnimationFrame(tick);
  else { frame = 0; toggle.hidden = true; }
}

function start(at = 0) {
  cancelAnimationFrame(frame);
  time = at;
  previous = 0;
  paused = false;
  toggle.hidden = false;
  toggle.textContent = 'Пауза';
  frame = requestAnimationFrame(tick);
}

function setup() {
  // Sample the exposed wall beside the poster, avoiding the nearby frames.
  texture.drawImage(photo, 1120, 295, 112, 298, 0, 0, 470, 640);
  texture.fillStyle = '#454b43aa';
  texture.fillRect(0, 0, 470, 640);
  texture.globalCompositeOperation = 'destination-in';
  for (const [x, y, length] of [[470, 0, 470], [0, 640, 640]]) {
    const mask = texture.createLinearGradient(0, 0, x, y);
    mask.addColorStop(0, 'transparent');
    mask.addColorStop(24 / length, '#fff');
    mask.addColorStop(1 - 24 / length, '#fff');
    mask.addColorStop(1, 'transparent');
    texture.fillStyle = mask;
    texture.fillRect(0, 0, 470, 640);
  }
  draw(0);
  replay.hidden = false;
  touch.hidden = false;
  if (!motion.matches) start();
}

toggle.addEventListener('click', () => {
  paused = !paused;
  if (paused) { cancelAnimationFrame(frame); frame = 0; }
  else { previous = 0; frame = requestAnimationFrame(tick); }
  toggle.textContent = paused ? 'Продолжить' : 'Пауза';
});
replay.addEventListener('click', () => start());
touch.addEventListener('click', () => start(1750));
motion.addEventListener('change', () => {
  cancelAnimationFrame(frame);
  frame = 0;
  toggle.hidden = true;
  if (motion.matches) draw(0);
  else start();
});
if (ctx && texture) {
  if (photo.complete && photo.naturalWidth) setup();
  else photo.addEventListener('load', setup, { once: true });
}
