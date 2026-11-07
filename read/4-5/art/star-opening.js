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
let beam, burst, halo, rays;

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

function glowSprite(color) {
  const sprite = document.createElement('canvas');
  sprite.width = sprite.height = 256;
  const paint = sprite.getContext('2d');
  const gradient = paint.createRadialGradient(128, 128, 0, 128, 128, 128);
  gradient.addColorStop(0, color);
  gradient.addColorStop(1, 'transparent');
  paint.fillStyle = gradient;
  paint.fillRect(0, 0, 256, 256);
  return sprite;
}

function raySprite() {
  const sprite = document.createElement('canvas');
  sprite.width = sprite.height = 420;
  const paint = sprite.getContext('2d');
  paint.translate(210, 210);
  const length = 180;
  const ray = paint.createLinearGradient(0, 0, 0, -length);
  ray.addColorStop(0, '#f9ffc9');
  ray.addColorStop(.56, '#d7ee7d');
  ray.addColorStop(1, 'transparent');
  paint.fillStyle = ray;
  paint.shadowBlur = 22;
  paint.shadowColor = '#cce64e';
  for (let i = 0; i < 7; i++) {
    paint.beginPath();
    paint.moveTo(-8, 4);
    paint.quadraticCurveTo(-13, -length * .47, 0, -length);
    paint.quadraticCurveTo(10, -length * .55, 8, 4);
    paint.fill();
    paint.rotate(Math.PI * 2 / 7);
  }
  return sprite;
}

function star(power) {
  if (!power) return;
  ctx.save();
  ctx.globalCompositeOperation = 'screen';
  ctx.globalAlpha = power * .68;
  ctx.drawImage(halo, CX - 250, CY - 250, 500, 500);
  const size = 175 + power * 245;
  ctx.drawImage(rays, CX - size / 2, CY - size / 2, size, size);
  ctx.restore();
}

function draw(t) {
  const fall = t - 1880;
  const reveal = ease(fall / 620);
  const zoom = 1 + .19 * ease(t / 4200);
  ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);
  ctx.save();
  ctx.translate(CX, CY);
  ctx.scale(zoom, zoom);
  ctx.translate(-CX, -CY);
  ctx.drawImage(photo, 0, 0, W, H);
  if (fall < 0) {
    ctx.save();
    ctx.globalCompositeOperation = 'screen';
    ctx.globalAlpha = .37;
    ctx.drawImage(beam, CX + 440 * (1 - ease(t / 1680)) - 255, CY - 255, 510, 510);
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
    ctx.drawImage(burst, CX - 295, CY - 295, 590, 590);
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
  beam = glowSprite('#e6efc8');
  burst = glowSprite('#fffde2');
  halo = glowSprite('#c6dc61');
  rays = raySprite();
  // Sample the exposed wall beside the poster, avoiding the nearby frames.
  const sx = photo.naturalWidth / W;
  const sy = photo.naturalHeight / H;
  texture.drawImage(photo, 1120 * sx, 295 * sy, 112 * sx, 298 * sy, 0, 0, 470, 640);
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
  const resize = () => {
    const scale = Math.min(1, Math.max(stage.clientWidth / W, stage.clientHeight / H) *
      Math.min(devicePixelRatio, 1.5));
    canvas.width = Math.max(2, Math.round(W * scale / 2) * 2);
    canvas.height = canvas.width / 2;
    draw(Math.min(time, duration));
  };
  resize();
  new ResizeObserver(resize).observe(stage);
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
  if (!rays) return;
  cancelAnimationFrame(frame);
  frame = 0;
  toggle.hidden = true;
  if (motion.matches) { time = 0; draw(0); }
  else start();
});
if (ctx && texture) {
  if (photo.complete && photo.naturalWidth) setup();
  else photo.addEventListener('load', setup, { once: true });
}
