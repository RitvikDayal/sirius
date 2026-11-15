# SIRIUS Website Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a one-page SIRIUS site at `https://ritvikdayal.github.io/sirius/`, built from mockup Echo v5, and link it from the portfolio.

**Architecture:** Static files in `site/`: semantic HTML for all content, one ES module that draws the point-cloud room with three.js, and a small pure module holding SIRIUS's speaking rules (tested under Node). A GitHub Actions workflow deploys `site/` to Pages.

**Tech Stack:** HTML, CSS, ES modules, three.js r160 (vendored), Web Speech API, Node 24 `node:test`, GitHub Actions `actions/deploy-pages`.

**Spec:** `docs/superpowers/specs/2026-11-15-sirius-website-design.md`

## Global Constraints

- No build step, framework, analytics, cookies or tracking. Fonts from Google Fonts only.
- Palette and type exactly as the spec's Look table; Archivo width 125 weight 800 for display.
- Every number on the page comes from the project's measurements (spec, "All numbers on the page").
- No claims beyond the spec's non-goals: say prototype, not calibrated, not tried by blind users, alongside a cane.
- Copy follows the humanizer rules: no em or en dashes, sentence-case headings, no emoji, straight quotes.
- Branch `feat/website` (stacked on `chore/public-release`); Ritvik merges. Portfolio change goes through its own PR from a separate worktree; his uncommitted work on `refresh-live-numbers` is not touched.

## Review Focus

1. Screen reader visitor: must reach every section by heading, never hear captions stream. Pin: Task 2 check that the canvas is `aria-hidden` and captions have `aria-live="off"`.
2. Reduced motion: page must show a still, fully lit room with one caption and no animation loop. Pin: Task 2 Playwright run with `reducedMotion: "reduce"`.
3. Phone width (393 px): no horizontal scroll, readable text, fewer points. Pin: Task 2 Playwright run at 393x852 checking `scrollWidth <= innerWidth`.
4. Hidden tab or scrolled past the hero: animation pauses. Pin: Task 2 check that the frame counter stops when `document.hidden` or hero off screen.
5. Browser without speech synthesis: "Hear it" is disabled with a clear label. Pin: Task 2 check with `speechSynthesis` deleted before load.

---

### Task 1: Speaking rules and room data

**Files:**
- Create: `site/rules.js`, `site/room.js`
- Test: `site/tests/rules.test.mjs`

**Interfaces:**
- Produces: `ZONES` (array of `{name, max, hex, css}`: urgent 1.0 `#FF5A36`, near 2.5 `#FFB23F`, aware 5.0 `#B8935A`); `zoneOf(r) -> zone | null`; `distanceWords(r) -> string`; `direction(dx, dz) -> "left"|"ahead"|"right"` (±15°); `phrase(label, eye, at) -> {r, text, zone}`. `room.js`: `OBJECTS` (chair, person, table, bottle with `label`, `at`), `makeRoom(density) -> {positions: Float32Array, tags: Uint8Array}`.

- [ ] **Step 1: Write failing tests** in `site/tests/rules.test.mjs` (Node `node:test`): `distanceWords` boundaries 0.74 "half a metre", 0.75 "one metre", 1.49 "one metre", 2.49 "two metres", 4.6 "five metres" (same thresholds as `src/sirius/alerts.py`); `zoneOf(0.8).name === "urgent"`, `zoneOf(1.0).name === "near"`, `zoneOf(5.1) === null`; `direction(-1, -2) === "left"`, `direction(0, -2) === "ahead"`; `phrase("chair", [0,1.6,0], [-1.3,0.5,-2.2]).text === "chair, two metres, left"`; `makeRoom(1).positions.length % 3 === 0`.
- [ ] **Step 2: Run** `node --test "site/tests/*.test.mjs"` → FAIL (modules missing).
- [ ] **Step 3: Implement** by moving the mockup's `echo-common.js` rules (without the voice) into `rules.js` and `room.js` unchanged in behaviour.
- [ ] **Step 4: Run** `node --test "site/tests/*.test.mjs"` → all pass.
- [ ] **Step 5: Commit** `Add the website's speaking rules and room data, with tests`.

### Task 2: The page

**Files:**
- Create: `site/index.html`, `site/scene.js`, `site/vendor/three.module.js` (copy of `src/sirius/viewer/static/three.module.js`), `site/favicon.svg`
- Test: `site/tests/check-page.mjs` (Playwright-driven checks, run by hand with the Playwright MCP or `npx playwright`)

**Interfaces:**
- Consumes: Task 1 exports.
- Produces: `scene.js` default export `startScene({canvas, labelsRoot, captionEl, voice})`; `window.__sirius = {frames}` frame counter for checks.

- [ ] **Step 1:** Build `index.html` sections in spec order (hero, How it works with the five numbered steps, What it says, Where it is today, Look inside, footer), with skip link, landmarks, headings in order, `<canvas aria-hidden="true">`, a visually hidden text description of the animation, caption `aria-live="off"`, and the dark fade behind hero text.
- [ ] **Step 2:** Port v5's scene into `scene.js`: mirrored edge sources, crossing waves, zone-colour lighting once both passed, fade between passes (8.5 s), rings, labels, captions; drop the debug `__dbg` and `?t=` freeze. Add: pause on `visibilitychange` and when the hero leaves the viewport (`IntersectionObserver`); density 0.45 and pixel ratio 1.5 below 760 px wide; reduced motion draws one lit frame.
- [ ] **Step 3: Verify** in a real browser at 1440x900: no console errors, waves visible at an early moment, room lit and a caption shown later.
- [ ] **Step 4: Verify** Review Focus 1–5: canvas `aria-hidden`, caption `aria-live="off"`, headings h1 then h2s in order; reduced-motion run shows a lit still frame and `__sirius.frames` stays at 1; 393x852 run has `document.documentElement.scrollWidth <= innerWidth`; frames stop increasing after scrolling past the hero; with `speechSynthesis` removed the button is disabled and says speech is not available.
- [ ] **Step 5: Commit** `Add the SIRIUS website: crossing-echo hero and project story`.

### Task 3: Publishing

**Files:**
- Create: `.github/workflows/pages.yml`, `site/social.jpg`
- Modify: `README.md` (link to the site), `docs/README.md` (link to the site)

- [ ] **Step 1:** Workflow: on push to `main` touching `site/**` or the workflow, and on manual dispatch; permissions `pages: write`, `id-token: write`; steps `actions/checkout`, `actions/configure-pages`, `actions/upload-pages-artifact` with `path: site`, `actions/deploy-pages`. Concurrency group `pages`.
- [ ] **Step 2:** Social preview `site/social.jpg` (1200x630) from a screenshot of the lit hero; `og:` and `twitter:` meta tags in `index.html` pointing at the absolute Pages URL.
- [ ] **Step 3: Verify** `node --test "site/tests/*.test.mjs"` passes and the workflow YAML parses (`python -c "import yaml"` load).
- [ ] **Step 4: Commit** `Publish the website to GitHub Pages`; push `feat/website`; open the PR.

### Task 4: Portfolio link

**Files (in `RitvikDayal/ritvikdayal.github.io`, worktree on `origin/master`):**
- Modify: `index.html` (a SIRIUS card beside FeatherWall's, same markup and link style: "Source" to the repo, "Site" to the Pages URL)

- [ ] **Step 1:** Add the card with a two-sentence description in the portfolio's voice and the same tag styling.
- [ ] **Step 2: Verify** by rendering the portfolio locally and screenshotting the card; links resolve to the right URLs.
- [ ] **Step 3: Commit** `Add SIRIUS to the projects`; push branch `feat/sirius-link`; open the PR.

### After merge (needs Ritvik's merges first)

- Make `RitvikDayal/sirius` public, enable Pages with the GitHub Actions source, re-run the workflow, and check the live URL renders.
