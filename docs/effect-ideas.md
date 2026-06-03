# Cube Dance — 20 new 3D effect ideas (+ self-critique)

A design brainstorm for new visual elements/presets that genuinely exploit the **3-D world**,
across simulation, fractal, geometric, structure-aware, and physical families. Each entry:
the concept, the **3-D angle**, how it **maps onto the cube** (positions / edges / corners /
normals / the truss triangles), **audio** reactivity, and **hold vs fire** suitability.

> **The governing constraint** (learned from the spiral/vortex): the cube is a **wireframe** —
> ~9.7k LEDs live only on the **12 edges + 8 corner clusters**, with **empty faces**. So any
> effect defined over a *volume* or *surface* is only **sampled on a sparse shell**. Effects
> that key off **where the LEDs actually are** (edges, corners, the truss triangles, normals)
> read far better than ones that assume a filled volume. This drives the critique at the end.

---

## A. Simulation / algorithmic

### 1. Game of Life 3D (volumetric CA)
A 3-D cellular automaton on a coarse voxel grid (e.g. 16³) with a Life-like rule (birth/survive
neighbour counts tuned for 3-D, e.g. 5766/B6/S567). Each LED samples its nearest voxel's
state. **3-D:** true volumetric evolution. **Cube map:** precompute LED→voxel index; lit where
the local cell is alive. **Audio:** kick injects a random live-cell "seed"; energy sets the
step rate (steps/sec). **Hold/fire:** *fire* = inject a glider/seed; could *hold* = freeze the
sim. Living, never-repeating texture.

### 2. Reaction–Diffusion (Gray–Scott)
Two chemicals diffuse and react on a small 3-D grid → organic spots / stripes / labyrinths that
slowly morph. LED brightness = chemical concentration. **3-D:** volumetric pattern formation.
**Audio:** feed/kill rates ride energy → morph between dots and coral. **Hold/fire:** *hold* to
"inject reagent" (bloom of activity under the finger). Gorgeous but the heaviest to compute.

### 3. Boids (flocking murmuration)
~40 boids fly in 3-D with cohesion/separation/alignment; each LED lights by proximity to the
nearest boid (same maths as the spiral, but to moving points). **3-D:** full free flight.
**Audio:** kick scatters the flock (startle), energy = speed, bass = cohesion. **Hold/fire:**
*hold* a pad = a moving "attractor" the flock chases toward that region. Alive and unpredictable.

### 4. Diffusion-Limited Aggregation (slow crystal)
A dendritic fractal grows from a seed: random-walking particles stick on contact, branching
outward. Grows over minutes — a set-long evolving sculpture. **3-D:** branching in space.
**Cube map:** light LEDs near the aggregate's points. **Audio:** growth rate from energy; a big
drop triggers a growth spurt. **Hold/fire:** *fire* = reset/re-seed. Best as a slow background.

---

## B. Fractal / noise

### 5. Fractal noise cloud (FBM)
Sample fractal Brownian motion (layered value/simplex noise) at each LED + time → a soft,
cloud-like field drifting through the cube. Threshold it for **stark** wisps or keep it smooth.
**3-D:** the noise is sampled in 3 dimensions, so it has real depth/parallax as you orbit.
**Audio:** octave gain + threshold ride the spectrum. **Hold/fire:** *hold* = "gust" (advect the
cloud fast). Distinct from `plasma` (sinusoids) — FBM is turbulent/cloudy.

### 6. Menger-sponge resonance (self-referential)
Light LEDs whose position lies in a **Menger sponge** (the recursive cube fractal) at a recursion
depth that pulses with the beat. A cube fractal **inside the cube** — thematically perfect.
**3-D:** genuine 3-D fractal membership (cheap digit test, no iteration). **Audio:** recursion
depth steps up on big hits; sub-cubes flicker per band. **Hold/fire:** *hold* = lock a depth.
Stark and geometric.

### 7. Mandelbulb shell
Escape-time of the **Mandelbulb** evaluated at LED positions mapped into the fractal's domain;
colour by iteration count, slowly rotate/zoom the camera into it. **3-D:** the canonical 3-D
fractal. **Cube map:** LEDs sample a thin shell of the bulb's surface. **Audio:** zoom speed =
energy, power parameter morphs on beat. **Hold/fire:** *fire* = "dive" (zoom burst). High wow,
high risk (see critique — sampling a shell may scatter).

---

## C. Geometric / implicit surfaces

### 8. Slicing plane (cross-section)
A flat plane sweeps and rotates through the cube; LEDs near it light → the **intersection
polygon** of plane-and-wireframe, morphing as the plane's normal turns. **3-D:** reveals the
cube's cross-section. **Audio:** sweep speed = energy; the normal jumps on snare. **Hold/fire:**
*hold* = park the plane and let it spin in place. Stark, clean, very legible on edges.

### 9. Breathing sphere shell
A sphere shell of radius r(t) centred in the cube; LEDs near the shell glow. **3-D:** radial.
**Audio:** radius pumps with the bass (the cube "inhales/exhales"); kicks snap it outward.
**Hold/fire:** *hold* = expand and hold at max (whole cube lit), release = collapse. The
continuous cousin of the `Shockwave` trigger.

### 10. Torus-knot thread
A parametric 3-D torus knot (p,q) threads through the cube; LEDs near the curve light (spiral-
style proximity). Morph p/q over time for shape-shifting. **3-D:** a knot only makes sense in 3-D.
**Audio:** knot complexity (q) steps with intensity; rotation = energy. **Hold/fire:** *fire* =
re-tie (jump to a new p,q). A more exotic relative of the helix.

### 11. Spinning platonic solid
A wireframe icosahedron (or tetra/octa) of light rotates inside the cube; LEDs light by proximity
to the **solid's edges**. **3-D:** a rotating polyhedron read in depth. **Audio:** spin = energy;
on kick it "tumbles" (axis flip); morph between solids on phrase changes. **Hold/fire:** *hold* =
freeze the rotation. Clean, hypnotic, distinctly geometric.

---

## D. Structure-aware (edges, corners, the truss triangles) — *the cube's home turf*

### 12. Edge-graph snake (Tron)
A light **travels along the actual cube edges**, turning at corners by following the edge
adjacency graph, leaving a fading trail — a light-cycle on the truss. **3-D + structure:** uses
the real edge topology. **Cube map:** precompute edge adjacency at the 8 corners; animate a head
by arc-length, pick the next edge at each junction (random / no-immediate-reverse). **Audio:**
speed = energy; spawn a second snake on the drop. **Hold/fire:** *hold* = freeze the trail.
Reads beautifully because it lives exactly where the LEDs are.

### 13. Triangle-lacing sequencer  ← *the "be aware of the triangles" idea*
The truss is made of **triangles** (diagonal lacing / corner X-panels). Light **individual
triangles** in patterns: chase them around a face, flash per frequency band, or "fill" a face
triangle-by-triangle. **3-D + structure:** keys off the real truss geometry
(`geometry.corner_x_faces`, beam chord triangles). **Audio:** each band owns a set of triangles;
kick lights a whole face's triangles. **Hold/fire:** *hold* = solidly light the touched face's
triangles. The most "of the object" effect — celebrates the physical build.

### 14. Corner-to-corner lightning
Lightning arcs that **path-find along edges** between two corners (graph shortest path), with
forks. **3-D + structure:** electricity crawling the frame. **Cube map:** edge-graph BFS between
random corner pairs; light the path + a few branch edges, hard and brief. **Audio:** strike on
kick; density with energy. **Hold/fire:** *fire* (it's a strike); *hold* = continuous arcing
storm. Distinct from the existing free `Lightning` (this one respects the structure).

### 15. Truss current / heat diffusion on the edge graph
Inject "energy" at a corner; it **diffuses across the edge graph** (each edge a resistor),
lighting edges by local charge, cooling over time. **3-D + structure:** the cube as a circuit/
heat network. **Audio:** kicks inject at random corners; bass = conductivity. **Hold/fire:**
*hold* a pad = hold a corner energized (current keeps spreading from it). Organic yet structural.

### 16. Face-normal sun (moving light)
A virtual light orbits the cube; every LED shades by **its normal · direction-to-light** — faces
toward the light glow, away go dark. **3-D:** real directional shading; the cube looks lit by a
moving sun. **Cube map:** uses the per-LED **normals already in the model** (no extra geometry!).
**Audio:** light orbits at energy speed; colour-temperature shifts with the spectrum; kick = a
flash from a new direction. **Hold/fire:** *hold* = park the sun. Cheap, and makes the form
read in 3-D better than almost anything.

---

## E. Physical / waves / organic

### 17. Ripple tank (interfering caustics)
Each kick drops a "stone": an expanding **sinusoidal ring** from that point; rings **interfere**
to make water-caustic patterns. **3-D:** spherical wavefronts in the volume. **Cube map:**
brightness = Σ over active ripples of sin(k·dist − ωt)·decay. **Audio:** kicks/snares spawn
ripples at mapped locations; bass = wavelength. **Hold/fire:** *hold* = a continuous emitter
(steady ripples from one point). Cheap (a handful of sources) and mesmerising.

### 18. Aurora curtains
Vertical **curtains** of light (northern-lights) that wave and shift hue, driven by 1-D noise
over angle/height; they drift around the cube. **3-D:** hanging sheets with depth. **Audio:**
curtain sway = mids; brightness ripples with treble; greens↔magentas over a set. **Hold/fire:**
*hold* = brighten/"solar storm". Distinct vertical-sheet structure (not a flat wash).

### 19. Accretion / black-hole v2 (inward spiral)
Particles **spiral inward** toward a moving sink and vanish (the inverse of an emitter) — a true
accretion disk, complementing the `vortex`. **3-D:** orbital decay in space. **Cube map:** LEDs
near particle paths light; a dark sink. **Audio:** infall rate = energy; bass = sink mass.
**Hold/fire:** *hold* = move/hold the sink (drag the black hole). Motion-led, very physical.

### 20. Magnetic dipole field lines
Trace the **field lines of a dipole** (bar magnet) whose axis rotates; LEDs near the lines glow,
arcing pole-to-pole. **3-D:** the lines loop through the volume in 3-D. **Audio:** dipole tilt =
mids, strength pulse = bass. **Hold/fire:** *fire* = flip polarity (lines snap to new config).
Science-y, organic loops — unlike anything currently in the set.

---

## Self-critique

Scoring each on the axes that actually matter here — **W**ireframe-readability (does it look
like the intent on a sparse edge cloud?), **D**istinctness (vs existing 10 presets), **P**erf
(realtime at ~9.7k LEDs, sharing the frame with other decks), **A**udio hook, and **build cost**.

### Tier 1 — build first (high readability, distinct, affordable)
- **#16 Face-normal sun.** Cheapest *and* the most 3-D-enhancing — it's the one effect that makes
  the cube's *form* obvious by shading. Uses existing normals. Almost no risk. **Build this first.**
- **#12 Edge-graph snake** and **#14 corner-to-corner lightning.** Structure-aware → guaranteed to
  read on the wireframe (they live on the edges). Main cost is a one-time **edge-adjacency graph**
  (build once from `geometry.build_edges` endpoints). Reusable infrastructure → unlocks #15 too.
- **#13 Triangle-lacing sequencer.** Directly answers "be aware of the triangles," and it's unique
  — nothing else references the truss build. Needs a LED→triangle map; the corner X-panels are
  already a region, so a first version is easy, a full version (beam-face triangles) is more work.
- **#8 Slicing plane** and **#9 breathing sphere.** Trivial signed-distance maths, stark, legible.
  #9 slightly overlaps the `Shockwave` trigger (continuous vs one-shot) — keep one or frame #9 as
  a bass-locked "lung." 
- **#17 Ripple tank.** Cheap (few sources), beautiful, strong kick hook. Low risk.

### Tier 2 — promising, needs care
- **#3 Boids** and **#10 torus knot** and **#11 platonic solid.** All reuse the proven
  **proximity-to-moving-geometry** trick (like the spiral), so they *will* read — but each needs a
  fat enough proximity width to catch the sparse LEDs, and boids needs the N×boids distance kept
  cheap (≤~40 boids, or a coarse spatial bin). Genuinely 3-D and distinct. Boids is the standout.
- **#19 accretion** overlaps the `vortex` conceptually; only build if its *inward* motion + draggable
  sink feel clearly different in motion — otherwise fold the "drag the centre" idea into `vortex`.
- **#1 Game of Life 3D** and **#6 Menger sponge.** Both are cheap to compute (membership/neighbour
  counts on a coarse grid). The risk is **legibility**: a volumetric on/off pattern sampled on a
  wireframe can read as random twinkle rather than "structure." Mitigation: coarse grid (so each
  voxel covers a chunk of edge), bold on/off, slow steps. Menger is the safer of the two (static
  self-similar structure vs Life's chaos). Worth a prototype; judge on a render before committing.
- **#18 Aurora.** Lovely, but "curtains" want vertical *sheets*; on a wireframe the sheets only
  show on the 4 posts + corners. May land closer to a fancy vertical wash. Prototype to confirm
  it's distinct from `plasma`/`AmbientWash` before shipping.

### Tier 3 — high risk / likely won't read on a wireframe (defer or cut)
- **#2 Reaction–Diffusion.** Beautiful in theory, but (a) it's the **most expensive** (per-frame
  Laplacian on a 3-D grid), and (b) it's a **surface/volume** pattern — sampled on sparse edges it
  loses the very spots/worms that make it RD. Would shine on the Phase-7 dense planes, not the cube.
  **Defer to the dense surfaces.**
- **#7 Mandelbulb shell.** Same volume-sampling problem plus heavy per-LED iteration; the cube
  grabs a thin, possibly-noisy shell. High effort, uncertain payoff. **Defer** (great on a future
  flat projector surface).
- **#4 DLA** and **#5 FBM cloud.** DLA is a slow background novelty (limited dance-floor punch);
  FBM risks being "plasma but blurrier." Keep as low-priority flavour, not headline acts.
- **#20 dipole field lines.** Cool, but the lines are thin curves in mostly-empty space → sparse
  hits, like the first spiral attempt. Would need fat lines + few of them. Medium risk.

### Cross-cutting lessons (apply to all of them)
1. **Favour the structure.** The wireframe rewards effects defined *on* the edges/corners/triangles
   or via *proximity to moving geometry/normals*. Pure volumetric fields underdeliver here — bank
   those for Phase 7's dense planes / projector surface, where they'll sing.
2. **Build the edge-adjacency graph once.** It's shared infrastructure for #12, #14, #15 (snake,
   lightning, current) — three Tier-1/2 effects for one piece of plumbing.
3. **Hard/stark + bold widths.** Stark thresholds and generous proximity widths consistently read
   better on sparse LEDs than soft gaussians (confirmed by the spiral/vortex tuning).
4. **Hold vs fire.** Most of these have a natural *hold* mode (freeze a sim, park the plane/sun,
   hold a sink, sustain an emitter) — worth wiring once `hold` triggers exist (now added).
5. **Perf budget.** Each deck shares the frame; keep per-effect cost in the few-ms range (coarse
   grids, ≤~40 entities, vectorised proximity). Flag RD/Mandelbulb as the ones to watch.

### Recommended first batch (when we build them)
`#16 sun`, `#12 snake`, `#13 triangles`, `#8 slice`, `#17 ripples` — all Tier 1, three of them
structure-aware, one shared graph dependency, all cheap. Then prototype `#3 boids`, `#6 Menger`,
`#11 platonic` and judge on renders before adding more.
