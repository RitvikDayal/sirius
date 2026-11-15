# Overview

## The idea

A white cane finds what is on the ground within reach. It misses things at head height,
drop-offs it does not touch, and anything further than a step away. SIRIUS tries to cover
that gap with cameras: look ahead, recognise what is there, measure how far away it is, and
say so in a few words.

The long-term shape is a pair of glasses with a camera at each temple and the computing done
on the wearer's phone. Phase 1 is the bench version of that: two USB webcams on a ruler,
standing in for the glasses, with a laptop doing the work.

SIRIUS restarts an earlier attempt called A-Eyes (2021). A-Eyes calibrated a stereo pair but
never connected depth to detection, and the distances it spoke were hard-coded random
values. SIRIUS builds the part A-Eyes skipped.

## What Phase 1 set out to prove

Can two cheap, unsynchronised webcams on a laptop tell a person what is in front of them and
how far away it is, quickly enough and accurately enough to be useful?

The targets, from the approved design:

| Target | Value |
|---|---|
| Distance error | 10% or less at 0.5 to 3 m, 20% or less at 5 m |
| Time from camera frame to speech starting | 300 ms or less at the 90th percentile |
| Scripted test | the right object and zone spoken in at least 17 of 20 placements |
| Stability | 10 minutes live with no crash and no growing lag |
| Honesty | no distance spoken without a valid measurement behind it |

[status.md](status.md) says which of these have been met.

## Ground rules

These shaped most of the code.

- Never speak a number that was not measured. If depth is missing or a camera is dark,
  SIRIUS still names the object but leaves the distance out. The one exception is a setting,
  `speak_approx_distances`, which lets single-camera estimates be spoken with the word
  "about" until the stereo pair is calibrated.
- One alert at a time, most urgent first. Nothing is repeated within 5 seconds.
- An alert that is more than a second old is dropped, not spoken late.
- Everything runs offline once the models are downloaded.
- Each stage sits behind a small interface (camera source, depth method, detector, voice),
  so the webcams can later be swapped for glasses or a network stream without touching the
  rest.

## What is out of scope for Phase 1

Spoken questions and answers ("can you find my water bottle?"), maps and nearby places,
haptics, outdoor street navigation, a phone or wearable build, and trials with blind users.
Those belong to later phases. [status.md](status.md) lists the plan for Phase 2.
