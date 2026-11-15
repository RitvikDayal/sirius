import io

import cv2
import numpy as np

from sirius.capture import ffmpeg_args, iter_jpegs


class ChunkyStream(io.RawIOBase):
    """Returns at most 7 bytes per read, like a Windows pipe that has not filled yet."""

    def __init__(self, data: bytes):
        self._b = io.BytesIO(data)

    def readable(self):
        return True

    def readinto(self, buf):
        chunk = self._b.read(min(7, len(buf)))
        buf[: len(chunk)] = chunk
        return len(chunk)


def _jpeg(value: int) -> bytes:
    img = np.full((16, 24, 3), value, np.uint8)
    return cv2.imencode(".jpg", img)[1].tobytes()


def test_iter_jpegs_splits_stream_across_short_reads():
    blobs = [_jpeg(v) for v in (10, 120, 240)]
    stream = ChunkyStream(b"".join(blobs) + blobs[0][:20])  # trailing partial frame
    got = list(iter_jpegs(stream))
    assert got == blobs
    decoded = [cv2.imdecode(np.frombuffer(g, np.uint8), cv2.IMREAD_COLOR) for g in got]
    assert [int(d.mean()) for d in decoded] == [10, 120, 240]


def test_ffmpeg_args_open_by_path_and_pass_mjpeg_through():
    args = ffmpeg_args("@device_pnp_\\\\?\\usb#x", 1280, 720, 30)
    assert args[args.index("-vcodec") + 1] == "mjpeg"
    assert args[args.index("-video_size") + 1] == "1280x720"
    assert args[args.index("-framerate") + 1] == "30"
    assert "video=@device_pnp_\\\\?\\usb#x" in args
    # Raw BGR at 83 MB/s per camera saturates the pipe (~23 FPS); copying the camera's JPEGs does not.
    assert args[args.index("-c:v") + 1] == "copy"
    assert args[args.index("-f", args.index("-i")) + 1] == "mjpeg"
    assert args[-1] == "pipe:1"
