"""Download model files into data/models/ (gitignored)."""

from pathlib import Path

from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[1] / "data" / "models"


def fetch_ffs() -> Path:
    out = ROOT / "ffs"
    for f in ("onnx/c_fast_foundationstereo_bp2_dynbatch_dynhw.onnx", "cfg.yaml"):
        hf_hub_download("nvidia/c-fast-foundationstereo", f, local_dir=out)
    return out / "onnx" / "c_fast_foundationstereo_bp2_dynbatch_dynhw.onnx"


if __name__ == "__main__":
    print(fetch_ffs())
