// A made-up room drawn as points, with the objects SIRIUS would announce.
// Units are metres; the viewer stands at the origin looking down -z, eyes at 1.6 m.
export const OBJECTS = [
  { label: "chair", at: [-1.3, 0.5, -2.2] },
  { label: "person", at: [0.2, 0.9, -1.1] },
  { label: "table", at: [1.6, 0.4, -3.0] },
  { label: "bottle", at: [1.5, 0.9, -3.0] },
];

function rnd(a, b) { return a + Math.random() * (b - a); }

export function makeRoom(density = 1) {
  const pts = [], tag = [];
  const push = (x, y, z, t = 0) => { pts.push(x, y, z); tag.push(t); };
  const n = (k) => Math.round(k * density);
  for (let i = 0; i < n(7000); i++) push(rnd(-3, 3), 0, rnd(-6, 1));            // floor
  for (let i = 0; i < n(5000); i++) push(rnd(-3, 3), rnd(0, 2.8), -6);          // back wall
  for (let i = 0; i < n(3500); i++) push(-3, rnd(0, 2.8), rnd(-6, 1));          // left wall
  for (let i = 0; i < n(3500); i++) push(3, rnd(0, 2.8), rnd(-6, 1));           // right wall
  // chair: seat, back, legs
  for (let i = 0; i < n(900); i++) push(rnd(-1.55, -1.05), 0.48, rnd(-2.45, -1.95), 1);
  for (let i = 0; i < n(700); i++) push(rnd(-1.55, -1.05), rnd(0.5, 1.0), -2.45, 1);
  for (const [lx, lz] of [[-1.53, -2.43], [-1.07, -2.43], [-1.53, -1.97], [-1.07, -1.97]])
    for (let i = 0; i < n(80); i++) push(lx, rnd(0, 0.48), lz, 1);
  // person: body cylinder + head
  for (let i = 0; i < n(2600); i++) {
    const a = rnd(0, Math.PI * 2), h = rnd(0, 1.45), r = 0.2 + 0.05 * Math.sin(h * 2.2);
    push(0.2 + r * Math.cos(a), h, -1.1 + r * 0.7 * Math.sin(a), 2);
  }
  for (let i = 0; i < n(700); i++) {
    const u = rnd(-1, 1), a = rnd(0, Math.PI * 2), s = Math.sqrt(1 - u * u);
    push(0.2 + 0.11 * s * Math.cos(a), 1.6 + 0.13 * u, -1.1 + 0.11 * s * Math.sin(a), 2);
  }
  // table top + legs, bottle
  for (let i = 0; i < n(1200); i++) push(rnd(1.1, 2.1), 0.75, rnd(-3.4, -2.6), 3);
  for (const [lx, lz] of [[1.12, -3.38], [2.08, -3.38], [1.12, -2.62], [2.08, -2.62]])
    for (let i = 0; i < n(90); i++) push(lx, rnd(0, 0.75), lz, 3);
  for (let i = 0; i < n(260); i++) {
    const a = rnd(0, Math.PI * 2), h = rnd(0.75, 1.02);
    const r = h > 0.95 ? 0.02 : 0.035;
    push(1.5 + r * Math.cos(a), h, -3.0 + r * Math.sin(a), 4);
  }
  return { positions: new Float32Array(pts), tags: new Uint8Array(tag) };
}
