"""DirectShow video device enumeration.

Both rig cameras report the same name, so they are told apart by device path.
OpenCV's CAP_DSHOW index is the position among DirectShow video devices, which
is the order ffmpeg lists them in.
"""

import re
import subprocess
from dataclasses import dataclass


class DeviceNotFound(LookupError):
    pass


class AmbiguousDevice(LookupError):
    pass


@dataclass(frozen=True)
class DeviceInfo:
    name: str
    path: str
    index: int


_NAME = re.compile(r'"(?P<name>.+)" \((?P<kind>video|audio|none)\)')
_ALT = re.compile(r'Alternative name "(?P<path>.+)"')


def parse_dshow_list(text: str) -> list[DeviceInfo]:
    devices: list[DeviceInfo] = []
    pending: str | None = None
    for line in text.splitlines():
        if m := _NAME.search(line):
            pending = m["name"] if m["kind"] == "video" else None
        elif (m := _ALT.search(line)) and pending is not None:
            devices.append(DeviceInfo(pending, m["path"], len(devices)))
            pending = None
    return devices


def list_video_devices() -> list[DeviceInfo]:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return parse_dshow_list(proc.stderr + proc.stdout)


def resolve(fragment: str, devices: list[DeviceInfo]) -> DeviceInfo:
    frag = fragment.lower()
    hits = [d for d in devices if frag in d.path.lower() or frag == d.name.lower()]
    if not hits:
        raise DeviceNotFound(f"no video device matches {fragment!r}")
    if len(hits) > 1:
        raise AmbiguousDevice(f"{len(hits)} video devices match {fragment!r}")
    return hits[0]
