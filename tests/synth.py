"""Synthetic stereo rig for calibration tests: two pinhole cameras, a planar board."""

import cv2
import numpy as np

W, H = 1280, 720
FX = 914.0
K = np.array([[FX, 0, W / 2], [0, FX, H / 2], [0, 0, 1]])
BASELINE = 0.117


def rot(pitch_deg=0.0, roll_deg=0.0, yaw_deg=0.0) -> np.ndarray:
    rx = cv2.Rodrigues(np.array([np.radians(pitch_deg), 0, 0]))[0]
    ry = cv2.Rodrigues(np.array([0, np.radians(yaw_deg), 0]))[0]
    rz = cv2.Rodrigues(np.array([0, 0, np.radians(roll_deg)]))[0]
    return rz @ ry @ rx


# Right camera relative to left: X_r = R_REL @ (X_l - C), C = (B, 0, 0); like the real rig.
R_REL = rot(pitch_deg=4.0, roll_deg=2.2)
C_RIGHT = np.array([BASELINE, 0.0, 0.0])


def to_right(R_b, t_b):
    return R_REL @ R_b, R_REL @ (t_b - C_RIGHT)


def render(texture: np.ndarray, px_per_m: float, R: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Image of a planar texture (z=0, origin top-left, metres) seen by a camera at pose (R, t)."""
    M = K @ np.column_stack([R[:, 0], R[:, 1], t])
    S = np.diag([1 / px_per_m, 1 / px_per_m, 1.0])
    img = cv2.warpPerspective(texture, M @ S, (W, H), flags=cv2.INTER_AREA, borderValue=200)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def board_poses(n: int, board_w: float, board_h: float, seed: int = 0):
    rng = np.random.default_rng(seed)
    poses = []
    while len(poses) < n:
        z = rng.uniform(0.5, 1.5)
        R_b = rot(rng.uniform(-25, 25), rng.uniform(-15, 15), rng.uniform(-25, 25))
        centre = np.array([BASELINE / 2 + rng.uniform(-0.15, 0.15) * z, rng.uniform(-0.1, 0.1) * z, z])
        t_b = centre - R_b @ np.array([board_w / 2, board_h / 2, 0.0])
        poses.append((R_b, t_b))
    return poses
