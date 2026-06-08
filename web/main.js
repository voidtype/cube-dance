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
const WAVE_M = 96;                               // scope samples per channel (-> feat[25..])
const _wL = new Float32Array(WAVE_M), _wR = new Float32Array(WAVE_M);
// downsample an analyser's time-domain signal into dst (the oscilloscope feed)
function waveOf(an, dst) { an.getFloatTimeDomainData(tbuf); const step = tbuf.length / WAVE_M;
  for (let i = 0; i < WAVE_M; i++) dst[i] = tbuf[(i * step) | 0]; }
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
const ZERO = { level:0,bass:0,mid:0,treble:0,bass_l:0,bass_r:0,buckets_l:new Float32Array(8),buckets_r:new Float32Array(8),beat:0,kick:false,waveL:new Float32Array(WAVE_M),waveR:new Float32Array(WAVE_M) };
function analyse() {
  if (!actx || actx.state !== 'running') return ZERO;
  analyserL.getFloatFrequencyData(dataL); analyserR.getFloatFrequencyData(dataR);
  const bl = bandLvl(dataL, band.bass), br = bandLvl(dataR, band.bass);
  const buckets_l = new Float32Array(8), buckets_r = new Float32Array(8);
  for (let i = 0; i < 8; i++) { buckets_l[i] = bandLvl(dataL, band.buckets[i]); buckets_r[i] = bandLvl(dataR, band.buckets[i]); }
  const mono = new Float32Array(band.binCount);
  for (let i = 0; i < band.binCount; i++) mono[i] = (dbN(dataL[i]) + dbN(dataR[i])) * 0.5;
  const { kick, beat } = detect(mono, actx.currentTime);
  waveOf(analyserL, _wL); waveOf(analyserR, _wR);   // the real stereo waveform -> scope
  return {
    level: (rms(analyserL)+rms(analyserR))*0.5, bass: (bl+br)*0.5,
    mid: (bandLvl(dataL,band.mid)+bandLvl(dataR,band.mid))*0.5,
    treble: (bandLvl(dataL,band.treble)+bandLvl(dataR,band.treble))*0.5,
    bass_l: bl, bass_r: br, buckets_l, buckets_r, beat, kick, waveL: _wL, waveR: _wR,
  };
}
function playBuffer(buf) {
  if (current) { try { current.stop(); } catch(_){} try { current.disconnect(); } catch(_){} }
  const src = new AudioBufferSourceNode(actx, { buffer: buf, loop: true });
  src.connect(actx.destination); src.connect(splitter); src.start(0); current = src;
  audioPlaying = true;
}
async function unlock() { ensureAudio(); if (actx.state === 'suspended') await actx.resume(); return actx.state; }
async function playURL(url) { ensureAudio(); await unlock(); const r = await fetch(url); playBuffer(await actx.decodeAudioData(await r.arrayBuffer())); }
async function playFile(file) { ensureAudio(); await unlock(); playBuffer(await actx.decodeAudioData(await file.arrayBuffer())); }

// ---------------------------------------------------------------- Pyodide bridge
let pyodide, BRIDGE, outProxy, featProxy, feat = new Float32Array(25 + 2 * WAVE_M), audioPlaying = false;

// A gentle synthetic beat so the cube is ALWAYS alive — on load, and any time no
// real audio is playing. Real audio takes over the moment a track starts.
function synthFeatures(t) {
  const b = (t * 1.9) % 1;                       // ~114 bpm
  const env = Math.exp(-b / 0.16) + 0.25;        // kick pulse + a floor (never dark)
  const sweep = 0.5 + 0.5 * Math.sin(t * 0.25);
  const bl = new Float32Array(8), br = new Float32Array(8);
  for (let i = 0; i < 8; i++) {
    const v = Math.min(1, 0.3 + 0.55 * Math.abs(Math.sin(t * 0.8 + i * 0.7)) * env);
    bl[i] = v; br[i] = v * 0.92;
  }
  const bass = Math.min(1, 0.4 + 0.5 * env);
  for (let i = 0; i < WAVE_M; i++) {             // a synthetic wave so the scope lives pre-audio
    const ph = (i / WAVE_M) * Math.PI * 6 + t * 6;
    _wL[i] = Math.sin(ph) * (0.25 + 0.5 * env);
    _wR[i] = Math.sin(ph + 0.6) * (0.25 + 0.5 * env) * 0.9;
  }
  return { level: Math.min(1, 0.35 + 0.4 * env), bass, mid: 0.3 + 0.35 * sweep,
    treble: 0.25 + 0.3 * (1 - sweep), bass_l: bass, bass_r: bass * 0.9,
    buckets_l: bl, buckets_r: br, beat: b, kick: b < 0.04, waveL: _wL, waveR: _wR };
}
const toObj = p => { const o = p.toJs({ dict_converter: Object.fromEntries }); p.destroy(); return o; };

async function bootPython() {
  setProg('loading Pyodide (CPython + numpy, WASM)…');
  const { loadPyodide } = await import(PYODIDE + 'pyodide.mjs');
  pyodide = await loadPyodide({ indexURL: PYODIDE });
  setProg('loading numpy + scipy…');
  await pyodide.loadPackage(['numpy', 'scipy']);
  setProg('fetching the live cube_dance engine…');
  const zip = await (await fetch('./cube_dance.zip')).arrayBuffer();
  await pyodide.unpackArchive(zip, 'zip');           // -> /home/pyodide/cube_dance (on sys.path)
  setProg('starting the engine…');
  const src = await (await fetch('./bridge.py')).text();
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
  curSchema = schema;
  if (f1ui) updateF1(schema);
}
// effect state + the saved-effects ("your effects") library
let cur = { name: '', source: '', isUser: false };
let BUILTIN = [];
const userFx = {};
function opt(v) { const o = document.createElement('option'); o.value = o.textContent = v; return o; }
function uniqueName(base) {
  base = (base || 'effect').replace(/\s*\(edit\)$/, '').trim() || 'effect';
  const taken = n => BUILTIN.includes(n) || (n in userFx);
  if (!taken(base)) return base;
  let i = 2; while (taken(base + ' ' + i)) i++; return base + ' ' + i;
}
function refreshList() {
  const sel = $('#preset'), val = sel.value; sel.innerHTML = '';
  BUILTIN.forEach(n => sel.appendChild(opt(n)));
  const names = Object.keys(userFx);
  if (names.length) {
    const g = document.createElement('optgroup'); g.label = '— your effects —';
    names.forEach(n => g.appendChild(opt(n))); sel.appendChild(g);
  }
  if ([...sel.options].some(o => o.value === val)) sel.value = val;
}
function persist() { try { localStorage.setItem('cubeUserFx', JSON.stringify(userFx)); } catch (_) {} }
function addUserFx(name, src) { userFx[name] = src; refreshList(); persist(); }

function loadPreset(name) {
  buildControls(toObj(BRIDGE.load(name)));
  cur = { name, source: BRIDGE.preset_source(name) || '', isUser: false };
  $('#preset').value = name;
}
function loadUser(name) {
  const src = userFx[name]; if (src == null) return;
  buildControls(toObj(BRIDGE.load_code(src, name)));
  cur = { name, source: src, isUser: true };
  $('#preset').value = name;
}
function fillPresetSelect() {
  BUILTIN = toObj(BRIDGE.preset_list());
  try { Object.assign(userFx, JSON.parse(localStorage.getItem('cubeUserFx') || '{}')); } catch (_) {}
  refreshList();
  $('#preset').addEventListener('change', e => { const n = e.target.value; (n in userFx) ? loadUser(n) : loadPreset(n); });
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
      const name = uniqueName(f.name.replace(/\.py$/i, ''));
      const sc = toObj(BRIDGE.load_code(src, name));
      buildControls(sc);
      if (sc.ok) { addUserFx(name, src); cur = { name, source: src, isUser: true }; $('#preset').value = name; }
    } else if (/^audio\//.test(f.type) || /\.(mp3|wav|flac|ogg|m4a|aac|aiff)$/i.test(f.name)) {
      await playFile(f); $('#hud').dataset.track = f.name;
    }
  });
}

// ---------------------------------------------------------------- toolbar + python editor
function download(filename, text) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/x-python' }));
  const a = document.createElement('a'); a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 100);
}
function edErr(sc) {
  const e = $('#ed-err'); if (sc.ok) { e.classList.remove('show'); return true; }
  e.textContent = sc.error || 'failed'; e.classList.add('show'); return false;
}
function openEditor() {
  $('#ed-base').textContent = cur.name || '—';
  $('#ed-code').value = cur.source || '# no source available\n';
  $('#ed-name').value = uniqueName(cur.name || 'effect');
  $('#ed-err').classList.remove('show');
  $('#editor').classList.add('show'); $('#ed-code').focus();
}
function installToolbar() {
  $('#btn-controls').addEventListener('click', () => {
    const p = $('#panel'), b = $('#btn-controls'), show = !p.classList.contains('show');
    p.classList.toggle('show', show); b.classList.toggle('active', show);
  });
  $('#btn-f1').addEventListener('click', () => {
    const f = $('#f1'), b = $('#btn-f1'), show = !f.classList.contains('show');
    f.classList.toggle('show', show); b.classList.toggle('active', show);
  });
  $('#btn-edit').addEventListener('click', openEditor);
  $('#ed-close').addEventListener('click', () => $('#editor').classList.remove('show'));
  $('#editor').addEventListener('click', e => { if (e.target.id === 'editor') $('#editor').classList.remove('show'); });
  $('#ed-run').addEventListener('click', () => {                       // preview the edit, no save
    const src = $('#ed-code').value, sc = toObj(BRIDGE.load_code(src, (cur.name || 'effect') + ' (edit)'));
    if (edErr(sc)) { buildControls(sc); cur = { name: cur.name, source: src, isUser: true }; }
  });
  $('#ed-save').addEventListener('click', () => {                      // save -> a new item in the list
    const src = $('#ed-code').value, name = uniqueName(($('#ed-name').value || '').trim() || cur.name || 'effect');
    const sc = toObj(BRIDGE.load_code(src, name));
    if (edErr(sc)) {
      addUserFx(name, src); buildControls(sc); cur = { name, source: src, isUser: true };
      $('#preset').value = name; $('#editor').classList.remove('show');
    }
  });
  $('#ed-download').addEventListener('click', () => {                  // download .py to send back
    const n = (($('#ed-name').value || cur.name || 'effect').trim().replace(/[^\w.-]+/g, '_')) || 'effect';
    download(n.endsWith('.py') ? n : n + '.py', $('#ed-code').value);
  });
  $('#ed-code').addEventListener('keydown', e => {                     // tab = 2 spaces; cmd/ctrl+enter = Run
    if (e.key === 'Tab') {
      e.preventDefault(); const t = e.target, s = t.selectionStart;
      t.value = t.value.slice(0, s) + '  ' + t.value.slice(t.selectionEnd); t.selectionStart = t.selectionEnd = s + 2;
    } else if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); $('#ed-run').click(); }
  });
}

// ---------------------------------------------------------------- simulated Traktor F1
const F1L = {
  W: 360, H: 880, knobsX: [54, 142, 230, 318], knobY: 118, knobR: 34,
  faderTop: 180, faderBot: 344, faderHW: 12,
  buttons: { SYNC:[14,372,98,408], QUANT:[104,372,188,408], CAPTURE:[194,372,278,408],
    SHIFT:[10,420,70,456], REVERSE:[76,420,138,456], TYPE:[144,420,206,456], SIZE:[212,420,274,456], BROWSE:[280,420,346,456] },
  display:[282,364,324,406], encX:343, encY:385, encR:14, pads:[16,474,344,812], stop:[16,822,344,858],
  palette:[[210,40,40],[220,110,30],[220,150,30],[210,200,40],[150,200,40],[60,180,60],[40,180,110],[40,190,180],
    [40,150,210],[50,90,210],[90,60,210],[140,50,200],[180,40,180],[210,40,140],[210,40,90],[210,60,60]],
  btnColor:{SYNC:[240,120,20],QUANT:[240,120,20],CAPTURE:[240,120,20],SHIFT:[220,220,225],REVERSE:[240,120,20],TYPE:[240,120,20],SIZE:[240,120,20],BROWSE:[40,90,230]},
};
let F1S = 0.55, f1ui = null, curSchema = null;
const f1knob = [0, 0, 0, 0], f1fader = [0.46, 0.48, 0.36, 0.22];
const FADERMAP = [ v => pointMat.uniforms.uBright.value = 0.6 + 2.6 * v, v => bloom.strength = 2.0 * v,
  v => pointMat.uniforms.uSize.value = 40 + 150 * v, v => controls.autoRotateSpeed = 2.6 * v ];
const FADERLAB = ['bright', 'bloom', 'size', 'spin'];
const fpx = v => v + 'px';   // natural panel coords; the whole #f1 is CSS-scaled by F1S

function setKnob(i, v) { f1knob[i] = v; if (f1ui) f1ui.inds[i].style.transform = `rotate(${-135 + 270 * v}deg)`; }
function setFader(i, v) { f1fader[i] = v; const f = f1ui.faders[i];
  f.th.style.top = ((1 - v) * (F1L.faderBot - F1L.faderTop) - 7) + 'px'; FADERMAP[i](v); }
function allEffects() { return [...BUILTIN, ...Object.keys(userFx)]; }
function cycleEffect(d) { const a = allEffects(); let i = a.indexOf(cur.name); i = (i + d + a.length) % a.length;
  (a[i] in userFx) ? loadUser(a[i]) : loadPreset(a[i]); }

function buildF1() {
  F1S = Math.max(0.45, Math.min(0.9, Math.min((innerHeight - 30) / F1L.H, (innerWidth * 0.27) / F1L.W)));
  const f1 = $('#f1'); f1.style.width = F1L.W + 'px'; f1.style.height = F1L.H + 'px';
  f1.style.transform = 'scale(' + F1S + ')'; f1.style.top = ((innerHeight - F1L.H * F1S) / 2) + 'px';
  f1.innerHTML = '';
  const node = (cls, x, y, w, h) => { const d = document.createElement('div'); d.className = cls;
    d.style.left = fpx(x); d.style.top = fpx(y); if (w != null) { d.style.width = fpx(w); d.style.height = fpx(h); } f1.appendChild(d); return d; };
  const lab = (text, x, y, w) => { const d = node('lab', x, y); d.style.width = fpx(w); d.textContent = text; return d; };
  f1ui = { inds: [], klab: [], faders: [], pads: [], btn: {}, btnOn: {}, trigs: [] };

  F1L.knobsX.forEach((cx, i) => {
    const k = node('f1-knob', cx - F1L.knobR, F1L.knobY - F1L.knobR, F1L.knobR * 2, F1L.knobR * 2);
    const ind = document.createElement('div'); ind.className = 'ind'; k.appendChild(ind); f1ui.inds.push(ind);
    f1ui.klab.push(lab('', cx - 40, F1L.knobY + F1L.knobR + 6, 80));
    k.addEventListener('pointerdown', e => { e.preventDefault(); const sy = e.clientY, s0 = f1knob[i];
      const mv = ev => { const v = Math.max(0, Math.min(1, s0 + (sy - ev.clientY) / 150)); setKnob(i, v); BRIDGE.set_knob(i, v); };
      const up = () => { removeEventListener('pointermove', mv); removeEventListener('pointerup', up); };
      addEventListener('pointermove', mv); addEventListener('pointerup', up); });
  });
  F1L.knobsX.forEach((cx, i) => {
    const tk = node('f1-fader', cx - F1L.faderHW, F1L.faderTop, F1L.faderHW * 2, F1L.faderBot - F1L.faderTop);
    const th = document.createElement('div'); th.className = 'f1-fthumb'; tk.appendChild(th);
    f1ui.faders.push({ tk, th }); lab(FADERLAB[i], cx - 30, F1L.faderBot + 6, 60);
    tk.addEventListener('pointerdown', e => { e.preventDefault(); const r = tk.getBoundingClientRect();
      const set = ev => setFader(i, Math.max(0, Math.min(1, 1 - (ev.clientY - r.top) / r.height)));
      set(e); const up = () => { removeEventListener('pointermove', set); removeEventListener('pointerup', up); };
      addEventListener('pointermove', set); addEventListener('pointerup', up); });
    setFader(i, f1fader[i]);
  });
  f1ui.disp = node('f1-disp', F1L.display[0], F1L.display[1], F1L.display[2] - F1L.display[0], F1L.display[3] - F1L.display[1]);
  const enc = node('f1-enc', F1L.encX - F1L.encR, F1L.encY - F1L.encR, F1L.encR * 2, F1L.encR * 2);
  enc.addEventListener('wheel', e => { e.preventDefault(); cycleEffect(e.deltaY > 0 ? 1 : -1); }, { passive: false });
  enc.addEventListener('pointerdown', e => { e.preventDefault(); let last = e.clientY;
    const mv = ev => { if (Math.abs(ev.clientY - last) > 16) { cycleEffect(ev.clientY > last ? 1 : -1); last = ev.clientY; } };
    const up = () => { removeEventListener('pointermove', mv); removeEventListener('pointerup', up); };
    addEventListener('pointermove', mv); addEventListener('pointerup', up); });
  for (const [name, [x0, y0, x1, y1]] of Object.entries(F1L.buttons)) {
    const b = node('f1-btn', x0, y0, x1 - x0, y1 - y0); b.textContent = name; f1ui.btn[name] = b; f1ui.btnOn[name] = false;
    b.addEventListener('pointerdown', () => {
      if (name === 'BROWSE') { toObj(BRIDGE.reset_knobs()).forEach((v, i) => setKnob(i, v)); return; }
      const on = !f1ui.btnOn[name]; f1ui.btnOn[name] = on; const col = F1L.btnColor[name];
      b.style.background = on ? `rgb(${col[0]},${col[1]},${col[2]})` : '#23262d'; b.style.color = on ? '#05060a' : '#9aa0ac';
      if (name === 'CAPTURE') BRIDGE.set_flag('mono', on);
      else if (name === 'REVERSE') BRIDGE.set_flag('reverse', on);
      else if (name === 'SIZE') BRIDGE.set_flag('size_boost', on);
      else if (name === 'QUANT') BRIDGE.set_flag('freeze', on);
    });
  }
  const [px0, py0, px1, py1] = F1L.pads, g = 8, pw = ((px1 - px0) - 3 * g) / 4, ph = ((py1 - py0) - 3 * g) / 4;
  for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) {
    const el = node('f1-pad', px0 + c * (pw + g), py0 + r * (ph + g), pw, ph);
    f1ui.pads.push(el);
    el.addEventListener('pointerdown', () => { const t = f1ui.trigs; if (t.length) BRIDGE.fire(t[c % t.length].label);
      el.classList.add('hit'); setTimeout(() => el.classList.remove('hit'), 130); });
  }
  const [sx0, sy0, sx1, sy1] = F1L.stop, sw = ((sx1 - sx0) - 3 * g) / 4;
  for (let c = 0; c < 4; c++) { const el = node('f1-stop', sx0 + c * (sw + g), sy0, sw, sy1 - sy0); el.addEventListener('pointerdown', () => BRIDGE.clear()); }
  if (curSchema) updateF1(curSchema);
}

function updateF1(schema) {
  if (!f1ui || !schema || !schema.ok) return;
  const ks = schema.knobs || [];
  for (let i = 0; i < 4; i++) { const k = ks[i];
    f1ui.inds[i].parentElement.style.opacity = k ? 1 : 0.3;
    f1ui.klab[i].textContent = k ? k.label : ''; setKnob(i, k ? k.value : 0); }
  f1ui.trigs = schema.triggers || [];
  f1ui.pads.forEach((el, idx) => { const c = idx % 4, r = (idx / 4) | 0;
    let col = F1L.palette[idx], txt = '';
    if (r === 3 && c < f1ui.trigs.length) { col = f1ui.trigs[c].color; txt = f1ui.trigs[c].label; }
    el.style.background = `rgb(${col[0]},${col[1]},${col[2]})`; el.textContent = txt; });
  const a = allEffects(), i = Math.max(0, a.indexOf(schema.name));
  f1ui.disp.textContent = String(i % 100).padStart(2, '0');
}

// ---------------------------------------------------------------- frame loop
let t0 = performance.now(), frames = 0, fps = 0, lastFps = t0;
function frame() {
  const now = performance.now(), t = (now - t0) / 1000;
  // 1. features -> Python's feature buffer (zero-copy view). Synthetic beat keeps
  //    the cube alive until a real track is playing.
  const m = audioPlaying ? analyse() : synthFeatures(t);
  feat[0]=m.level; feat[1]=m.bass; feat[2]=m.mid; feat[3]=m.treble; feat[4]=m.bass_l; feat[5]=m.bass_r;
  feat[6]=m.beat; feat[7]=m.kick?1:0; feat[8]=m.kick?Math.min(1,m.bass*1.5+0.4):0;
  feat.set(m.buckets_l, 9); feat.set(m.buckets_r, 17);
  feat.set(m.waveL, 25); feat.set(m.waveR, 25 + WAVE_M);   // stereo scope -> atlas oscilloscope
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
    loadPreset('atlas');                              // the reference plugin (maps sound -> pixels)
    installDnD();
    installToolbar();
    buildF1();
    $('#panel').classList.add('show');
    $('#f1').classList.add('show'); $('#btn-f1').classList.add('active');
    requestAnimationFrame(frame);                     // the cube is alive on load (synthetic beat)
    $('#gate').classList.add('gone');                 // reveal the living cube immediately
    const snd = $('#sound'); snd.classList.add('show');
    const AUDIO = ['./anchorite.mp3', '../assets/smooth.mp3'];   // default track, then a fallback already on the site
    snd.addEventListener('click', async () => {
      snd.textContent = '…';
      for (const u of AUDIO) {
        try { await playURL(u); snd.classList.add('on'); snd.textContent = '♪ Anchorite'; $('#hud').dataset.track = 'Anchorite'; return; }
        catch (e) { /* try the next candidate */ }
      }
      snd.textContent = '▶ sound (drag a track in)';
    });
  } catch (e) {
    setProg('boot failed:\n' + (e && e.message ? e.message : e));
    console.error(e);
  }
})();
