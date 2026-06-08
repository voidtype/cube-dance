// Cube Dance — browser preview. Loads the REAL cube_dance engine in Pyodide
// (zero edits to the package), renders the LEDs with Three.js, drives reactivity
// from Web Audio, and previews dragged-in audio files or .py effects.

import * as THREE from 'three';
import { OrbitControls }   from 'three/addons/controls/OrbitControls.js';
import { EffectComposer }  from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass }      from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.29.4/full/';
const POS_SCALE = 5.5;     // model metres -> scene units
const BRIGHT = 1.7;        // push hot LEDs past the bloom threshold

const $ = s => document.querySelector(s);
const prog = $('#prog');
const setProg = m => { prog.textContent = m; };

// ---------------------------------------------------------------- Three.js
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NoToneMapping;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x05060a);
const camera = new THREE.PerspectiveCamera(58, innerWidth / innerHeight, 0.1, 2000);
camera.position.set(7, 4, 16);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = 0.06;
controls.autoRotate = true; controls.autoRotateSpeed = 0.55;

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.95, 0.45, 0.7);
composer.addPass(bloom);

const pointMat = new THREE.ShaderMaterial({
  uniforms: { uSize: { value: 90.0 }, uBright: { value: BRIGHT } },
  vertexColors: true, transparent: true, blending: THREE.AdditiveBlending,
  depthWrite: false, toneMapped: false,
  // NB: ShaderMaterial + vertexColors:true auto-injects `attribute vec3 color`,
  // so we must NOT redeclare it (that's a GLSL redefinition error).
  vertexShader: `varying vec3 vColor; uniform float uSize;
    void main(){ vColor=color; vec4 mv=modelViewMatrix*vec4(position,1.0);
      gl_PointSize=max(1.5, uSize/-mv.z); gl_Position=projectionMatrix*mv; }`,
  fragmentShader: `varying vec3 vColor; uniform float uBright;
    void main(){ vec2 uv=gl_PointCoord-0.5; float d=length(uv);
      float a=smoothstep(0.5,0.0,d); if(a<=0.0) discard;
      gl_FragColor=vec4(vColor*uBright, a); }`,
});
let points = null, colorAttr = null, N = 0;

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight); composer.setSize(innerWidth, innerHeight);
});

function buildCloud(posFlat) {
  N = posFlat.length / 3;
  const pos = new Float32Array(N * 3);
  let rmax = 0;
  for (let i = 0; i < N * 3; i++) pos[i] = posFlat[i] * POS_SCALE;
  for (let i = 0; i < N; i++) {
    const r = Math.hypot(pos[i*3], pos[i*3+1], pos[i*3+2]); if (r > rmax) rmax = r;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  colorAttr = new THREE.BufferAttribute(new Float32Array(N * 3), 3);
  colorAttr.setUsage(THREE.DynamicDrawUsage);
  geo.setAttribute('color', colorAttr);
  if (points) scene.remove(points);
  points = new THREE.Points(geo, pointMat); scene.add(points);
  const d = rmax * 2.4; camera.position.set(d*0.45, d*0.28, d*0.95); controls.update();
}

// ---------------------------------------------------------------- Web Audio
let actx, analyserL, analyserR, splitter, dataL, dataR, band, current = null;
const FFT = 2048;
function ensureAudio() {
  if (actx) return actx;
  actx = new (window.AudioContext || window.webkitAudioContext)();
  splitter = new ChannelSplitterNode(actx, { numberOfOutputs: 2 });
  analyserL = new AnalyserNode(actx, { fftSize: FFT, smoothingTimeConstant: 0.6 });
  analyserR = new AnalyserNode(actx, { fftSize: FFT, smoothingTimeConstant: 0.6 });
  splitter.connect(analyserL, 0); splitter.connect(analyserR, 1);
  dataL = new Float32Array(analyserL.frequencyBinCount);
  dataR = new Float32Array(analyserR.frequencyBinCount);
  band = computeBands(actx.sampleRate, FFT);
  return actx;
}
function computeBands(sr, fft) {
  const binCount = fft / 2, hzPerBin = (sr / 2) / binCount;
  const toBin = hz => Math.max(1, Math.min(binCount - 1, Math.round(hz / hzPerBin)));
  const LO = 30, HI = Math.min(16000, sr * 0.49), edges = [];
  for (let i = 0; i <= 8; i++) edges.push(toBin(LO * Math.pow(HI / LO, i / 8)));
  const buckets = [];
  for (let i = 0; i < 8; i++) buckets.push([edges[i], Math.max(edges[i] + 1, edges[i + 1])]);
  return { binCount, bass: [toBin(20), toBin(250)], mid: [toBin(250), toBin(4000)],
           treble: [toBin(4000), toBin(16000)], buckets };
}
const DB_MIN = -100, DB_MAX = -30;
const dbN = db => isFinite(db) ? Math.min(1, Math.max(0, (db - DB_MIN) / (DB_MAX - DB_MIN))) : 0;
function bandLvl(d, [a, b]) { let s = 0, n = 0; for (let i = a; i < b; i++) { s += dbN(d[i]); n++; } return n ? s/n : 0; }
const tbuf = new Float32Array(FFT);
function rms(an) { an.getFloatTimeDomainData(tbuf); let s = 0; for (let i = 0; i < tbuf.length; i++) s += tbuf[i]*tbuf[i]; return Math.sqrt(s/tbuf.length); }
let prevSpec = null, fluxAvg = 0, fluxVar = 1e-6, lastKick = 0, beatPeriod = 0.5, lastBeat = 0;
function detect(mono, now) {
  let kick = false;
  if (prevSpec) {
    let flux = 0; for (let i = 0; i < mono.length; i++) { const dd = mono[i]-prevSpec[i]; if (dd>0) flux += dd; }
    const a = 0.05, diff = flux - fluxAvg; fluxAvg += a*diff; fluxVar = (1-a)*(fluxVar + a*diff*diff);
    if (flux > fluxAvg + 1.5*Math.sqrt(fluxVar) && (now-lastKick) > 0.12) {
      kick = true; const ioi = now - lastKick; if (ioi>0.25 && ioi<1.0) beatPeriod += 0.2*(ioi-beatPeriod);
      lastKick = now; lastBeat = now;
    }
  } else prevSpec = new Float32Array(mono.length);
  prevSpec.set(mono);
  let beat = ((now - lastBeat) / beatPeriod) % 1; if (beat < 0) beat += 1;
  return { kick, beat };
}
const ZERO = { level:0,bass:0,mid:0,treble:0,bass_l:0,bass_r:0,buckets_l:new Float32Array(8),buckets_r:new Float32Array(8),beat:0,kick:false };
function analyse() {
  if (!actx || actx.state !== 'running') return ZERO;
  analyserL.getFloatFrequencyData(dataL); analyserR.getFloatFrequencyData(dataR);
  const bl = bandLvl(dataL, band.bass), br = bandLvl(dataR, band.bass);
  const buckets_l = new Float32Array(8), buckets_r = new Float32Array(8);
  for (let i = 0; i < 8; i++) { buckets_l[i] = bandLvl(dataL, band.buckets[i]); buckets_r[i] = bandLvl(dataR, band.buckets[i]); }
  const mono = new Float32Array(band.binCount);
  for (let i = 0; i < band.binCount; i++) mono[i] = (dbN(dataL[i]) + dbN(dataR[i])) * 0.5;
  const { kick, beat } = detect(mono, actx.currentTime);
  return {
    level: (rms(analyserL)+rms(analyserR))*0.5, bass: (bl+br)*0.5,
    mid: (bandLvl(dataL,band.mid)+bandLvl(dataR,band.mid))*0.5,
    treble: (bandLvl(dataL,band.treble)+bandLvl(dataR,band.treble))*0.5,
    bass_l: bl, bass_r: br, buckets_l, buckets_r, beat, kick,
  };
}
function playBuffer(buf) {
  if (current) { try { current.stop(); } catch(_){} try { current.disconnect(); } catch(_){} }
  const src = new AudioBufferSourceNode(actx, { buffer: buf, loop: true });
  src.connect(actx.destination); src.connect(splitter); src.start(0); current = src;
}
async function unlock() { ensureAudio(); if (actx.state === 'suspended') await actx.resume(); return actx.state; }
async function playURL(url) { ensureAudio(); await unlock(); const r = await fetch(url); playBuffer(await actx.decodeAudioData(await r.arrayBuffer())); }
async function playFile(file) { ensureAudio(); await unlock(); playBuffer(await actx.decodeAudioData(await file.arrayBuffer())); }

// ---------------------------------------------------------------- Pyodide bridge
let pyodide, BRIDGE, outProxy, featProxy, feat = new Float32Array(25);
const toObj = p => { const o = p.toJs({ dict_converter: Object.fromEntries }); p.destroy(); return o; };

async function bootPython() {
  setProg('loading Pyodide (CPython + numpy, WASM)…');
  const { loadPyodide } = await import(PYODIDE + 'pyodide.mjs');
  pyodide = await loadPyodide({ indexURL: PYODIDE });
  setProg('loading numpy + scipy…');
  await pyodide.loadPackage(['numpy', 'scipy']);
  setProg('fetching the live cube_dance engine…');
  const zip = await (await fetch('/cube_dance.zip')).arrayBuffer();
  await pyodide.unpackArchive(zip, 'zip');           // -> /home/pyodide/cube_dance (on sys.path)
  setProg('starting the engine…');
  const src = await (await fetch('/web/bridge.py')).text();
  pyodide.FS.writeFile('bridge.py', src);
  const mod = pyodide.pyimport('bridge');
  BRIDGE = mod.BRIDGE;
  outProxy = BRIDGE.out;     // persistent ndarray proxies (kept for app life)
  featProxy = BRIDGE.feat;
  window.__py = pyodide; window.__bridge = BRIDGE;   // debug handles
  // geometry
  const pp = BRIDGE.positions(); const pb = pp.getBuffer('f32');
  buildCloud(new Float32Array(pb.data)); pb.release(); pp.destroy();
}

// ---------------------------------------------------------------- controller UI
function buildControls(schema) {
  $('#curname').textContent = schema.name;
  $('#curtag').textContent = schema.ok ? `${N.toLocaleString()} px` : 'error';
  const err = $('#err');
  if (!schema.ok) { err.style.display = 'block'; err.textContent = schema.error || 'failed'; return; }
  err.style.display = 'none';
  // knobs
  const kw = $('#knobs'); kw.innerHTML = '';
  (schema.knobs || []).forEach((k, i) => {
    const d = document.createElement('div'); d.className = 'knob';
    d.innerHTML = `<div class="k"><span>${k.label}</span><span data-v>${k.value.toFixed(2)}</span></div>
      <input type="range" min="0" max="1" step="0.01" value="${k.value}">`;
    const inp = d.querySelector('input'), vv = d.querySelector('[data-v]');
    inp.addEventListener('input', () => { vv.textContent = (+inp.value).toFixed(2); BRIDGE.set_knob(i, +inp.value); });
    kw.appendChild(d);
  });
  // pads
  const pw = $('#pads'); pw.innerHTML = '';
  (schema.triggers || []).forEach(t => {
    const b = document.createElement('button'); b.className = 'pad' + (t.hold ? ' hold' : '');
    b.textContent = t.label;
    const [r,g,bl] = t.color; b.style.background = `rgb(${r},${g},${bl})`;
    b.addEventListener('pointerdown', () => BRIDGE.fire(t.label));
    pw.appendChild(b);
  });
}
function loadPreset(name) { buildControls(toObj(BRIDGE.load(name))); }

function fillPresetSelect() {
  const list = toObj(BRIDGE.preset_list());
  const sel = $('#preset'); sel.innerHTML = '';
  list.forEach(n => { const o = document.createElement('option'); o.value = o.textContent = n; sel.appendChild(o); });
  sel.value = 'deep';
  sel.addEventListener('change', () => loadPreset(sel.value));
  return list;
}

// ---------------------------------------------------------------- drag & drop
function installDnD() {
  const body = document.body, stop = e => { e.preventDefault(); e.stopPropagation(); };
  ['dragenter','dragover'].forEach(ev => body.addEventListener(ev, e => { stop(e); e.dataTransfer.dropEffect='copy'; body.classList.add('drag'); }));
  ['dragleave','drop'].forEach(ev => body.addEventListener(ev, e => { stop(e); body.classList.remove('drag'); }));
  body.addEventListener('drop', async e => {
    stop(e); const f = e.dataTransfer.files && e.dataTransfer.files[0]; if (!f) return;
    if (/\.py$/i.test(f.name)) {
      const src = await f.text();
      const sc = toObj(BRIDGE.load_code(src, f.name.replace(/\.py$/,'')));
      buildControls(sc);
      if (sc.ok) $('#preset').value = '';   // a dropped effect isn't in the list
    } else if (/^audio\//.test(f.type) || /\.(mp3|wav|flac|ogg|m4a|aac|aiff)$/i.test(f.name)) {
      await playFile(f); $('#hud').dataset.track = f.name;
    }
  });
}

// ---------------------------------------------------------------- frame loop
let t0 = performance.now(), frames = 0, fps = 0, lastFps = t0;
function frame() {
  const now = performance.now(), t = (now - t0) / 1000;
  // 1. audio features -> Python's feature buffer (zero-copy view)
  const m = analyse();
  feat[0]=m.level; feat[1]=m.bass; feat[2]=m.mid; feat[3]=m.treble; feat[4]=m.bass_l; feat[5]=m.bass_r;
  feat[6]=m.beat; feat[7]=m.kick?1:0; feat[8]=m.kick?Math.min(1,m.bass*1.5+0.4):0;
  feat.set(m.buckets_l, 9); feat.set(m.buckets_r, 17);
  let stepMs = 0;
  if (BRIDGE) {
    const t1 = performance.now();
    const fb = featProxy.getBuffer('f32'); fb.data.set(feat); fb.release();
    BRIDGE.step(t);                                   // run the REAL engine
    const ob = outProxy.getBuffer('f32'); colorAttr.array.set(ob.data); ob.release();
    colorAttr.needsUpdate = true;
    stepMs = performance.now() - t1;
  }
  const t2 = performance.now();
  controls.update(); composer.render();
  const renderMs = performance.now() - t2;
  frames++; if (now - lastFps > 500) { fps = Math.round(frames * 1000 / (now - lastFps)); frames = 0; lastFps = now;
    window.__perf = { fps, stepMs: +stepMs.toFixed(1), renderMs: +renderMs.toFixed(1) };
    $('#hud').innerHTML = `<span class="fps">${fps} fps</span> · ${N.toLocaleString()} px<br><b>${$('#curname').textContent}</b>` +
      `<br><span style="color:#525c73">eng ${stepMs.toFixed(0)}ms · gfx ${renderMs.toFixed(0)}ms</span>` +
      (m.level>0?`<br>lvl ${m.level.toFixed(2)} · bass ${m.bass.toFixed(2)}`:''); }
  requestAnimationFrame(frame);
}

// ---------------------------------------------------------------- boot
(async function () {
  try {
    await bootPython();
    fillPresetSelect();
    loadPreset('deep');
    installDnD();
    $('#panel').classList.add('show');
    requestAnimationFrame(frame);                     // render even before audio (silent)
    setProg('ready.'); $('#startbtn').classList.add('ready');
    $('#startbtn').addEventListener('click', async () => {
      $('#gate').classList.add('gone');
      try { await playURL('/showcase/assets/smooth.mp3'); $('#hud').dataset.track = 'Smooth Operator'; }
      catch (e) { console.warn('audio load failed', e); }
    });
  } catch (e) {
    setProg('boot failed:\n' + (e && e.message ? e.message : e));
    console.error(e);
  }
})();
