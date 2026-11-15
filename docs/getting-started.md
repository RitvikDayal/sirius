# Getting started

## What you need

- Windows 11. Capture uses DirectShow and the voice uses the built-in Windows speech engine.
- An NVIDIA GPU. Development used an RTX 5090 Laptop GPU (24 GB).
- Python 3.11, managed by [uv](https://docs.astral.sh/uv/).
- `ffmpeg` on your `PATH`. SIRIUS reads the cameras through it. `winget install ffmpeg` works.
- Two identical USB webcams fixed side by side on something rigid. See
  [hardware.md](hardware.md).

## Install

```
git clone https://github.com/RitvikDayal/sirius.git
cd sirius
uv sync
```

`uv sync` installs PyTorch built for CUDA 12.8 and onnxruntime-gpu 1.26. The versions are
pinned on purpose; [findings.md](findings.md) explains why.

The first run of anything that uses a model downloads it from Hugging Face into your local
cache. The Fast-FoundationStereo ONNX file is fetched separately:

```
uv run python scripts/fetch_models.py
```

## Find and check the cameras

```
uv run sirius devices
```

This lists every video device Windows knows about, with its index and its full device path.
Both rig cameras call themselves "USB Camera", so SIRIUS tells them apart by a fragment of
that path, which is tied to the USB port. Put the fragments in `config/rig.toml`:

```toml
left_path = "6&1ec6b2f7"    # the camera on the left when you look the way the cameras look
right_path = "6&315a9f63"
```

Swapping the plugs between ports swaps left and right, so label the cables. Then:

```
uv run sirius check
```

This runs both cameras for 10 seconds and reports frames per second, how far apart in time
the paired frames are, brightness and colour, and whether left and right are the right way
round. It exits with an error if left and right are swapped.

## See it working

```
uv run sirius view --speak
```

Your browser opens the dashboard at http://127.0.0.1:8765 with both cameras, the depth map,
detected objects, a 3D view, and the line SIRIUS last spoke. Before calibration it uses the
single-camera depth model. [dashboard.md](dashboard.md) describes each panel.

To try it without cameras, record a clip first and replay it:

```
uv run sirius record --seconds 10 --out data/clips/test
uv run sirius view --replay data/clips/test
```

## Calibrate

Stereo distances need calibration. [calibration.md](calibration.md) covers printing the
board, capturing, and checking the result.

## Run the tests

```
uv run pytest
```

There are 73 tests. Most run anywhere. Tests marked `gpu` need CUDA and the downloaded
models, and skip with a reason if those are missing. Everything under `data/` (recordings,
calibration captures, models) is git-ignored.
