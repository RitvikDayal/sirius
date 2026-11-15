# SIRIUS website design

Approved direction: mockup "Echo v5, crossing" (2026-11-15). This document turns that mockup
into a real page.

## Intent

A single page that explains SIRIUS to someone who has never heard of it, in under a minute,
and lets them feel what it does rather than read about it. It sits alongside the author's
portfolio and the FeatherWall site and shares their character: near-black, very large
display type, one idea carried by the 3D scene.

Readers, in rough order: people browsing the portfolio, engineers curious about the build,
and people interested in assistive technology.

## Goals

- Explain in plain words what SIRIUS is, how it works, what it says, and where it stands.
- Show the core idea live: two cameras, two waves, a room appearing where both have looked.
- Let a visitor hear SIRIUS speak, on request.
- Point to the source and the docs.

## Non-goals

- No claims of results the project has not shown. It is a bench prototype, not calibrated,
  not tried by blind users.
- No sign-up, analytics, cookies or tracking.
- No build step or framework. Plain HTML, CSS and one JavaScript module.

## Anti-goals

- A page a screen-reader user cannot use. For a project about blindness that would be a
  failure however good it looks.
- Motion that ignores the visitor's reduced-motion setting.
- Text that is hard to read over the animation.

## The page

```
┌─ hero ─────────────────────────────────────────────┐
│ SIRIUS                                  How · Says · Status · Source
│
│  [two waves enter from the screen edges, cross,
│   and the room lights up from the middle]
│
│ SIRIUS
│ A second pair of eyes for people who are blind or have low vision.
│ Two small cameras ... chair, two metres, left.
│ Each camera sends out its own wave ... only then can SIRIUS measure it.
│ (Hear it)  person, one metre, ahead
│ 2 cameras | 17 kinds | 25 fps | ~50 ms | offline
└────────────────────────────────────────────────────┘
  How it works: See, Measure, Recognise, Decide, Speak   (a real sequence, numbered)
  It only speaks when it matters: three zones + the quiet rules
  Where it is today: what works, what does not yet, what is next (Phase 2)
  Look inside: source, docs, licence
  Footer: who built it, link back to the portfolio
```

| Section | Content source |
|---|---|
| Hero | mockup v5: copy, facts strip, Hear it button, floor zone rings, floating labels |
| How it works | the five steps from mockup v2, with the measured numbers from `docs/status.md` and `docs/depth.md` |
| What it says | the zone table and quiet rules from mockup v1 and `docs/alerts-and-voice.md` |
| Where it is today | `docs/status.md` and the Phase 2 plan in `docs/hardware.md` |
| Look inside | links to the repository, `docs/README.md`, the licence |

All numbers on the page come from the project's own measurements: 2 cameras about 12 cm
apart, 17 announced classes, 25 frames a second in room light, speech starting in about
50 ms once warm, SGBM at about 17 ms a frame, offline.

## Look

| Token | Value |
|---|---|
| Background | `#000` |
| Phosphor amber (near zone, accents) | `#FFB23F` |
| Urgent | `#FF5A36` |
| Aware | `#B8935A` |
| Left wave | `#FF7A3D` |
| Right wave | `#FFE2A8` |
| Bone (text) | `#EDE6DA` |
| Muted text | `#A79F92` |
| Type | Archivo from Google Fonts: width 125 and weight 800 for display, normal width for body |

## Behaviour

- The scene is a made-up room (floor, walls, a chair, a person, a table with a bottle) built
  from points, not real footage.
- Two wave sources sit just outside the left and right edges of the view, mirrored. Each
  pass: the waves sweep in, cross, and a point lights in its distance-zone colour once both
  have passed it. The room fades before the next pass. One pass takes about 8.5 seconds.
- Captions show the sentence SIRIUS would say for each object as both waves reach it, using
  the real rules (distance words, left/ahead/right, zones).
- "Hear it" turns on the browser's own speech (Web Speech API). Off by default; turning it on
  speaks one short line to confirm.
- Reduced motion: no animation. The room is drawn once, fully lit, with labels and one caption.
- Small screens: fewer points, lower pixel ratio, facts in two columns.
- The scene pauses when the tab is hidden and when the hero scrolls out of view.

## Accessibility

- Real headings in order, a skip link, landmarks, visible focus.
- The canvas is hidden from assistive technology; a text description of the animation
  stands in for it.
- Captions are not announced continuously (that would talk over everything); the Hear it
  button is the way to listen.
- Text sits on a dark fade so contrast holds over the points.

## Hosting

- Files live in `site/` in this repository: `index.html`, `scene.js`, `room.js`,
  `rules.js`, `vendor/three.module.js` (r160, MIT, copied from the dashboard), a favicon and
  a social preview image.
- A GitHub Actions workflow (`.github/workflows/pages.yml`) publishes `site/` to GitHub
  Pages on every push to `main` that touches it. URL: `https://ritvikdayal.github.io/sirius/`.
- The repository becomes public first (decided 2026-11-15), so Pages works on the free plan.

## Portfolio link

The portfolio (`RitvikDayal/ritvikdayal.github.io`) gets a link to the SIRIUS page, placed
the way its other project links are, through a pull request.

## Left to the builder

Exact point counts, animation timings within the ranges above, section spacing, the social
preview image, and wording polish that keeps every fact intact.
