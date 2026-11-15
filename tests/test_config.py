from sirius.config import load_config, set_config_value


def test_set_config_value_replaces_and_uncomments(tmp_path):
    p = tmp_path / "rig.toml"
    p.write_text(
        'left_path = "a"\nright_path = "b"\n'
        'depth_method = "sgbm"   # set by bake-off\n'
        "# baseline_mm_measured = 0.0   # measure\n"
        "[charuco]\nsquare_mm = 35.0\nmarker_mm = 26.0\n",
        encoding="utf-8",
    )
    set_config_value(p, "depth_method", "ffs")
    set_config_value(p, "baseline_mm_measured", 117.5)
    set_config_value(p, "calibration", "data/calib/x/calib.npz")
    cfg = load_config(p)
    assert cfg.depth_method == "ffs"
    assert cfg.baseline_mm_measured == 117.5
    assert cfg.calibration == "data/calib/x/calib.npz"
    assert cfg.charuco.square_mm == 35.0


def test_load_config_defaults(tmp_path):
    p = tmp_path / "rig.toml"
    p.write_text(
        'left_path = "6&1ec6b2f7"\n'
        'right_path = "6&315a9f63"\n'
        "[charuco]\n"
        "square_mm = 35.0\n"
        "marker_mm = 26.0\n",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.fps == 30
    assert (cfg.width, cfg.height) == (1280, 720)
    assert cfg.depth_method == "sgbm"
    assert cfg.baseline_mm_measured is None
    assert cfg.charuco.cols == 7 and cfg.charuco.rows == 5
    assert cfg.charuco.dictionary == "DICT_5X5_100"
