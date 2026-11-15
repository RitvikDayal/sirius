# Commands

Every command takes `--config PATH` (default `config/rig.toml`) before the command name:
`uv run sirius --config other.toml check`.

## Cameras

| Command | What it does |
|---|---|
| `sirius devices` | Lists DirectShow video devices with index and path, and marks which is left and right according to the config. |
| `sirius check [--seconds 10]` | Runs both cameras and reports FPS per camera, pair timing (p50 and p90), brightness, colour saturation, and a left/right identity check. Fails under 24 FPS, with pair timing over 33 ms at p90, or if left and right are swapped. Warns between 24 and 28 FPS, which usually means dim light. |
| `sirius record --out DIR [--seconds 5]` | Records stereo pairs as lossless PNGs plus a `pairs.csv` of capture timestamps. Replay a recording with `view --replay`. |

## Calibration

| Command | What it does |
|---|---|
| `sirius board [--out data/board.png]` | Writes the ChArUco board as a PNG and a true-size PDF for printing. |
| `sirius calib-capture --out DIR [--pairs 30]` | Shows both cameras and saves a pair each time the board is seen by both in a new position. Press `q` to stop early. |
| `sirius calibrate DIR [--out FILE]` | Calibrates from the captured pairs, prints the reprojection error and the measured baseline, and saves `calib.npz`. |
| `sirius baseline-check` | Compares the calibrated baseline with the ruler measurement in the config (must be within 2%) and checks that live rectified images line up row by row (median vertical offset under 1 px). |

## Depth bake-off

| Command | What it does |
|---|---|
| `sirius target [--out data/target.png]` | Writes the ArUco target (145 mm marker) as PNG and PDF. |
| `sirius bakeoff-capture --distance M [--tag NAME] [--seconds 2]` | Records the target placed at a taped distance into `data/bakeoff/`. |
| `sirius bakeoff-score` | Runs every depth method on every capture, writes `docs/m1-depth-bakeoff.md`, and sets `depth_method` in the config if a stereo method meets the targets. Stops and says so if none does. |

## Running it

`sirius view` runs the full pipeline and serves the dashboard.

| Option | Effect |
|---|---|
| `--depth sgbm\|ffs\|mono\|none` | Depth method. Defaults to the config's `depth_method` once calibrated, and to `mono` before that. |
| `--speak` | Speaks alerts through the Windows voice. Without it, alerts appear on the dashboard only. |
| `--log` | Writes one JSON line per frame to `data/runs/<timestamp>/log.jsonl`. |
| `--replay DIR` | Plays a recorded clip instead of the live cameras. |
| `--no-detect` | Turns off object detection. |
| `--port 8765` | Dashboard port. It only listens on 127.0.0.1. |
| `--no-browser` | Does not open the browser. |
| `--seconds N` | Stops after N seconds. |
| `--snapshot FILE` | On exit, saves the last frame of all four panels as one image. |
