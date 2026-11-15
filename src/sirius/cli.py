import argparse
import sys
from pathlib import Path

from sirius.config import DEFAULT_CONFIG, load_config
from sirius.devices import list_video_devices


def cmd_devices(args) -> int:
    cfg = load_config(args.config)
    for d in list_video_devices():
        role = ""
        if cfg.left_path.lower() in d.path.lower():
            role = "  <- left"
        elif cfg.right_path.lower() in d.path.lower():
            role = "  <- right"
        print(f"[{d.index}] {d.name}{role}\n     {d.path}")
    return 0


def cmd_check(args) -> int:
    import time

    import numpy as np

    from sirius.health import ir_mismatch
    from sirius.identity import check_left_right
    from sirius.source import LiveStereoSource

    src = LiveStereoSource(load_config(args.config))
    src.start()
    skews, fps_l, fps_r, last = [], [], [], None
    t_end = time.perf_counter() + args.seconds
    next_sample = time.perf_counter() + 2.0
    try:
        while time.perf_counter() < t_end:
            pair = src.read(timeout_s=0.5)
            if pair is not None:
                skews.append(pair.skew_ns / 1e6)
                last = pair
            if time.perf_counter() >= next_sample:
                fps_l.append(src.left.fps())
                fps_r.append(src.right.fps())
                next_sample += 2.0
        h = src.health()
    finally:
        src.stop()

    fl = float(np.mean(fps_l)) if fps_l else 0.0
    fr = float(np.mean(fps_r)) if fps_r else 0.0
    p50, p90 = (np.percentile(skews, [50, 90]) if skews else (float("nan"),) * 2)
    print(f"fps        left {fl:5.1f}   right {fr:5.1f}   (reopens L{src.left.reopens} R{src.right.reopens})")
    print(f"pairs      {len(skews)}   skew p50 {p50:.1f} ms   p90 {p90:.1f} ms")
    print(f"luma       left {h.luma_left:.0f}   right {h.luma_right:.0f}")
    print(f"saturation left {h.sat_left:.1f}   right {h.sat_right:.1f}" + ("   IR MISMATCH" if ir_mismatch(h) else ""))
    failures = []
    if fl < 24 or fr < 24:
        failures.append("a camera averaged under 24 FPS")
    elif fl < 28 or fr < 28:
        # These boards lengthen exposure in dim light: 40 ms frames = 25 FPS.
        print("WARN: under 28 FPS - likely auto-exposure in dim light; more light gives 30 FPS")
    if not skews or p90 > 33:
        failures.append("pair skew p90 over 33 ms")
    if last is None:
        failures.append("no stereo pair received")
    else:
        idr = check_left_right(last.left.image, last.right.image)
        print(f"identity   matches {idr.matches}   dx {idr.median_dx:+.1f} px   dy {idr.median_dy:+.1f} px")
        if idr.matches >= 50 and idr.median_dx <= 0:
            failures.append("LEFT AND RIGHT ARE SWAPPED: swap left_path/right_path in config or the USB plugs")
        elif not idr.ok:
            failures.append("left/right identity could not be confirmed (too few matches - point the rig at a textured scene)")
    for f in failures:
        print(f"FAIL: {f}")
    print("PASS" if not failures else "")
    return 1 if failures else 0


def cmd_record(args) -> int:
    from sirius.recorder import record
    from sirius.source import LiveStereoSource

    src = LiveStereoSource(load_config(args.config))
    src.start()
    try:
        n = record(src, args.out, args.seconds)
    finally:
        src.stop()
    print(f"wrote {n} pairs to {args.out}")
    return 0 if n else 1


def cmd_board(args) -> int:
    from sirius.calib.board import render_board_png

    spec = load_config(args.config).charuco
    args.out.parent.mkdir(parents=True, exist_ok=True)
    render_board_png(spec, args.out)
    print(f"wrote {args.out}: {spec.cols}x{spec.rows} squares of {spec.square_mm} mm. Print at 100% (no 'fit to page').")
    return 0


def cmd_calib_capture(args) -> int:
    from sirius.calib.board import make_board
    from sirius.calib.session import capture
    from sirius.source import LiveStereoSource

    cfg = load_config(args.config)
    src = LiveStereoSource(cfg)
    src.start()
    try:
        n = capture(src, make_board(cfg.charuco), args.out, args.pairs)
    finally:
        src.stop()
    print(f"saved {n} pairs to {args.out}")
    return 0 if n >= 15 else 1


def cmd_calibrate(args) -> int:
    from sirius.calib.board import make_board
    from sirius.calib.session import load_pairs
    from sirius.calib.stereo import calibrate

    cfg = load_config(args.config)
    pairs = load_pairs(args.calib_dir)
    h, w = pairs[0][0].shape[:2]
    c = calibrate(pairs, make_board(cfg.charuco), (w, h))
    out = args.out or args.calib_dir / "calib.npz"
    c.save(out)
    print(f"{len(pairs)} pairs  rms left {c.rms_left:.3f}  right {c.rms_right:.3f}  stereo {c.rms_stereo:.3f} px")
    print(f"baseline {c.baseline_m * 1000:.1f} mm  -> {out}")
    print(f"set in config/rig.toml: calibration = \"{Path(out).as_posix()}\"")
    return 0


def cmd_baseline_check(args) -> int:
    import numpy as np

    from sirius.calib.rectify import Rectifier
    from sirius.calib.stereo import Calibration
    from sirius.identity import match_points
    from sirius.source import LiveStereoSource

    cfg = load_config(args.config)
    if not cfg.calibration or cfg.baseline_mm_measured is None:
        print("FAIL: set calibration and baseline_mm_measured in config/rig.toml")
        return 1
    calib = Calibration.load(cfg.calibration)
    b_mm = calib.baseline_m * 1000
    err = abs(b_mm - cfg.baseline_mm_measured) / cfg.baseline_mm_measured
    print(f"baseline   calibrated {b_mm:.1f} mm   ruler {cfg.baseline_mm_measured:.1f} mm   error {err * 100:.2f}%")

    src = LiveStereoSource(cfg)
    src.start()
    try:
        pair = None
        for _ in range(20):
            pair = src.read(timeout_s=1.0) or pair
    finally:
        src.stop()
    if pair is None:
        print("FAIL: no stereo pair")
        return 1
    rp = Rectifier(calib, 1.0).rectify(pair)
    pl, pr = match_points(rp.left, rp.right)
    dy = float(np.median(np.abs(pl[:, 1] - pr[:, 1]))) if len(pl) else float("inf")
    print(f"rectified  {len(pl)} matches   median |dy| {dy:.2f} px   (unrectified rig: ~62 px)")
    ok = err <= 0.02 and dy < 1.0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


BAKEOFF_DIR = Path("data/bakeoff")


def cmd_target(args) -> int:
    import cv2
    from PIL import Image

    from sirius.eval.bakeoff import TARGET_MM, make_target

    img = make_target()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.out), img)
    # The marker is 6 of the image's 8 modules; size the PDF so the marker prints at TARGET_MM.
    dpi = img.shape[1] / (TARGET_MM * 8 / 6 / 25.4)
    Image.fromarray(img).save(args.out.with_suffix(".pdf"), resolution=dpi)
    print(f"wrote {args.out.with_suffix('.pdf')}: black square {TARGET_MM:.0f} mm. Print at 100%.")
    return 0


def cmd_bakeoff_capture(args) -> int:
    from sirius.recorder import record
    from sirius.source import LiveStereoSource

    name = f"{args.distance:.2f}m" + (f"_{args.tag}" if args.tag else "")
    out = BAKEOFF_DIR / name
    src = LiveStereoSource(load_config(args.config))
    src.start()
    try:
        n = record(src, out, args.seconds)
    finally:
        src.stop()
    print(f"captured {n} pairs at {args.distance} m -> {out}")
    return 0 if n else 1


def _depth_estimators():
    from sirius.depth.sgbm import SgbmEstimator

    ests = [SgbmEstimator()]
    onnx =Path("data/models/ffs/onnx/c_fast_foundationstereo_bp2_dynbatch_dynhw.onnx")
    if onnx.exists():
        from sirius.depth.ffs import FfsEstimator

        ests.append(FfsEstimator(onnx))
    else:
        print(f"skipping ffs: {onnx} missing (uv run python scripts/fetch_models.py)")
    from sirius.depth.mono import MonoEstimator

    ests.append(MonoEstimator())
    return ests


def cmd_bakeoff_score(args) -> int:
    import hashlib
    import platform

    import cv2
    import numpy as np
    import onnxruntime
    import torch

    from sirius.calib.rectify import Rectifier
    from sirius.calib.stereo import Calibration
    from sirius.config import set_config_value
    from sirius.eval.bakeoff import choose_default, find_target, score_capture, summarise
    from sirius.replay import ReplayStereoSource

    cfg = load_config(args.config)
    calib = Calibration.load(cfg.calibration)
    rect = Rectifier(calib, cfg.depth_scale)
    rect_full = Rectifier(calib, 1.0)  # the target is ~25 px wide at 5 m: find it at full resolution
    ests = _depth_estimators()
    scores = []
    for d in sorted(BAKEOFF_DIR.iterdir()):
        true_m = float(d.name.split("m")[0])
        src = ReplayStereoSource(d, realtime=False)
        src.start()
        while (pair := src.read(0.0)) is not None:
            rp = rect.rectify(pair)
            quad = find_target(rect_full.rectify(pair).left)
            quad = None if quad is None else quad * cfg.depth_scale
            scores.extend(score_capture(rp, e, true_m, quad) for e in ests)
        found = [s for s in scores if s.true_m == true_m and s.est_m is not None]
        print(f"{d.name}: {len(found)} scored estimates")
    default = choose_default(scores)
    calib_hash = hashlib.sha256(Path(cfg.calibration).read_bytes()).hexdigest()[:12]
    report = [
        "# M1 depth bake-off", "",
        "Median distance error per method and taped distance (target: <=10% to 3 m, <=20% at 5 m).", "",
        summarise(scores), "",
        f"**Default chosen:** `{default}`" if default else "**No stereo method met the targets. Stopped for a decision.**", "",
        "## Reproducibility", "", "```yaml",
        f"hardware: {torch.cuda.get_device_name(0)}, {platform.platform()}",
        f"framework_version: {{torch: {torch.__version__}, onnxruntime: {onnxruntime.__version__}, opencv: {cv2.__version__}, numpy: {np.__version__}}}",
        f"resolution: capture {cfg.width}x{cfg.height}, depth at scale {cfg.depth_scale}",
        f"calibration: {cfg.calibration} (sha256 {calib_hash}), rms stereo {calib.rms_stereo:.3f} px",
        f"baseline: calibrated {calib.baseline_m * 1000:.1f} mm, ruler {cfg.baseline_mm_measured} mm",
        f"captures: {', '.join(p.name for p in sorted(BAKEOFF_DIR.iterdir()))}",
        f"methods: {', '.join(e.name for e in ests)}",
        "```", "",
    ]
    out = Path("docs/m1-depth-bakeoff.md")
    out.write_text("\n".join(report), encoding="utf-8")
    print(summarise(scores))
    if default:
        set_config_value(args.config, "depth_method", default)
        print(f"default depth method -> {default} (written to {args.config})")
        return 0
    print("NO METHOD MET THE TARGETS - stopping for a decision")
    return 1


def cmd_view(args) -> int:
    from sirius.source import LiveStereoSource
    from sirius.viewer.live import run_view

    cfg = load_config(args.config)
    if args.replay:
        from sirius.replay import ReplayStereoSource

        source = ReplayStereoSource(args.replay, realtime=True)
    else:
        source = LiveStereoSource(cfg)
    detector = None
    if not args.no_detect:
        try:
            from sirius.detect import DFineDetector

            detector = DFineDetector()
        except ImportError:
            pass
    voice = None
    if args.speak:
        from sirius.voice import SapiVoice

        voice = SapiVoice()
    log = None
    if args.log:
        import datetime

        log = Path("data/runs") / datetime.datetime.now().strftime("%Y%m%d-%H%M%S") / "log.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
    run_view(cfg, source, args.depth, args.port, open_browser=not args.no_browser,
             snapshot=args.snapshot, seconds=args.seconds, detector=detector, voice=voice, log_path=log)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sirius")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("devices", help="list DirectShow video devices").set_defaults(fn=cmd_devices)
    c = sub.add_parser("check", help="verify both cameras: fps, pair skew, health, left/right identity")
    c.add_argument("--seconds", type=float, default=10.0)
    c.set_defaults(fn=cmd_check)
    r = sub.add_parser("record", help="record stereo pairs to a clip folder")
    r.add_argument("--seconds", type=float, default=5.0)
    r.add_argument("--out", type=Path, required=True)
    r.set_defaults(fn=cmd_record)
    b = sub.add_parser("board", help="write the ChArUco calibration board PNG for printing")
    b.add_argument("--out", type=Path, default=Path("data/board.png"))
    b.set_defaults(fn=cmd_board)
    cc = sub.add_parser("calib-capture", help="live capture of calibration pairs")
    cc.add_argument("--out", type=Path, required=True)
    cc.add_argument("--pairs", type=int, default=30)
    cc.set_defaults(fn=cmd_calib_capture)
    ca = sub.add_parser("calibrate", help="stereo-calibrate from captured pairs")
    ca.add_argument("calib_dir", type=Path)
    ca.add_argument("--out", type=Path)
    ca.set_defaults(fn=cmd_calibrate)
    sub.add_parser("baseline-check", help="verify calibration against the ruler and live rectification").set_defaults(fn=cmd_baseline_check)
    tg = sub.add_parser("target", help="write the ArUco bake-off target for printing")
    tg.add_argument("--out", type=Path, default=Path("data/target.png"))
    tg.set_defaults(fn=cmd_target)
    bc = sub.add_parser("bakeoff-capture", help="record the target at a taped distance")
    bc.add_argument("--distance", type=float, required=True)
    bc.add_argument("--tag", default="")
    bc.add_argument("--seconds", type=float, default=2.0)
    bc.set_defaults(fn=cmd_bakeoff_capture)
    sub.add_parser("bakeoff-score", help="score every depth method on the captures").set_defaults(fn=cmd_bakeoff_score)
    v = sub.add_parser("view", help="live browser dashboard: cameras, depth, objects, 3D view")
    v.add_argument("--depth", choices=["sgbm", "ffs", "mono", "none"], help="default: config depth_method, or mono before calibration")
    v.add_argument("--port", type=int, default=8765)
    v.add_argument("--replay", type=Path, help="play a recorded clip instead of the cameras")
    v.add_argument("--snapshot", type=Path, help="write the last composite frame here on exit")
    v.add_argument("--seconds", type=float, help="stop after this long")
    v.add_argument("--no-browser", action="store_true")
    v.add_argument("--no-detect", action="store_true")
    v.add_argument("--speak", action="store_true", help="speak alerts through the Windows voice")
    v.add_argument("--log", action="store_true", help="write per-frame JSON lines under data/runs/")
    v.set_defaults(fn=cmd_view)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
