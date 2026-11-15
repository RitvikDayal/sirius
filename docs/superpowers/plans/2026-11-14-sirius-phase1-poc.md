# SIRIUS Phase 1 POC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A laptop POC that takes two webcams on a fixed rig, measures distance by stereo, recognises objects, and speaks short proximity alerts ("person, one metre, ahead").

**Architecture:** A pipeline of swappable modules — stereo source → pairer → rectifier → depth estimator ∥ detector → fusion → tracker → alert policy → voice — wired by `sirius run` from a TOML config. M1 runs a depth bake-off (SGBM vs Fast-FoundationStereo vs monocular) on this rig and its result sets the default depth module; later tasks only use the `DepthEstimator` interface.

**Tech Stack:** Python 3.11, uv, OpenCV (contrib, for ArUco/ChArUco), NumPy, PyTorch cu128, transformers (D-FINE, Depth Anything V2 metric), onnxruntime-gpu (Fast-FoundationStereo ONNX), supervision (ByteTrack), pywin32 (SAPI voice), pytest.

**Spec:** the approved Phase 1 design (2026-11-14), kept in the author's notes. Its content is summarised in `docs/overview.md`.

## Global Constraints

- Windows 11, RTX 5090 Laptop (sm_120): torch/torchvision from the `https://download.pytorch.org/whl/cu128` index, as in `Projects/Personal/emit-or-detect/pyproject.toml`.
- `requires-python = ">=3.11,<3.12"`; managed with `uv`; tests with `uv run pytest`.
- Capture: 1280×720 MJPEG @ 30 FPS per camera; cameras bound by DirectShow device path, never by index alone.
- Rig (measured 2026-11-14): left camera = path containing `6&1ec6b2f7` (USB port 7), right = `6&315a9f63` (port 8). Lenses differ by ~4° pitch, ~2.2° roll — corrected by calibration only.
- **Only stereo depth may produce a spoken distance.** Monocular depth is benchmark-only in Phase 1.
- **No spoken number without valid depth:** both cameras fresh (newest frame age ≤ 200 ms, mean luma ≥ 10) and ≥ 50% valid pixels in the object's sampled region; else the alert omits the distance.
- Distance = straight-line range from the midpoint between the lenses to the object surface, metres.
- Zones: urgent < 1.0 m, near 1.0–2.5 m, aware 2.5–5.0 m, beyond 5.0 m silent. Direction: left < −15°, ahead −15°..15°, right > 15° (bearing from the rig midpoint).
- Spoken distance words: < 0.75 m "half a metre"; < 1.5 m "one metre"; < 2.5 m "two metres"; < 3.5 m "three metres"; < 4.5 m "four metres"; else "five metres".
- Re-announce a track only on zone change or after 5 s; an urgent alert interrupts speech in progress; an alert older than 1.0 s (from its frame's capture time) or whose object left its zone is dropped, never spoken late.
- Announced classes (COCO names): person, chair, couch, bed, dining table, bench, bicycle, car, motorcycle, dog, potted plant, tv, laptop, backpack, suitcase, bottle, cup.
- Licences: no AGPL/GPL dependencies. D-FINE (Apache-2.0) via `ustc-community/dfine-small-coco`. Fast-FoundationStereo weights from `nvidia/c-fast-foundationstereo` (NVIDIA Open Model Agreement — note in README).
- Data (calibration captures, recordings, bake-off captures, model downloads) lives under `data/` and is gitignored. Nothing calls a network service at runtime once models are cached.
- Commits: Claude stages explicit paths and hands Ritvik the `git commit` command; Claude never commits. Branch `feat/phase1-poc`. No `Co-Authored-By` trailers.

## Review Focus

1. **A camera unplugs or freezes mid-run** → no crash; distances stop within 200 ms; alerts continue without numbers; capture recovers on replug. (Task 2 grabber reopen test, Task 10 freshness test, Task 12 live check.)
2. **Left and right swap after a replug** (both cameras report the same name) → `sirius check` and `sirius run` refuse to start, naming the swap. (Task 2 identity check.)
3. **Object closer than the stereo search range (< ~0.45 m)** → never reported as far; invalid region → no number. (Task 5 test `test_too_close_is_invalid`.)
4. **Many objects in view** → one alert at a time, most urgent first; the queue never holds stale alerts. (Task 11 tests.)
5. **Dim light flips one board to IR/greyscale** → warning logged when the two cameras' mean saturation differs by > 3× ; depth not trusted. (Task 2 health test.)

## Human steps (Ritvik) — marked 👤 in tasks

- Task 4: print the ChArUco board at 100%, measure one square to 0.1 mm; measure the lens centre-to-centre spacing to 1 mm; move the board in front of the rig during capture.
- Task 8: print the ArUco target, place it at taped distances 0.5 / 1 / 2 / 3 / 5 m.
- Task 13: seated scripted test placements; supervised walk is deferred (spec: mount decided after M2).

---

### Task 1: Repo scaffold, config, device enumeration

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `README.md`, `config/rig.toml`, `src/sirius/__init__.py`, `src/sirius/config.py`, `src/sirius/devices.py`, `src/sirius/cli.py`
- Test: `tests/test_devices.py`, `tests/test_config.py`, `tests/fixtures/ffmpeg_list_devices.txt`

**Interfaces:**
- Produces:
  - `DeviceInfo(name: str, path: str, index: int)` (frozen dataclass); `index` = position among DirectShow *video* devices, which is OpenCV's `CAP_DSHOW` index.
  - `parse_dshow_list(text: str) -> list[DeviceInfo]`; `list_video_devices() -> list[DeviceInfo]` (runs `ffmpeg -hide_banner -list_devices true -f dshow -i dummy`).
  - `resolve(path_fragment: str, devices: list[DeviceInfo]) -> DeviceInfo` — raises `DeviceNotFound` (zero matches) or `AmbiguousDevice` (>1).
  - `RigConfig` dataclass loaded by `load_config(path: Path) -> RigConfig` with fields: `left_path: str`, `right_path: str`, `width: int = 1280`, `height: int = 720`, `fps: int = 30`, `baseline_mm_measured: float | None`, `charuco: CharucoSpec(cols=7, rows=5, square_mm: float, marker_mm: float, dictionary="DICT_5X5_100")`, `depth_method: str = "sgbm"`, `depth_scale: float = 0.5`.
  - CLI entry point `sirius` (`[project.scripts] sirius = "sirius.cli:main"`), subcommand `sirius devices`.

- [ ] **Step 1:** Save the real output of `ffmpeg -hide_banner -list_devices true -f dshow -i dummy` (captured 2026-11-14: Integrated Camera, two "USB Camera", a virtual camera, four audio devices) to `tests/fixtures/ffmpeg_list_devices.txt`.
- [ ] **Step 2: Write failing tests**
  - `test_parse_real_listing`: parsing the fixture gives exactly 4 video devices; indices 0..3 in order; the two "USB Camera" entries have paths containing `6&315a9f63` (index 1) and `6&1ec6b2f7` (index 2); audio devices excluded.
  - `test_resolve_fragment`: `resolve("6&1ec6b2f7", devs).index == 2`; `resolve("USB Camera", devs)` raises `AmbiguousDevice`; `resolve("nope", devs)` raises `DeviceNotFound`.
  - `test_load_config_defaults`: a minimal TOML with only the two paths and charuco square/marker loads with `fps == 30`, `depth_method == "sgbm"`.
- [ ] **Step 3:** Run `uv run pytest tests/test_devices.py tests/test_config.py -v` → FAIL (module missing).
- [ ] **Step 4:** Implement. `pyproject.toml`: hatchling, `packages = ["src/sirius"]`, deps `numpy`, `opencv-contrib-python`, `tomli-w`; dev group `pytest`. Heavier deps are added by the tasks that need them. `.gitignore`: `data/`, `.venv/`, `__pycache__/`, `*.onnx`, `*.pth`. `README.md` states up front: research prototype, not a safety device, supplements a cane. `config/rig.toml` with the two real path fragments, `square_mm`/`marker_mm` = 35.0/26.0 placeholders marked `# 👤 measure`.
- [ ] **Step 5:** Run tests → PASS. Run `uv run sirius devices` on the box → prints both USB cameras with indices 1 and 2 (or whatever the live order is), and marks which is left/right per config.
- [ ] **Step 6:** Stage the files; hand Ritvik: `git commit -m "Scaffold sirius: config, DirectShow device enumeration"`.

### Task 2: Capture, pairing, health, `sirius check`

**Files:**
- Create: `src/sirius/capture.py`, `src/sirius/pairing.py`, `src/sirius/source.py`, `src/sirius/health.py`, `src/sirius/identity.py`
- Modify: `src/sirius/cli.py` (add `check`)
- Test: `tests/test_pairing.py`, `tests/test_health.py`, `tests/test_identity.py`

**Interfaces:**
- Consumes: `DeviceInfo`, `resolve`, `RigConfig`.
- Produces:
  - `Frame(image: np.ndarray, t_ns: int, seq: int)`; `StereoPair(left: Frame, right: Frame)` with properties `skew_ns: int` (abs difference) and `t_ns: int` (max of the two).
  - `CameraGrabber(device: DeviceInfo, width, height, fps)` — thread; opens `cv2.VideoCapture(index, cv2.CAP_DSHOW)` with FOURCC `MJPG`, size, fps, `CAP_PROP_BUFFERSIZE=1`; retries open up to 5 times with 1 s gaps; on read failure for > 1 s, releases and reopens. `latest() -> Frame | None`, `fps() -> float` (rolling 2 s), `stop()`. `t_ns` = `time.perf_counter_ns()` when `read()` returns.
  - `pair_latest(left: Frame | None, right: Frame | None, max_skew_ns: int, last_pair_seq: tuple[int,int] | None) -> StereoPair | None` — returns `None` if either missing, skew > max, or the same seq pair was already emitted.
  - `StereoSource` protocol: `start()`, `stop()`, `read(timeout_s: float) -> StereoPair | None`, `health() -> SourceHealth`. `LiveStereoSource(cfg: RigConfig)` implements it with two grabbers and `max_skew_ns = 1e9 / fps`.
  - `SourceHealth(fps_left, fps_right, age_ms_left, age_ms_right, luma_left, luma_right, sat_left, sat_right)`; `health.is_fresh(h: SourceHealth) -> bool` (both ages ≤ 200, both luma ≥ 10); `health.ir_mismatch(h) -> bool` (max(sat)/max(min(sat),0.1) > 3).
  - `identity.check_left_right(left_img, right_img) -> IdentityResult(ok: bool, median_dx: float, median_dy: float, matches: int)` — ORB (4000 features) + cross-check BF + RANSAC homography; `ok` iff `matches ≥ 50` and `median_dx` (right-to-left content shift, `x_left − x_right`) > 0.
- [ ] **Step 1: Failing tests**
  - `test_pair_rejects_skew`: frames at t=0 and t=40 ms with max 33 ms → `None`; at t=0 and t=20 ms → pair with `skew_ns == 20_000_000`.
  - `test_pair_no_duplicates`: same seqs as `last_pair_seq` → `None`.
  - `test_freshness`: age 250 ms on one side → `is_fresh` False; luma 5 → False; ages 30/30, luma 120/110 → True.
  - `test_ir_mismatch`: sat 8.0 vs 1.5 → True; 8.0 vs 7.5 → False.
  - `test_identity_detects_swap`: build a textured image, crop two views 60 px apart horizontally to simulate left/right → `ok` True; swap arguments → `ok` False with `median_dx < 0`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement as specified.
- [ ] **Step 4:** Run tests → PASS.
- [ ] **Step 5:** `sirius check [--seconds 10]`: starts the live source, prints per-camera FPS, skew p50/p90 (ms), luma, saturation, then runs `check_left_right` on one pair. Exits non-zero if either FPS < 28, skew p90 > 33 ms, or identity not ok (message names the swap).
- [ ] **Step 6 (hardware):** Run `uv run sirius check --seconds 10` → both FPS ≥ 28, skew p90 ≤ 33 ms, identity ok with `median_dx > 0`. Then swap `left_path`/`right_path` in a temp config and run `uv run sirius check --config <tmp>` → exits non-zero naming the swap (forces the check red).
- [ ] **Step 7 (hardware, Review Focus 1):** During a 30 s `sirius check --seconds 30`, Ritvik unplugs the right camera for ~5 s and replugs → no crash; that camera's FPS drops to 0 then recovers; final exit code reflects the gap (FPS < 28 averaged is acceptable, a traceback is not).
- [ ] **Step 8:** Stage; hand Ritvik: `git commit -m "Add threaded capture, timestamp pairing, health and left/right identity check"`.

### Task 3: Recorder and replay source

**Files:**
- Create: `src/sirius/recorder.py`, `src/sirius/replay.py`
- Modify: `src/sirius/cli.py` (add `record`)
- Test: `tests/test_replay.py`

**Interfaces:**
- Consumes: `StereoSource`, `StereoPair`, `Frame`.
- Produces:
  - `record(source: StereoSource, out_dir: Path, seconds: float) -> int` (pairs written). Layout: `left/000000.png`, `right/000000.png` (PNG — lossless, per FFS guidance), `pairs.csv` with `idx,t_left_ns,t_right_ns`.
  - `ReplayStereoSource(clip_dir: Path, realtime: bool = True)` implementing `StereoSource`; with `realtime=True`, `read()` sleeps to reproduce the original inter-pair timing; frames keep their recorded `t_ns` offsets rebased to `perf_counter_ns()` at `start()` (so latency math works on replays).
- [ ] **Step 1: Failing test** `test_roundtrip`: write 5 synthetic pairs with known timestamps via `record()` over a fake source, replay with `realtime=False` → 5 pairs, identical pixels, `t_ns` differences preserved exactly.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5 (hardware):** `uv run sirius record --seconds 5 --out data/clips/smoke` → ~150 pairs; `pairs.csv` skew column p90 ≤ 33 ms.
- [ ] **Step 6:** Stage; hand Ritvik: `git commit -m "Add stereo clip recorder and replay source"`.

### Task 4: ChArUco calibration and rectification

**Files:**
- Create: `src/sirius/calib/__init__.py`, `src/sirius/calib/board.py`, `src/sirius/calib/stereo.py`, `src/sirius/calib/rectify.py`
- Modify: `src/sirius/cli.py` (add `board`, `calib-capture`, `calibrate`, `baseline-check`)
- Test: `tests/test_calibration.py`

**Interfaces:**
- Consumes: `RigConfig.charuco`, `StereoSource`, `identity.check_left_right` (reused for the rectified-residual measure).
- Produces:
  - `make_board(spec: CharucoSpec) -> cv2.aruco.CharucoBoard`; `render_board_png(spec, path: Path, dpi=300)`.
  - `detect(board, gray) -> CharucoDetection(corners: np.ndarray Nx1x2, ids: np.ndarray Nx1)` using `cv2.aruco.CharucoDetector`.
  - `Calibration` dataclass: `K1, D1, K2, D2, R, T, R1, R2, P1, P2, Q, size: tuple[int,int], rms_left, rms_right, rms_stereo: float`; property `baseline_m = float(np.linalg.norm(T))` (T in metres — square size passed in metres); `save(path)` / `Calibration.load(path)` as `.npz`.
  - `calibrate(pairs: list[tuple[np.ndarray, np.ndarray]], board, size) -> Calibration` — per-camera `cv2.calibrateCamera` on matched ChArUco corners (`board.matchImagePoints`), then `cv2.stereoCalibrate` with `CALIB_FIX_INTRINSIC` using only corner IDs seen in both views, then `cv2.stereoRectify(alpha=0)`.
  - `RectifiedPair(left: np.ndarray, right: np.ndarray, t_ns: int, fx: float, fy: float, cx: float, cy: float, baseline_m: float)`.
  - `Rectifier(calib: Calibration, scale: float)` — precomputes `initUndistortRectifyMap` (CV_16SC2) at full size; `rectify(pair: StereoPair) -> RectifiedPair` remaps with `INTER_LINEAR` then resizes by `scale`; intrinsics scaled accordingly (from `P1`).
- [ ] **Step 1: Failing tests**
  - `test_synthetic_stereo_calibration`: render the board, project it into two virtual pinhole cameras (fx = fy = 914, 1280×720, baseline 0.117 m, right camera pitched 4° and rolled 2.2° relative to left) at 25 random board poses 0.5–1.5 m away; `calibrate()` → `abs(baseline_m − 0.117) / 0.117 < 0.01`, `rms_stereo < 0.5`.
  - `test_rectified_rows_align`: after `Rectifier(calib, 1.0)`, project 50 random 3D points visible to both cameras, map through rectification → median |y_left − y_right| < 0.5 px.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** `sirius board --out data/board.png` → 👤 Ritvik prints at 100% on A4, glues to card, measures one square with a ruler to 0.1 mm, and the marker; writes both into `config/rig.toml`. 👤 Measures lens centre-to-centre spacing to 1 mm → `baseline_mm_measured`.
- [ ] **Step 6:** `sirius calib-capture --out data/calib/<date>`: live view; auto-saves a pair when ≥ 20 common corners are detected in both views and the board pose differs from every saved pose (corner-centroid moved > 80 px or board area changed > 20%); stops at 30 pairs. 👤 Ritvik moves the board through near/far, left/right, tilted.
- [ ] **Step 7:** `sirius calibrate data/calib/<date> --out data/calib/<date>/calib.npz` prints rms values and `baseline_m`.
- [ ] **Step 8 (verification marker):** `sirius baseline-check` → PASS iff `|baseline_m×1000 − baseline_mm_measured| / baseline_mm_measured ≤ 0.02` **and** median |dy| between rectified live views (ORB matches) < 1.0 px (before calibration it was 62 px). Print both numbers.
- [ ] **Step 9:** Stage code only (not `data/`); hand Ritvik: `git commit -m "Add ChArUco stereo calibration, rectification and baseline check"`.

### Task 5: Depth interface, geometry, SGBM

**Files:**
- Create: `src/sirius/depth/__init__.py`, `src/sirius/depth/base.py`, `src/sirius/depth/geometry.py`, `src/sirius/depth/sgbm.py`
- Test: `tests/test_depth_geometry.py`, `tests/test_sgbm.py`

**Interfaces:**
- Consumes: `RectifiedPair`.
- Produces:
  - `DepthResult(range_m: np.ndarray  # float32 HxW, NaN = invalid, latency_ms: float, method: str)`.
  - `DepthEstimator` protocol: `name: str`, `kind: Literal["stereo", "mono"]`, `estimate(rp: RectifiedPair) -> DepthResult`.
  - `geometry.depth_from_disparity(disp: np.ndarray, fx: float, baseline_m: float) -> np.ndarray` (Z; disp ≤ 0 → NaN).
  - `geometry.range_from_z(z: np.ndarray, fx, fy, cx, cy, baseline_m) -> np.ndarray` — X = (u−cx)Z/fx, Y = (v−cy)Z/fy, range = ‖(X − B/2, Y, Z)‖ (midpoint origin; left-rectified frame).
  - `geometry.bearing_deg(u: float, z: float, fx, cx, baseline_m) -> float` — atan2(X − B/2, Z) in degrees, positive = right.
  - `SgbmEstimator(num_disparities=128, block_size=5)` — `StereoSGBM_create(minDisparity=0, numDisparities=128, blockSize=5, P1=8*3*25, P2=32*3*25, disp12MaxDiff=1, uniquenessRatio=10, speckleWindowSize=100, speckleRange=2, mode=STEREO_SGBM_MODE_SGBM_3WAY)`; disparity /16; ≤ 0 or invalid → NaN; latency measured with `perf_counter`.
- [ ] **Step 1: Failing tests**
  - `test_range_on_axis`: z = 2.0 at the principal point with B = 0.12 → range = √(0.06² + 2²).
  - `test_bearing_signs`: point right of centre → positive; left → negative.
  - `test_sgbm_plane`: random-texture image; right view = left shifted by 40 px (fronto-parallel plane); fx = 457, B = 0.117 → median range over the valid centre region within 2% of fx·B/40 = 1.337 m (range ≈ Z near axis).
  - `test_too_close_is_invalid` (Review Focus 3): shift 200 px (> 128 search range) → ≥ 80% of the centre region is NaN, and no valid pixel reports a range > 1.0 m.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Stage; hand Ritvik: `git commit -m "Add depth interface, stereo geometry and SGBM estimator"`.

### Task 6: Fast-FoundationStereo (ONNX)

**Files:**
- Create: `src/sirius/depth/ffs.py`, `scripts/fetch_models.py`
- Test: `tests/test_ffs.py` (marked `@pytest.mark.gpu`, skipped when the ONNX file or CUDA EP is absent — and the skip reason printed)

**Interfaces:**
- Consumes: `DepthEstimator`, `RectifiedPair`, `geometry.depth_from_disparity`, `geometry.range_from_z`.
- Produces: `FfsEstimator(onnx_path: Path, input_hw: tuple[int,int] = (384, 640))` with `name = "ffs"`, `kind = "stereo"`.
- [ ] **Step 1:** Add deps `onnxruntime-gpu`, `huggingface_hub`. `scripts/fetch_models.py` downloads `nvidia/c-fast-foundationstereo` file `onnx/c_fast_foundationstereo_bp2_dynbatch_dynhw.onnx` (+ `cfg.yaml`) into `data/models/ffs/`.
- [ ] **Step 2:** Inspect the model: print `get_inputs()` / `get_outputs()` names, shapes, dtypes; record them as constants at the top of `ffs.py` with a comment citing the inspection. Confirm `CUDAExecutionProvider` is active (`session.get_providers()[0]`). **Timebox: if CUDA EP will not load on sm_120 after trying the latest `onnxruntime-gpu` and the cu12 CUDA/cuDNN wheels, stop this task, record the error in `docs/m1-depth-bakeoff.md`, and the bake-off runs with SGBM + mono only.**
- [ ] **Step 3: Failing test** `test_ffs_plane`: same synthetic 40 px plane as Task 5 at 640×384 → median range within 5% of 1.337 m over the centre.
- [ ] **Step 4:** Implement: RGB, input padded/resized to `input_hw` (multiples of 32), output disparity scaled back to the rectified image width; invalid where disparity ≤ 0 or outside the left-right overlap (columns < max disparity on the left edge set NaN).
- [ ] **Step 5:** Run → PASS. Print latency median/p90 over 50 runs after 10 warm-ups.
- [ ] **Step 6:** Stage (not `data/`); hand Ritvik: `git commit -m "Add Fast-FoundationStereo ONNX depth estimator"`.

### Task 7: Monocular metric depth (benchmark only)

**Files:**
- Create: `src/sirius/depth/mono.py`
- Test: `tests/test_mono.py` (`@pytest.mark.gpu`)

**Interfaces:**
- Produces: `MonoEstimator(model_id="depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf")`, `name = "mono-dav2-indoor-s"`, `kind = "mono"`; uses the left rectified image only; `predicted_depth` (metres, Z) resized to the image, then `range_from_z`.
- [ ] **Step 1:** Add deps `torch`, `torchvision` (cu128 index, explicit), `transformers`.
- [ ] **Step 2: Failing test** `test_mono_shapes_and_units`: a real frame from `data/clips/smoke` → result shape equals input, finite fraction > 0.95, median range between 0.3 and 20.
- [ ] **Step 3:** Implement. **Step 4:** Run → PASS. Print latency median/p90.
- [ ] **Step 5:** Stage; hand Ritvik: `git commit -m "Add monocular metric depth estimator for the bake-off"`.

### Task 8: Depth bake-off (M1 gate)

**Files:**
- Create: `src/sirius/eval/__init__.py`, `src/sirius/eval/bakeoff.py`
- Modify: `src/sirius/cli.py` (add `target`, `bakeoff-capture`, `bakeoff-score`)
- Test: `tests/test_bakeoff.py`
- Output: `docs/m1-depth-bakeoff.md`

**Interfaces:**
- Consumes: all `DepthEstimator`s, `Rectifier`, `ReplayStereoSource`.
- Produces:
  - Target: ArUco `DICT_4X4_50` id 7, 160 mm side (`sirius target --out data/target.png`). The spec's "flat target + a person" is split: the flat marker here (automatic region, no detector needed yet); the person measured through the full pipeline in Task 13.
  - `score_capture(rp: RectifiedPair, est: DepthEstimator, true_range_m: float) -> Score(method, true_m, est_m: float | None, err_pct: float | None, valid_frac: float, latency_ms: float)` — finds the marker in the rectified left image, samples the central 60% of the marker quad, `est_m` = median of valid range, `None` if valid fraction < 0.5.
  - `summarise(scores: list[Score]) -> str` — markdown table: rows = distance, columns = method (err % and valid frac), plus latency median/p90 per method.
  - `choose_default(scores) -> str | None` — among `kind == "stereo"` methods with p90 latency ≤ 100 ms, the one with the smallest worst-case error that meets ≤ 10% at 0.5–3 m and ≤ 20% at 5 m; `None` if none qualifies.
- [ ] **Step 1: Failing tests**
  - `test_score_on_synthetic`: render the target onto a fronto-parallel textured plane at a known disparity → SGBM `err_pct < 3`.
  - `test_choose_default_rules`: mono never chosen even if most accurate; a stereo method with p90 150 ms excluded; none passing → `None`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5 (👤 + hardware):** Ritvik places the target at 0.5, 1, 2, 3, 5 m (taped from the lens midpoint, target facing the rig, centred and then ~25° to one side at 2 m). For each: `sirius bakeoff-capture --distance <m> [--tag side]` saves 30 rectified pairs.
- [ ] **Step 6:** `sirius bakeoff-score` runs every available estimator on every capture, writes `docs/m1-depth-bakeoff.md` with the table, the reproducibility block (versions of torch/onnxruntime/opencv, GPU, driver, resolution, calibration file hash, baseline measured vs calibrated) and the chosen default; writes `depth_method` into `config/rig.toml`.
- [ ] **Step 7 (gate):** If `choose_default` returns `None`, **stop** and report the table to Ritvik with the likely cause; do not relax targets. Otherwise continue.
- [ ] **Step 8:** Stage code + `docs/m1-depth-bakeoff.md`; hand Ritvik: `git commit -m "Add depth bake-off and record M1 results"`.

### Task 9: Detector

**Files:**
- Create: `src/sirius/detect.py`
- Test: `tests/test_detect.py`

**Interfaces:**
- Produces: `Detection(box: tuple[float, float, float, float]  # xyxy pixels in the rectified left image, label: str, score: float)`; `Detector` protocol `detect(image_bgr) -> list[Detection]`; `DFineDetector(model_id="ustc-community/dfine-small-coco", threshold=0.5, classes=ANNOUNCED_CLASSES)` (transformers `AutoModelForObjectDetection` + `post_process_object_detection`), fp16 on CUDA; filters to the announced class list in Global Constraints.
- [ ] **Step 1: Failing tests** `test_filters_classes` (fake model output with "person" and "toothbrush" → only person kept); `test_real_frame` (`@pytest.mark.gpu`): a recorded frame containing Ritvik → ≥ 1 `person` with score ≥ 0.5.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS; print latency median/p90 at the rectified size.
- [ ] **Step 5:** Stage; hand Ritvik: `git commit -m "Add D-FINE detector limited to announced classes"`.

### Task 10: Fusion and tracking

**Files:**
- Create: `src/sirius/fusion.py`, `src/sirius/track.py`
- Test: `tests/test_fusion.py`, `tests/test_track.py`

**Interfaces:**
- Consumes: `Detection`, `DepthResult`, `RectifiedPair`, `SourceHealth`, `health.is_fresh`, `geometry.bearing_deg`.
- Produces:
  - `object_range(det: Detection, depth: DepthResult) -> float | None` — median of `range_m` over the box's central region (inner 50% width × 50% height); `None` if < 50% of that region is valid.
  - `TrackedObject(track_id: int, label: str, box, range_m: float | None, bearing_deg: float, frame_t_ns: int, zone: str | None)`.
  - `Tracker()` wrapping `supervision.ByteTrack`; `update(dets: list[Detection], depth: DepthResult | None, rp: RectifiedPair, fresh: bool) -> list[TrackedObject]`. Range smoothed per track with EMA α = 0.4; **when `fresh` is False or `depth` is None, every object's `range_m` is None** (smoothing state cleared). Bearing uses smoothed range (or 2.0 m nominal when range is None, for direction only).
  - `zone_of(range_m: float | None) -> str | None` — "urgent" / "near" / "aware" / None (beyond 5 m or unknown).
- [ ] **Step 1: Failing tests**
  - `test_range_median_ignores_edges`: depth map with background 4.0 m and a 1.0 m object filling the box centre → 1.0.
  - `test_insufficient_valid_is_none`: 60% NaN in the central region → None.
  - `test_not_fresh_suppresses_ranges` (spec criterion 5): `fresh=False` → all `range_m is None` even with a perfect depth map.
  - `test_track_ids_stable`: the same box moving 5 px per frame over 10 frames keeps one `track_id`.
  - `test_zones`: 0.8 → urgent, 1.0 → near, 2.6 → aware, 5.1 → None.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement (add dep `supervision`). **Step 4:** Run → PASS.
- [ ] **Step 5:** Stage; hand Ritvik: `git commit -m "Add depth-detection fusion and ByteTrack tracking"`.

### Task 11: Alert policy

**Files:**
- Create: `src/sirius/alerts.py`
- Test: `tests/test_alerts.py`

**Interfaces:**
- Consumes: `TrackedObject`, `zone_of`.
- Produces:
  - `Alert(text: str, urgent: bool, track_id: int, zone: str | None, frame_t_ns: int)`.
  - `phrase(obj: TrackedObject) -> str` — `"{label}, {distance words}, {direction}"`; without range: `"{label}, {direction}"`. Labels spoken as plain words ("dining table" → "table", "tv" → "TV", "potted plant" → "plant").
  - `AlertPolicy(repeat_s=5.0, max_age_s=1.0)`; `update(objs: list[TrackedObject], now_ns: int) -> Alert | None` — returns at most one alert: the highest-priority object that is new, changed zone, or last announced ≥ 5 s ago. Priority: urgent > near > aware > no-range; ties → smaller range, then closer to ahead. Objects with zone None and a valid range (beyond 5 m) are never announced. Objects with no range are announced at most once per track (direction only).
  - `is_stale(alert: Alert, objs_now: list[TrackedObject], now_ns: int) -> bool` — older than 1.0 s from `frame_t_ns`, or its track is gone or in a different zone.
- [ ] **Step 1: Failing tests**
  - `test_phrase`: person 0.9 m at bearing 0 → "person, one metre, ahead"; chair 2.2 m at −30° → "chair, two metres, left"; bottle range None at 20° → "bottle, right".
  - `test_one_alert_most_urgent` (Review Focus 4): five objects, one urgent → only that one returned.
  - `test_no_repeat_within_5s`, `test_repeat_on_zone_change`, `test_repeat_after_5s`.
  - `test_beyond_5m_silent`.
  - `test_stale_dropped`: alert frame 1.2 s old → stale; track gone → stale.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Stage; hand Ritvik: `git commit -m "Add alert policy: zones, priority, rate limit, staleness"`.

### Task 12: Voice, pipeline runner, debug view

**Files:**
- Create: `src/sirius/voice.py`, `src/sirius/pipeline.py`, `src/sirius/viewer.py`
- Modify: `src/sirius/cli.py` (add `run`, `tts-latency`)
- Test: `tests/test_pipeline.py`, `tests/test_voice.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `Voice` protocol: `say(text: str, interrupt: bool) -> int` (returns `perf_counter_ns()` at the call), `busy() -> bool`. `SapiVoice` via `win32com.client.Dispatch("SAPI.SpVoice")`: flags `SVSFlagsAsync (1)`, plus `SVSFPurgeBeforeSpeak (2)` when `interrupt`; `busy()` = `Status.RunningState == 2`. `RecordingVoice` (tests) stores `(text, interrupt, t_ns)`.
  - `measure_tts_start_ms(voice: SapiVoice, n=10) -> tuple[float, float]` — median/p90 from `say()` to `RunningState == 2`, polled every 1 ms.
  - `Pipeline(source, rectifier, depth, detector, tracker, policy, voice, viewer | None)`; `step() -> StepLog | None`; depth and detection run concurrently (two worker threads, each on its own CUDA stream for torch models); `StepLog(frame_t_ns, depth_ms, detect_ms, total_ms, alert_text: str | None, speak_t_ns: int | None, fresh: bool)` appended as JSON lines to `data/runs/<ts>/log.jsonl`.
  - Speaking rule: say an alert if voice idle; if busy, say it only if urgent (interrupt) — otherwise hold it as the single pending alert, replaced by any newer alert, discarded when `is_stale`.
  - `Viewer`: one window — rectified left with boxes, labels and range; depth colormap (TURBO, 0.3–6 m); status line with FPS L/R, skew, fresh/IR flags, last latency. `--snapshot <path>` writes the composite of the current frame.
- [ ] **Step 1: Failing tests** (fake source/depth/detector + `RecordingVoice`)
  - `test_urgent_interrupts`: voice busy, urgent alert arrives → `say(..., interrupt=True)`.
  - `test_pending_replaced_and_stale_dropped`: two non-urgent alerts while busy → only the newer is spoken when idle; one older than 1 s is never spoken.
  - `test_black_frame_no_numbers` (criterion 5): right frames all black → every spoken text has no distance words.
  - `test_replay_end_to_end`: replaying `data/clips/smoke` through the real SGBM + detector produces a log with `total_ms` recorded for every pair and at least one `person` alert (`@pytest.mark.gpu`).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement (add dep `pywin32`). **Step 4:** Run → PASS.
- [ ] **Step 5 (hardware):** `uv run sirius tts-latency` prints median/p90 start delay. `uv run sirius run --snapshot data/runs/snap.png` with Ritvik in view → spoken "person, … metre(s), ahead"; snapshot shows box, range label, depth map, status line. Open the PNG to confirm (the render is the proof, not the log).
- [ ] **Step 6 (hardware, criterion 5):** while running, cover the right lens → spoken alerts lose their numbers within 1 s; uncover → numbers return.
- [ ] **Step 7:** Stage; hand Ritvik: `git commit -m "Add SAPI voice, concurrent pipeline runner and debug view"`.

### Task 13: Phase 1 acceptance runs and write-up

**Files:**
- Create: `src/sirius/eval/latency.py`, `src/sirius/eval/scripted.py`, `config/placements.toml`, `docs/phase1-results.md`
- Modify: `src/sirius/cli.py` (add `latency-eval`, `scripted-test`, `soak`)
- Test: `tests/test_eval.py`

**Interfaces:**
- Produces:
  - `latency_eval(clip_dir, reveal_idx: int, label: str) -> float` — replays a clip in real time; latency = (first alert for `label` speak time − reveal pair's capture time) + measured TTS start median.
  - `config/placements.toml`: 20 placements (object ∈ person/chair/bottle, true range ∈ {0.5, 1, 2, 3} m (+ 5 m for person/chair), direction ∈ left/ahead/right); scoring = first alert within 5 s matches label and zone (and direction).
  - `soak(seconds=600)` — pass iff no exception and p90 `total_ms` in the last minute ≤ 1.5 × the first minute's.
- [ ] **Step 1: Failing tests** `test_latency_math` (synthetic log → expected ms); `test_scripted_scoring` (log with label match but wrong zone → miss).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5 (👤 + hardware):** record 5 reveal clips (object uncovered in front of the rig), run `latency-eval` on each → criterion 2 (p90 ≤ 300 ms). Run `scripted-test` with Ritvik placing objects → criterion 3 (≥ 17/20). Run person/chair/bottle accuracy at 0.5–5 m through the full pipeline → criterion 1. Run `soak` → criterion 4. Cover-one-camera from Task 12 → criterion 5.
- [ ] **Step 6:** Write `docs/phase1-results.md`: each criterion with the measured number, pass/fail, the reproducibility block, and known gaps (thin/glass obstacles, dim light). Copy the summary into the vault project (`03-projects/sirius/development.md`).
- [ ] **Step 7:** Stage; hand Ritvik: `git commit -m "Add Phase 1 acceptance tooling and record results"`.
