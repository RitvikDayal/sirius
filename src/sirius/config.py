import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "rig.toml"


@dataclass(frozen=True)
class CharucoSpec:
    square_mm: float
    marker_mm: float
    cols: int = 7
    rows: int = 5
    dictionary: str = "DICT_5X5_100"


@dataclass(frozen=True)
class RigConfig:
    left_path: str
    right_path: str
    charuco: CharucoSpec
    width: int = 1280
    height: int = 720
    fps: int = 30
    baseline_mm_measured: float | None = None
    depth_method: str = "sgbm"
    depth_scale: float = 0.5
    calibration: str | None = None
    speak_approx_distances: bool = False  # speak single-camera distances, with "about", until stereo is calibrated
    extra: dict = field(default_factory=dict)


def set_config_value(path: Path, key: str, value) -> None:
    """Set a top-level key in the TOML file, keeping comments and layout.

    Replaces `key = ...` or a commented-out `# key = ...`; otherwise inserts the
    key before the first [table].
    """
    import re

    rendered = f'"{value}"' if isinstance(value, str) else str(value)
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    pat = re.compile(rf"^\s*#?\s*{re.escape(key)}\s*=")
    for i, line in enumerate(lines):
        if line.lstrip().startswith("["):
            lines.insert(i, f"{key} = {rendered}")
            break
        if pat.match(line):
            lines[i] = f"{key} = {rendered}"
            break
    else:
        lines.append(f"{key} = {rendered}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_config(path: Path = DEFAULT_CONFIG) -> RigConfig:
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    charuco = CharucoSpec(**raw.pop("charuco"))
    known = set(RigConfig.__dataclass_fields__) - {"charuco", "extra"}
    kwargs = {k: raw.pop(k) for k in list(raw) if k in known}
    return RigConfig(charuco=charuco, extra=raw, **kwargs)
