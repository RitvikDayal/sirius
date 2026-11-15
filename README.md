# SIRIUS

> **Research prototype. Not a safety device.** It is meant to sit alongside a white cane, never to replace one.

Project page: **https://ritvikdayal.github.io/sirius/**

SIRIUS is an experiment in giving a blind or low-vision person a second pair of eyes. Two
matched cameras look ahead, a detector names what is in view, a depth estimator works out
how far away each thing is, and the computer speaks a short alert such as
"person, one metre, ahead".

Phase 1, the code in this repository, runs on a Windows laptop with two cheap USB webcams
fixed to a steel ruler. It captures both cameras, matches their frames in time, estimates
depth, detects and tracks objects, decides what is worth saying, and speaks it. A browser
dashboard shows every stage live, including a 3D point cloud of the current frame.

```
 left cam ─┐                          ┌─► depth ──────┐
           ├─► pair frames ─► rectify ┤               ├─► track ─► alert rules ─► voice
right cam ─┘   by timestamp           └─► detection ──┘                └─► dashboard
```

## Where it stands

| Works today | Not done yet |
|---|---|
| Capture from both cameras at 25 FPS in room light, paired to within ~30 ms | Calibration on the real rig (needs the printed board) |
| Object detection, tracking and spoken alerts, about 15 FPS end to end | Stereo distances on the real rig (needs calibration) |
| Live dashboard with depth map, boxes, 3D view and a mute button | Depth bake-off and the acceptance tests |
| 73 automated tests | Distances you can trust: the current single-camera estimates are badly off up close |

The details, with numbers, are in [docs/status.md](docs/status.md).

## Quick start

You need Windows 11, an NVIDIA GPU, [uv](https://docs.astral.sh/uv/) and `ffmpeg` on your
`PATH`.

```
uv sync
uv run sirius devices      # find the two cameras
uv run sirius check        # FPS, frame pairing, left/right check
uv run sirius view --speak # dashboard at http://127.0.0.1:8765, voice on
```

[docs/getting-started.md](docs/getting-started.md) walks through setup step by step.

## Documentation

Start at [docs/README.md](docs/README.md). It links everything: how the system is built, each
command, calibration, the depth methods, the alert rules, the hardware, what was learned
along the way, and the plan for the next phase.

## Models and their licences

| Model | Used for | Licence |
|---|---|---|
| D-FINE small (`ustc-community/dfine-small-coco`) | object detection | Apache-2.0 |
| Fast-FoundationStereo (`nvidia/c-fast-foundationstereo`) | learned stereo depth | NVIDIA Open Model Agreement |
| Depth Anything V2 metric indoor small | single-camera depth, comparison only | see the model card |

`src/sirius/viewer/static/` carries a copy of three.js r160 (MIT) so the dashboard works
offline.

## Licence

MIT, see [LICENSE](LICENSE). The models keep their own licences, listed above.
