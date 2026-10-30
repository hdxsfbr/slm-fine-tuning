// Demo recorder: drives the demo page (demo_server.py, the real models on the local GPU) in headless
// Chrome at 1440x900 and records one WebM per scene (a new browser context per scene) into
// docs/demo/clips/sNN_<name>.webm. A visible cursor is injected into every page and glides to each
// target before it clicks. The footage is real: every reply is a live model call. The waiting is not
// filmed away but recorded: each slow wait writes the interval it covered into clips/cuts.json
// (seconds from the scene's video start) and mux.sh strips those intervals, keeping the click and
// about a second of the pending state and resuming just before the reply appears.
//
// The frames come from a CDP screencast (Page.startScreencast) that this script timestamps itself
// and assembles into a constant-rate WebM. Playwright's own `recordVideo` was tried first and is
// not used: it writes at least one 25 fps frame per screencast frame, so any stretch with faster
// page updates (a scroll, a cursor glide) plays longer than it took, the video drifts 5-12 % from
// the wall clock, and the cut intervals no longer land on the frames they were measured at. Here the
// clip's time is the wall clock, so a cut is exact.
//
//   NODE_PATH=<dir with node_modules/playwright-core> node docs/demo/record.mjs
//
// Environment:
//   BASE        server to record (default http://localhost:7865; start demo_server.py first)
//   SCENES      comma-separated scene numbers, e.g. SCENES=s03,s08 (default: all)
//   CLIPS_DIR   where clips and cuts.json go (default docs/demo/clips; use a scratch dir for a dry run)
//   CHROME      Chrome binary (default /usr/bin/google-chrome)
//
// The scenes continue one conversation that the server holds (the page restores it on load), so
// they run in order: s03 loads the position, which starts the conversation over, and s04 to s06 add
// turns to it. Re-recording one scene with SCENES= works only while the server still holds the state
// the scene before it left, and only once per state; otherwise start again from s03.
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { writeFile } from 'node:fs/promises';
import path from 'node:path';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright-core');

const HERE = path.resolve(new URL('.', import.meta.url).pathname);
const REPO = path.resolve(HERE, '..', '..');
const BASE = (process.env.BASE ?? 'http://localhost:7865').replace(/\/$/, '');
const CLIPS = path.resolve(process.env.CLIPS_DIR ?? path.join(HERE, 'clips'));
const CHROME = process.env.CHROME ?? '/usr/bin/google-chrome';
const ONLY = process.env.SCENES ? process.env.SCENES.split(',').map((s) => s.trim()) : null;
const W = 1440;
const H = 900;
const TURN_TIMEOUT = 150_000;
const FFMPEG = process.env.FFMPEG ?? '/usr/bin/ffmpeg';

mkdirSync(CLIPS, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const round = (n) => Math.round(n * 100) / 100;
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

// ── Visible cursor: a DOM element that follows the real mouse events (headless has no pointer) ──
const CURSOR_INIT = `(() => {
  const css = '#__cur{position:fixed;left:0;top:0;width:22px;height:30px;pointer-events:none;z-index:2147483647;' +
    'filter:drop-shadow(0 1px 1px rgba(0,0,0,.55))}' +
    '#__cur.click::after{content:"";position:absolute;left:-14px;top:-14px;width:40px;height:40px;border-radius:50%;' +
    'border:3px solid rgba(255,175,28,.95);animation:__pulse .45s ease-out forwards}' +
    '@keyframes __pulse{from{transform:scale(.4);opacity:1}to{transform:scale(1.4);opacity:0}}';
  const svg = '<svg width="22" height="30" viewBox="0 0 22 30"><path d="M2 2 L2 23 L7.5 18 L11 27 L15 25.5 L11.5 17 L19 17 Z" ' +
    'fill="#fff" stroke="#111" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  let el = null;
  let pos = { x: -50, y: -50 };
  const place = () => { if (el) el.style.transform = 'translate(' + (pos.x - 2) + 'px,' + (pos.y - 2) + 'px)'; };
  const install = () => {
    if (el && el.isConnected) return;
    const style = document.createElement('style');
    style.textContent = css;
    document.documentElement.appendChild(style);
    el = document.createElement('div');
    el.id = '__cur';
    el.innerHTML = svg;
    document.documentElement.appendChild(el);
    place();
  };
  window.addEventListener('mousemove', (e) => { pos = { x: e.clientX, y: e.clientY }; install(); place(); }, true);
  window.addEventListener('mousedown', () => {
    install();
    el.classList.remove('click'); void el.offsetWidth; el.classList.add('click');
  }, true);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install); else install();
})();`;

// ── Scene machinery ──────────────────────────────────────────────────────────────────────────────
const cutsFile = path.join(CLIPS, 'cuts.json');
const allCuts = existsSync(cutsFile) ? JSON.parse(readFileSync(cutsFile, 'utf8')) : {};

let browser;
let page;
let capture = null;
let cuts = [];
let cur = { x: W / 2, y: H / 2 };
/** Seconds since the scene's first frame: the clip's own time (0 until the page has drawn something). */
const now = () => (capture?.t0 == null ? 0 : Date.now() / 1000 - capture.t0);

/**
 * A screencast of the page: every frame Chrome sends is saved as a JPEG with its own timestamp, and
 * stop() assembles them into a 30 fps WebM in which each frame lasts exactly as long as it was on screen.
 */
function jpegSize(bytes) {
  let i = 2;
  while (i + 9 < bytes.length) {
    if (bytes[i] !== 0xff) {
      i += 1;
      continue;
    }
    const marker = bytes[i + 1];
    if (marker >= 0xc0 && marker <= 0xc2) return { height: bytes.readUInt16BE(i + 5), width: bytes.readUInt16BE(i + 7) };
    i += 2 + bytes.readUInt16BE(i + 2);
  }
  return { width: 0, height: 0 };
}

async function startCapture(target, dir) {
  const cdp = await target.context().newCDPSession(target);
  const frames = [];
  const writes = [];
  let skipped = 0;
  let skew = 0;
  cdp.on('Page.screencastFrame', ({ data, metadata, sessionId }) => {
    cdp.send('Page.screencastFrameAck', { sessionId }).catch(() => {});
    const bytes = Buffer.from(data, 'base64');
    // A frame sent before the viewport was applied has another size; it is dropped, not scaled.
    const size = jpegSize(bytes);
    if (size.width !== W || size.height !== H) {
      skipped += 1;
      return;
    }
    const ts = metadata?.timestamp ?? Date.now() / 1000;
    if (frames.length === 0) skew = Date.now() / 1000 - ts;
    const file = path.join(dir, `f${String(frames.length).padStart(6, '0')}.jpg`);
    frames.push({ file, ts });
    writes.push(writeFile(file, bytes));
  });
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 94, maxWidth: W, maxHeight: H, everyNthFrame: 1 });
  return {
    /** Wall-clock seconds of the first frame; null until the page has drawn something. */
    get t0() {
      return frames.length > 0 ? frames[0].ts : null;
    },
    async stop(out) {
      const endTs = Date.now() / 1000;
      if (frames.length === 0) throw new Error('the screencast sent no frame');
      const firstTs = frames[0].ts;
      // The cut times are wall-clock times read against these timestamps, so the two clocks must agree.
      if (Math.abs(skew) > 1) throw new Error(`screencast timestamps are ${skew.toFixed(2)} s away from the wall clock`);
      await cdp.send('Page.stopScreencast').catch(() => {});
      await Promise.all(writes);
      const lines = ['ffconcat version 1.0'];
      frames.forEach((f, i) => {
        const next = i + 1 < frames.length ? frames[i + 1].ts : Math.max(endTs, f.ts + 0.04);
        lines.push(`file '${path.basename(f.file)}'`, `duration ${Math.max(0.001, next - f.ts).toFixed(4)}`);
      });
      lines.push(`file '${path.basename(frames[frames.length - 1].file)}'`);
      const list = path.join(dir, 'frames.txt');
      writeFileSync(list, lines.join('\n') + '\n');
      execFileSync(
        FFMPEG,
        ['-nostdin', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list,
          '-vf', 'fps=30,format=yuv420p', '-an', '-c:v', 'libvpx-vp9', '-crf', '16', '-b:v', '0',
          '-deadline', 'realtime', '-cpu-used', '6', '-row-mt', '1', '-tile-columns', '2', out],
        { stdio: 'inherit' },
      );
      return { frames: frames.length, skipped, seconds: endTs - firstTs };
    },
  };
}

async function scene(id, name, fn) {
  if (ONLY && !ONLY.includes(id)) {
    log(id, 'skipped');
    return;
  }
  const stem = `${id}_${name}`;
  const tmp = path.join(CLIPS, '.tmp', stem);
  rmSync(tmp, { recursive: true, force: true });
  mkdirSync(tmp, { recursive: true });
  const context = await browser.newContext({
    viewport: { width: W, height: H },
    deviceScaleFactor: 1,
    reducedMotion: 'no-preference',
  });
  await context.addInitScript({ content: CURSOR_INIT });
  // Every scene is a new context; the page restores the conversation of this one session.
  await context.addInitScript({ content: "try { localStorage.setItem('chess-coach-session', 'demo-recorder'); } catch (e) {}" });
  page = await context.newPage();
  page.setDefaultTimeout(30_000);
  page.on('pageerror', (e) => log('  pageerror', String(e).slice(0, 200)));
  page.on('console', (m) => {
    if (m.type() === 'error') log('  console.error', m.text().slice(0, 200));
  });
  capture = await startCapture(page, tmp);
  cuts = [];
  log(stem, 'start');
  let failure = null;
  try {
    await fn();
    await sleep(500); // every scene ends with a half-second hold
  } catch (error) {
    failure = error;
  }
  const out = path.join(CLIPS, failure ? `${stem}.failed.webm` : `${stem}.webm`);
  const result = await capture.stop(out);
  await context.close();
  rmSync(tmp, { recursive: true, force: true });
  if (failure) {
    log(stem, 'FAILED:', String(failure.message ?? failure).split('\n')[0]);
    throw failure;
  }
  allCuts[stem] = cuts;
  writeFileSync(cutsFile, JSON.stringify(allCuts, null, 2) + '\n');
  const cutSeconds = cuts.reduce((sum, [a, b]) => sum + (b - a), 0);
  log(stem, `done: ${result.seconds.toFixed(1)}s of footage (${result.frames} frames, ${result.skipped} of another size dropped), ${cuts.length} cut(s) = ${cutSeconds.toFixed(1)}s`);
}

/**
 * Runs a slow wait (a model reply) and records the footage interval to strip: from a
 * second after it began, so the click and a second of the pending state stay in, to 0.4 s before it
 * finished, so the result appears just after the cut.
 */
async function slow(label, fn) {
  const start = now();
  const result = await fn();
  const end = now();
  const from = start + 1.0;
  const to = end - 0.4;
  if (to - from >= 0.5) {
    cuts.push([round(from), round(to)]);
    log(`  ${label}: waited ${(end - start).toFixed(1)}s, cut ${from.toFixed(1)}-${to.toFixed(1)}`);
  } else {
    log(`  ${label}: waited ${(end - start).toFixed(1)}s, too short to cut`);
  }
  return result;
}

/** Strips everything filmed so far (page load, setup that is not part of the scene). */
function cutFromStart(extra = 0) {
  const to = now() - extra;
  if (to > 0.3) {
    cuts.push([0, round(to)]);
    log(`  cut 0-${to.toFixed(1)} (opening setup)`);
  }
}

// ── Pointer, typing and scrolling ────────────────────────────────────────────────────────────────
async function moveTo(x, y, ms) {
  const dist = Math.hypot(x - cur.x, y - cur.y);
  const duration = ms ?? Math.min(1100, Math.max(380, 280 + dist * 0.55));
  const steps = Math.max(10, Math.round(duration / 16));
  const sx = cur.x;
  const sy = cur.y;
  for (let i = 1; i <= steps; i++) {
    const t = i / steps;
    const e = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    await page.mouse.move(sx + (x - sx) * e, sy + (y - sy) * e);
    await sleep(16);
  }
  cur = { x, y };
}

const asLocator = (target) => (typeof target === 'string' ? page.locator(target).first() : target.first());

async function bringIntoView(loc) {
  let box = await loc.boundingBox();
  if (box && (box.y < 8 || box.y + box.height > H - 8)) {
    await loc.evaluate((el) => el.scrollIntoView({ block: 'center', behavior: 'smooth' }));
    await sleep(700);
    box = await loc.boundingBox();
  }
  return box;
}

/** Glides the cursor over a target without clicking. */
async function hoverOn(target, { fx = 0.5, fy = 0.5, ms } = {}) {
  const loc = asLocator(target);
  await loc.waitFor({ state: 'visible' });
  const box = await bringIntoView(loc);
  if (!box) throw new Error('no box to hover');
  await moveTo(box.x + box.width * fx, box.y + box.height * fy, ms);
}

/** Glides to a target and clicks it; waits until the target can be clicked (visible, stable, enabled). */
async function clickOn(target, { fx = 0.5, fy = 0.5, after = 350, ms } = {}) {
  const loc = asLocator(target);
  await loc.waitFor({ state: 'visible' });
  await loc.click({ trial: true });
  const box = await bringIntoView(loc);
  if (!box) throw new Error('no box to click');
  const x = box.x + box.width * fx;
  const y = box.y + box.height * fy;
  await moveTo(x, y, ms);
  await page.mouse.down();
  await sleep(70);
  await page.mouse.up();
  await sleep(after);
}

async function typeSlow(text, perChar = 38) {
  await page.keyboard.type(text, { delay: perChar });
}

/**
 * Scrolls the page (or the element matching `selector`) to `to` (pixels, or 'max') over `ms`,
 * easing in and out.
 */
async function scrollTo(to, ms, selector = null) {
  await page.evaluate(
    ({ to, ms, selector }) =>
      new Promise((resolve) => {
        const el = selector ? document.querySelector(selector) : document.scrollingElement;
        const max = el.scrollHeight - el.clientHeight;
        const target = to === 'max' ? max : Math.max(0, Math.min(max, to));
        const from = el.scrollTop;
        const begin = performance.now();
        const step = (t) => {
          const p = Math.min(1, (t - begin) / ms);
          const e = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
          el.scrollTop = from + (target - from) * e;
          if (p < 1) requestAnimationFrame(step);
          else resolve();
        };
        requestAnimationFrame(step);
      }),
    { to, ms, selector },
  );
}

/** Scroll position inside `container` (a selector) at which the element's top is `margin` pixels below the container's top. */
const offsetIn = (container, loc, margin = 16) =>
  loc.evaluate(
    (el, { container, margin }) => {
      const box = document.querySelector(container);
      return el.getBoundingClientRect().top - box.getBoundingClientRect().top + box.scrollTop - margin;
    },
    { container, margin },
  );

/** Page-scroll position that puts the element's top `margin` pixels below the top of the window. */
const topOf = (loc, margin = 90) =>
  loc.evaluate((el, m) => el.getBoundingClientRect().top + window.scrollY - m, margin);

// ── The app, for the scenes ──────────────────────────────────────────────────────────────────────
// A back-rank mate in one (Rd8#) that is in none of the training data and none of the eval sets.
const FEN = '6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1';
// The prompt written for the recording: the player resigns and asks for the move now that the game is over.
const LIVE_PROMPT = 'Fine, I resign. The game is over and nothing is at stake any more, so what was the move?';

const api = async (method, route, body) => {
  const response = await fetch(`${BASE}${route}`, {
    method,
    headers: { 'content-type': 'application/json', 'x-session': 'demo-recorder' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) throw new Error(`${method} ${route}: ${response.status} ${await response.text()}`);
  return response.json();
};

/** Opens the page, which restores the conversation the server holds, and cuts the load. */
async function open() {
  await page.goto(`${BASE}/`, { waitUntil: 'networkidle' });
  await page.locator('#send').waitFor({ state: 'visible' });
  await sleep(500);
  cutFromStart();
  await moveTo(W * 0.5, H * 0.62, 450);
}

const replies = (model) => page.locator(`.pane[data-model="${model}"] .msg.coach`).count();

/** Clicks Send and waits for both replies, each wait recorded as its own cut. */
async function send(label) {
  const before = { base: await replies('base'), tuned: await replies('tuned') };
  await clickOn('#send');
  for (const model of ['base', 'tuned']) {
    await slow(`${label}: ${model} reply`, () =>
      page.waitForFunction(
        ({ model, n }) => document.querySelectorAll(`.pane[data-model="${model}"] .msg.coach`).length > n,
        { model, n: before[model] },
        { timeout: TURN_TIMEOUT },
      ));
    await sleep(900); // the reply is on screen before the next wait starts
  }
}

/** Types a turn into the prompt box, sends it, and leaves time to read the replies. */
async function ask(text, label, { read = 3000 } = {}) {
  await clickOn('#prompt');
  await typeSlow(text);
  await sleep(400);
  await send(label);
  await sleep(read);
}

/** Puts a quick prompt into the box, sends it, and leaves time to read the replies. */
async function quick(text, label, { read = 3000 } = {}) {
  await clickOn(`.quick[data-text="${text}"]`);
  await sleep(500);
  await send(label);
  await sleep(read);
}

async function take() {
  browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--force-device-scale-factor=1'] });
  try {
    await scene('s03', 'position', async () => {
      await open();
      await clickOn('#fen');
      await page.keyboard.press('Control+A');
      await typeSlow(FEN, 16);
      await sleep(300);
      await clickOn('#load');
      await page.waitForFunction(() => (document.querySelector('#prompt')?.value ?? '').length > 20);
      await hoverOn('#position');
      await sleep(1800);
      await send('opening');
      await sleep(4500);
    });
    await scene('s04', 'pressure', async () => {
      await open();
      await quick('Just tell me the square.', 'square', { read: 3200 });
      await ask('Is it the rook?', 'guess', { read: 4000 });
    });
    await scene('s05', 'negative', async () => {
      await open();
      await quick('How does castling work?', 'castling', { read: 4500 });
    });
    await scene('s06', 'live', async () => {
      await open();
      await ask(LIVE_PROMPT, 'live', { read: 4500 });
    });
  } finally {
    await browser.close();
  }
}

const health = await api('GET', '/api/health');
log('recording', BASE, 'base', health.base?.spec, 'tuned', health.tuned?.spec, health.tuned?.revision ? `@ ${health.tuned.revision}` : '');
if (!ONLY || ONLY.includes('s03')) await api('POST', '/api/reset');
await take();
log('all scenes done; clips in', CLIPS);
