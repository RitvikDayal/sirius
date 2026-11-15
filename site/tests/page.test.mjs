import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");

// The page must not claim more than the project's docs support.
test("no overclaims", () => {
  assert.ok(!html.includes("never says a distance it did not measure"), "approximate distances are spoken today");
  assert.ok(!html.includes("ordinary laptop"), "timings come from an RTX 5090 laptop");
  assert.ok(!/until speech starts/.test(html), "50 ms is the voice starting, not camera-to-speech latency");
  assert.ok(!/Said once, after anything closer/.test(html), "alerts.py repeats after 5 s");
});

test("skip link lands on the main content", () => {
  assert.match(html, /<a class="skip" href="#top">/);
});

test("Hear it keeps one name and shows state with aria-pressed", () => {
  assert.ok(!html.includes('"Sound on"'), "the label must not change with the state");
});
