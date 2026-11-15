import numpy as np


def depth_to_points(
    z: np.ndarray, image_bgr: np.ndarray, fx: float, fy: float, cx: float, cy: float,
    baseline_m: float, step: int = 4, max_m: float = 8.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Back-project a depth map to coloured 3D points, origin at the lens midpoint (x right, y down, z forward)."""
    zs = z[::step, ::step]
    v, u = np.mgrid[0:z.shape[0]:step, 0:z.shape[1]:step]
    keep = np.isfinite(zs) & (zs > 0) & (zs < max_m)
    zk = zs[keep]
    x = (u[keep] - cx) * zk / fx - baseline_m / 2
    y = (v[keep] - cy) * zk / fy
    xyz = np.column_stack([x, y, zk]).astype(np.float32)
    rgb = image_bgr[::step, ::step][keep][:, ::-1].astype(np.uint8)
    return xyz, np.ascontiguousarray(rgb)
