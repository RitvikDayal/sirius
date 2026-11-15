from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Frame:
    image: np.ndarray
    t_ns: int
    seq: int


@dataclass(frozen=True)
class StereoPair:
    left: Frame
    right: Frame

    @property
    def skew_ns(self) -> int:
        return abs(self.left.t_ns - self.right.t_ns)

    @property
    def t_ns(self) -> int:
        return max(self.left.t_ns, self.right.t_ns)


def pair_latest(
    left: Frame | None,
    right: Frame | None,
    max_skew_ns: int,
    last_pair_seq: tuple[int, int] | None,
) -> StereoPair | None:
    if left is None or right is None:
        return None
    if last_pair_seq == (left.seq, right.seq):
        return None
    pair = StereoPair(left, right)
    return pair if pair.skew_ns <= max_skew_ns else None
