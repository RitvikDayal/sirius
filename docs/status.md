# Status

Phase 1 is built and runs end to end on the bench rig: capture, depth, detection, tracking,
alerts, voice and the dashboard. What it cannot do yet is give trustworthy distances, because
the real rig has not been calibrated.

## Against the Phase 1 targets

| Target | Status |
|---|---|
| Distance error: 10% or less up to 3 m, 20% at 5 m | Not measured. Needs calibration, then the bake-off. |
| Frame to speech start: 300 ms or less (p90) | Not measured end to end. Parts measured: step time about 56 to 66 ms with single-camera depth and detection, speech start about 50 ms once warm. |
| Scripted test: 17 of 20 placements right | Not run. |
| 10 minutes live without crash or growing lag | Not run as a formal test. |
| No distance spoken without valid depth | Built and tested with simulated dark and stale cameras. Not yet checked by covering a lens on the live rig. |

## Built and tested

| Area | Evidence |
|---|---|
| Capture | Both cameras at 25 FPS in room light; paired frames 2 to 13 ms apart at the median, up to 30 ms at p90 |
| Left/right check | Correct order measured at +70 to +85 px; a swapped config is caught |
| Calibration code | Recovers a 117 mm baseline to 0.74% on synthetic images |
| Depth | SGBM, Fast-FoundationStereo and single-camera depth all run; timings in [depth.md](depth.md) |
| Detection | D-FINE finds people, chairs, beds, laptops and backpacks in recorded and live frames, 24 to 62 ms per frame |
| Alerts and voice | Rules covered by tests; voice live with mute |
| Dashboard | Checked in a real browser: live cameras, depth, boxes, 3D view |
| Tests | 73 passing |

## Known problems

- Distances are not trustworthy yet. Before calibration they come from the single-camera
  model, which read a person at about 0.45 m as 1.7 to 1.8 m.
- Fast-FoundationStereo is too slow for live use on this laptop (133 ms per frame).
- The rig's spacing has only been estimated from a photo (about 11.5 to 12 cm).
- The cameras drop to 25 FPS in ordinary room light.
- In dim light one camera can switch to infrared while the other does not.
- When a detection flickers, the tracker gives it a new identity. The repeated-sentence rule
  hides this from the user, but the tracker itself is simple.

## Next steps for Phase 1

1. Measure the lens spacing, print the board, calibrate, and pass `sirius baseline-check`.
2. Run the depth bake-off and let it choose the default stereo method.
3. Turn off `speak_approx_distances` once stereo distances are in use.
4. Run the acceptance tests: latency from reveal clips, the 20-placement scripted test,
   a 10-minute run, and covering one lens live.

## Phase 2

The cameras move off the laptop onto a worn Raspberry Pi 5, with a VL53L5CX infrared
time-of-flight sensor added, streaming to the laptop over Wi-Fi. Parts are listed in
[hardware.md](hardware.md). Research for the step after that, running everything on a phone,
found:

- iOS has no USB webcam driver, so frames must reach a phone over the network.
- Apple publishes Depth Anything V2 small for iPhones at about 31 to 34 ms per frame on the
  Neural Engine. A YOLO-style detector is the safer choice there than D-FINE.
- The weak point is the local wireless link. iOS 26 added Wi-Fi Aware for direct
  device-to-device links, but no Raspberry Pi support for it was found, and a Pi acting as a
  hotspot can be dropped by iOS. This has to be measured on real hardware.
