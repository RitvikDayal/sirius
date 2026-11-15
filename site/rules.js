// SIRIUS's speaking rules, the same thresholds as src/sirius/alerts.py and fusion.py.
export const ZONES = [
  { name: "urgent", max: 1.0, hex: 0xFF5A36, css: "#FF5A36" },
  { name: "near", max: 2.5, hex: 0xFFB23F, css: "#FFB23F" },
  { name: "aware", max: 5.0, hex: 0x8A6A3A, css: "#B8935A" },
];

// True when a new pass has begun, however far the last frame stepped.
export function passWrapped(prevPhase, phase) {
  return phase < prevPhase;
}

export function zoneOf(r) {
  for (const z of ZONES) if (r < z.max) return z;
  return null;
}

export function distanceWords(r) {
  if (r < 0.75) return "half a metre";
  if (r < 1.5) return "one metre";
  if (r < 2.5) return "two metres";
  if (r < 3.5) return "three metres";
  if (r < 4.5) return "four metres";
  return "five metres";
}

// Bearing from the viewer, positive to the right, in degrees.
export function direction(dx, dz) {
  const deg = Math.atan2(dx, -dz) * 180 / Math.PI;
  return deg < -15 ? "left" : deg > 15 ? "right" : "ahead";
}

export function phrase(label, eye, at) {
  const dx = at[0] - eye[0], dy = at[1] - eye[1], dz = at[2] - eye[2];
  const r = Math.hypot(dx, dy, dz);
  return { r, text: `${label}, ${distanceWords(r)}, ${direction(dx, dz)}`, zone: zoneOf(r) };
}
