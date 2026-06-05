# Cube Dance — 20 more effect ideas (famous-inspired + structure-aware)

Round 2. **Part A** is 10 ideas grounded in real, famous music visualisations (with the
reference, how it maps onto the truss cube, the audio hook, and a feasibility note for the
wireframe). **Part B** is 10 animations that key off the *physical F34 truss* — its beams,
corners, the diagonal lacing triangles, the chord rows, the rings.

> Wireframe reminder (from `effect-ideas.md`): the LEDs live on 12 edges + 8 corner clusters,
> faces are empty. Effects that key off *where the LEDs are* (waveform paths, edges, rings,
> corners, normals) read best; full-screen 2-D looks must be re-imagined onto the lines.

---

## Part A — inspired by famous visualisations

### A1. Oscilloscope / Lissajous — *the music draws the shape*
**Real:** Jerobeam Fenderson's *Oscilloscope Music* and Winamp **AVS SuperScope** — the stereo
waveform is plugged into an oscilloscope's X/Y so the **sound itself draws** Lissajous figures
and 3-D shapes. We already have the raw stereo window (`window_at`). **Cube:** treat
(left, right, mid) as a parametric (x, y, z) path and trace it through the cube by proximity
(like the snake/knot, but the curve *is* the live waveform) — pure sine → a clean loop, rich
audio → a writhing 3-D scribble. **Hook:** it's 100% the signal. **Feasible:** yes — reuses
the proximity-curve machinery; the most "honest" audio-visual of the lot.

### A2. Spectrogram waterfall
**Real:** the spectrogram in every DAW / the Monstercat "Spectrogram" mode — frequency on one
axis, **time scrolling** on the other. **Cube:** map the 8 bands across the four vertical
posts and scroll the history *downward* over time → bands rain down the posts (a falling
spectrogram). **Hook:** shows the whole spectrum's recent past at a glance. **Feasible:** good
on the posts/edges; keep a small rolling history buffer.

### A3. MilkDrop feedback warp
**Real:** Ryan Geiss's **MilkDrop** (Winamp) — beat-detected, iterated-image **feedback** with
per-pixel zoom/rotate/warp so frames melt into each other. **Cube:** keep a decaying copy of
last frame's LED buffer, re-inject it warped (rotate about the vertical axis + radial
zoom) each frame, beat = a zoom/rotate kick → the signature trippy melting echo. **Hook:**
beat-driven motion + long ghost trails. **Feasible:** medium — needs a per-LED "previous
buffer" remapped by nearest-neighbour each frame (precompute the warp index map).

### A4. Monstercat radial spectrum
**Real:** the **Monstercat** circular EQ — spectrum bars fanned around a ring with a waveform
overlaid. **Cube:** lay the spectrum **around the top + bottom rings** (angle = frequency, the
beam segment lights proportional to that band) and run a waveform around the mid-height. **Hook:**
clean, recognisable "this is the music's spectrum." **Feasible:** strong — the rings are real
continuous LED runs.

### A5. Magnetosphere particle bloom
**Real:** Robert Hodgin's **Magnetosphere** (the iTunes 8 visualiser) — a charged-particle
physics system where **each particle is assigned an FFT bin** that drives its charge/forces, so
the swarm blooms and recoils with the music. **Cube:** a force-based particle system (attract/
repel), each particle bound to a band; kicks inject energy → blooms. LEDs lit by proximity.
**Hook:** organic, never-repeating, deeply audio-bound. **Feasible:** yes — like `flock` but
charge-driven; keep ≤~50 particles.

### A6. Cymatics / Chladni nodal patterns
**Real:** **Ernst Chladni**'s plates — a driven frequency forms **standing waves**; sand
collects on the **nodal lines** (no motion), higher pitch → finer pattern. **Cube:** drive a
standing wave along the edges with wave-number set by the **dominant frequency**; LEDs dark at
nodes, bright at antinodes → the cube literally shows the *shape of the pitch*, refining as the
sound goes higher. **Hook:** real physics, distinctly "scientific." **Feasible:** cheap and
distinct (a cosine of arc-position × frequency).

### A7. Demoscene tunnel
**Real:** the classic real-time **tunnel** (Second Reality and countless demos) — flying down a
textured tube. **Cube:** depth-banded rings rushing outward from the centre axis + an angular
texture scroll → a hyperspace rush. **Hook:** speed/heading from energy. **Feasible:** medium
— abstract on a wireframe (reads as expanding rings, close to `ripple`/`sphere`); include only
if it feels distinct in motion.

### A8. Larson scanner (KITT / Cylon)
**Real:** the **Larson scanner** — the back-and-forth eye of *Knight Rider*'s KITT and the
*Battlestar* Cylons, a bright point sweeping with a **fading tail**. **Cube:** a bright plane
sweeps an axis back and forth (or around the rings) with a dim trailing tail. **Hook:** tempo-
locked sweep; snare flips direction. **Feasible:** trivial and iconic — reads instantly.

### A9. Festival strobe / blinder banks
**Real:** the white **audience-blinder strobe** banks every big EDM drop leans on (Daft Punk,
deadmau5, every festival main stage). **Cube:** beat-synced full-cube white strobe + a base-ring
"blinder," `QUANT`-tight, with a build-then-blackout on the drop. **Hook:** pure
drop-energy performance tool. **Feasible:** trivial; pairs with the existing hold-strobe pads.

### A10. Panel sequencer (Daft Punk pyramid / deadmau5 Cube)
**Real:** **Daft Punk's pyramid** and **deadmau5's Cube** — segmented LED panels running pixel
patterns (chevrons, sweeps, glyphs) across the segments. **Cube:** treat the beams as a coarse
pixel grid and run **sequenced panel patterns** — chevrons climbing the faces, sweeps crossing,
simple marquee glyphs. **Hook:** choreographed, "produced-show" feel. **Feasible:** good on the
beams; author patterns as keyframed segment masks.

---

## Part B — structure-aware animations (the physical truss)

### B1. Per-beam spectrum bars
The 12 beams become a 3-D graphic EQ: each beam owns a frequency band and **fills from its
corner** proportional to that band's energy. A spectrum analyser wrapped onto the actual truss.

### B2. Triangle-lacing wave
The F34 truss's **diagonal lacing forms triangles**. Light them in a **wave that sweeps across
each face**, triangle by triangle — the brace pattern itself becomes the animation (uses
`geometry.corner_x_faces` + the beam-face triangles).

### B3. Corner-to-corner nerve impulse
A pulse **propagates across the edge graph by graph-distance**, from one corner to the
diagonally-opposite one (BFS over the 8 corners / 12 edges) — a signal firing through the frame,
branching at each junction.

### B4. Face-perimeter spin
Light each of the **6 faces' four-edge perimeter** in turn so a lit square face appears to
rotate around the cube; the shared edges hand off between adjacent faces.

### B5. Beam barber-pole (chord rows)
Each beam carries **multiple parallel LED chord rows**. Phase-offset the rows so every beam
reads as a **rotating barber-pole / DNA twist** running along its length — motion *along* and
*around* each beam at once.

### B6. Wireframe self-build
The cube **draws itself edge-by-edge** (a CAD model assembling — edges extrude from their
corners in sequence), holds, then **dissolves** the same way. A perfect intro/outro / track
transition.

### B7. Ring counter-rotation
The **top and bottom horizontal rings** chase in **opposite directions**, and the four vertical
posts bridge the phase between them → a peristaltic twist of the whole cage. Speed = tempo.

### B8. Gravity drip down the posts
Light **drips down the four vertical posts** like liquid under gravity (accelerating), then
**pools and ripples at the base ring** — a structural rain that respects which edges are
vertical vs. horizontal.

### B9. Diagonal plane sweep (X-brace aligned)
Sweep a plane along the cube's **face-diagonal directions** — the same orientation as the truss
lacing — lighting edges and brace triangles as the plane crosses them, so the sweep "rhymes"
with the physical X-braces.

### B10. Truss modal resonance
Simulate the cube's **structural vibration modes** (bending / twisting eigenmodes): the bass
"strikes" the frame and edges brighten (and could visually displace) along a **mode shape**, so
the truss appears to physically **ring** with the kick — the structure as an instrument.

---

## Sources

- [MilkDrop — Wikipedia](https://en.wikipedia.org/wiki/MilkDrop) · [Music visualization — Wikipedia](https://en.wikipedia.org/wiki/Music_visualization) (Geiss, G-Force, AVS SuperScope)
- [Oscilloscope Music / Jerobeam Fenderson & Hansi Raber — CreativeApplications](https://www.creativeapplications.net/project/oscilloscope-music-jerobeam-fenderson-and-hansi-raber/) · [IEEE Spectrum](https://spectrum.ieee.org/jerobeam-fendersons-trippy-oscilloscope-music)
- [Magnetosphere — Robert Hodgin](https://roberthodgin.com/project/magnetosphere) · [CDM: Magnetosphere in iTunes 8](https://cdm.link/flight404s-magnetosphere-the-new-visualizer-in-itunes-8/)
- [Cymatics — Wikipedia](https://en.wikipedia.org/wiki/Cymatics) (Chladni plates, nodal lines, standing waves)
- [deadmau5 Cube — Your EDM](https://www.youredm.com/2016/02/11/better-cube-cage-opinion/) · [Amon Tobin ISAM — Billboard](https://www.billboard.com/articles/photos/live/465928/amon-tobin-pushes-envelope-with-shape-shifting-dj-experience)
- [Monstercat-style visualizer (Rainmeter) — GitHub](https://github.com/marcopixel/monstercat-visualizer) · [Larson scanner — Hackaday](https://hackaday.com/tag/larson-scanner/)
