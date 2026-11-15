// The hero scene: two waves start at opposite edges of the view, cross, and the room lights
// up once both have passed a point, because only then could SIRIUS measure it.
import * as THREE from "./vendor/three.module.js";
import { makeRoom, OBJECTS } from "./room.js";
import { ZONES, phrase, passWrapped } from "./rules.js";

const PERIOD = 8.5;       // seconds per pass
const SPEED = 1.45;       // metres per second
const EYE = [0, 1.6, 0];  // where the listener stands
const LEFT = new THREE.Color(0xff7a3d), RIGHT = new THREE.Color(0xffe2a8), FAR = new THREE.Color(0x5a4a35);

export function makeVoice() {
  const supported = typeof window.speechSynthesis !== "undefined" && typeof window.SpeechSynthesisUtterance !== "undefined";
  let on = false;
  return {
    supported,
    get on() { return on; },
    toggle() { on = supported && !on; if (!on && supported) speechSynthesis.cancel(); return on; },
    say(text, urgent = false) {
      if (!on) return;
      if (urgent) speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.rate = 1.1;
      speechSynthesis.speak(u);
    },
  };
}

export function startScene({ canvas, hero, labelsRoot, captionEl, voice }) {
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const small = innerWidth < 760;
  const stats = (window.__sirius = { frames: 0, running: false, drawMs: 0 });

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: !small });
  } catch {
    document.documentElement.classList.add("no-webgl");
    captionEl.textContent = phrase("person", EYE, OBJECTS[1].at).text;
    return { live: false, stop() {} };
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, small ? 1.5 : 2));

  const scene = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, 0.05, 50);
  cam.position.set(0.55, 2.05, 1.9);
  cam.lookAt(0.15, 0.7, -2.4);
  cam.updateMatrixWorld();

  const { positions, tags } = makeRoom(small ? 0.45 : 1);
  const N = positions.length / 3;
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const col = new Float32Array(N * 3);
  geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
  scene.add(new THREE.Points(geo, new THREE.PointsMaterial({
    size: small ? 0.028 : 0.02, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  })));

  // Zone colour per point, from its distance to the listener.
  const zc = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const d = Math.hypot(positions[i*3] - EYE[0], positions[i*3+1] - EYE[1], positions[i*3+2] - EYE[2]);
    const z = ZONES.find(q => d < q.max), c = z ? new THREE.Color(z.hex) : FAR;
    zc[i*3] = c.r; zc[i*3+1] = c.g; zc[i*3+2] = c.b;
  }

  // Distance rings on the floor.
  const rings = ZONES.map(z => {
    const pts = Array.from({ length: 181 }, (_, k) => {
      const a = Math.PI * (0.06 + 0.88 * k / 180);
      return new THREE.Vector3(Math.cos(a) * z.max, 0.005, -Math.sin(a) * z.max);
    });
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: z.hex, transparent: true, opacity: 0.3 }));
    scene.add(line);
    return line;
  });

  // Wave sources just outside the left and right edges of the view, mirrored.
  let EYES, dL, dR;
  function placeSources() {
    cam.aspect = innerWidth / innerHeight;
    cam.updateProjectionMatrix();
    cam.updateMatrixWorld();
    const edge = (x) => new THREE.Vector3(x, 0.05, 0.5).unproject(cam).sub(cam.position).normalize().multiplyScalar(3.6).add(cam.position);
    const l = edge(-1.02), r = edge(1.02), mid = (l.x + r.x) / 2, half = (r.x - l.x) / 2, zAvg = (l.z + r.z) / 2;
    EYES = [[mid - half, l.y, zAvg], [mid + half, r.y, zAvg]];
    dL = new Float32Array(N); dR = new Float32Array(N);
    for (let i = 0; i < N; i++) {
      const x = positions[i*3], y = positions[i*3+1], z = positions[i*3+2];
      dL[i] = Math.hypot(x - EYES[0][0], y - EYES[0][1], z - EYES[0][2]);
      dR[i] = Math.hypot(x - EYES[1][0], y - EYES[1][1], z - EYES[1][2]);
    }
  }
  placeSources();
  const gL = new Float32Array(N), gR = new Float32Array(N), lit = new Float32Array(N);

  const labels = OBJECTS.map(o => {
    const el = document.createElement("div");
    el.className = "obj-label";
    el.setAttribute("aria-hidden", "true");
    labelsRoot.appendChild(el);
    return el;
  });

  let said = new Set(), lastPhase = 0;
  function draw(s) {
    const t0 = performance.now();
    const phase = reduce ? PERIOD : s % PERIOD, r = reduce ? 99 : phase * SPEED;
    const fade = reduce ? 1 : Math.min(1, Math.max(0, (PERIOD - phase) / 0.9));
    if (passWrapped(lastPhase, phase)) said = new Set();
    lastPhase = phase;
    for (let i = 0; i < N; i++) {
      gL[i] = Math.abs(dL[i] - r) < 0.13 ? 1 : gL[i] * 0.9;
      gR[i] = Math.abs(dR[i] - r) < 0.13 ? 1 : gR[i] * 0.9;
      const both = r >= dL[i] && r >= dR[i];
      if (!both) lit[i] = 0;
      else lit[i] = lit[i] === 0 ? 1.6 : Math.max(0.55, lit[i] * 0.95);  // flash as the second wave arrives
      const w = tags[i] ? 1.3 : 0.75, g = (reduce ? 0.6 : lit[i] * fade) * w + 0.03;
      const fl = reduce ? 0 : gL[i] * 0.5 * w, fr = reduce ? 0 : gR[i] * 0.5 * w;
      col[i*3] = zc[i*3] * g + LEFT.r * fl + RIGHT.r * fr;
      col[i*3+1] = zc[i*3+1] * g + LEFT.g * fl + RIGHT.g * fr;
      col[i*3+2] = zc[i*3+2] * g + LEFT.b * fl + RIGHT.b * fr;
    }
    geo.attributes.color.needsUpdate = true;
    rings.forEach(l => { l.material.opacity = 0.12 + 0.25 * fade; });

    OBJECTS.forEach((o, k) => {
      const p = phrase(o.label, EYE, o.at), v = new THREE.Vector3(...o.at).project(cam), el = labels[k];
      const reach = Math.max(
        Math.hypot(o.at[0] - EYES[0][0], o.at[1] - EYES[0][1], o.at[2] - EYES[0][2]),
        Math.hypot(o.at[0] - EYES[1][0], o.at[1] - EYES[1][1], o.at[2] - EYES[1][2]));
      el.style.left = ((v.x + 1) / 2 * innerWidth) + "px";
      el.style.top = ((1 - v.y) / 2 * innerHeight - 14) + "px";
      el.style.color = p.zone ? p.zone.css : "#EDE6DA";
      el.innerHTML = `${o.label}<small>${p.r.toFixed(1)} m, ${p.zone ? p.zone.name : "beyond 5 m"}</small>`;
      el.style.opacity = r > reach ? fade : 0;
      if (!reduce && r > reach && !said.has(k) && o.label !== "table") {
        said.add(k);
        captionEl.textContent = p.text;
        captionEl.classList.toggle("urgent", !!p.zone && p.zone.name === "urgent");
        voice.say(p.text, !!p.zone && p.zone.name === "urgent");
      }
    });
    if (reduce) captionEl.textContent = phrase("person", EYE, OBJECTS[1].at).text;
    renderer.render(scene, cam);
    stats.frames++;
    stats.drawMs = performance.now() - t0;
  }

  function resize() {
    renderer.setSize(innerWidth, innerHeight, false);
    placeSources();
    if (reduce || !stats.running) draw(performance.now() / 1000);
  }
  addEventListener("resize", resize);
  renderer.setSize(innerWidth, innerHeight, false);

  if (reduce) {
    draw(0);
    return { live: false, stop() {} };
  }

  // Run only while the hero is on screen and the tab is visible.
  let raf = 0, heroVisible = true;
  const loop = (t) => { draw(t / 1000); raf = requestAnimationFrame(loop); };
  function update() {
    const should = heroVisible && !document.hidden;
    if (should && !stats.running) { stats.running = true; raf = requestAnimationFrame(loop); }
    if (!should && stats.running) { stats.running = false; cancelAnimationFrame(raf); }
    labelsRoot.hidden = !heroVisible;
  }
  new IntersectionObserver(([e]) => { heroVisible = e.isIntersecting; update(); }, { threshold: 0.05 }).observe(hero);
  document.addEventListener("visibilitychange", update);
  update();
  return { live: true, stop() { heroVisible = false; update(); } };
}
