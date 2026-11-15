from pathlib import Path

import pytest

from sirius.devices import AmbiguousDevice, DeviceNotFound, parse_dshow_list, resolve

FIXTURE = Path(__file__).parent / "fixtures" / "ffmpeg_list_devices.txt"


@pytest.fixture
def devs():
    return parse_dshow_list(FIXTURE.read_text(encoding="utf-8", errors="replace"))


def test_parse_real_listing(devs):
    assert [d.index for d in devs] == [0, 1, 2, 3]
    usb = [d for d in devs if d.name == "USB Camera"]
    assert len(usb) == 2
    assert "6&315a9f63" in usb[0].path and usb[0].index == 1
    assert "6&1ec6b2f7" in usb[1].path and usb[1].index == 2
    assert not any("Microphone" in d.name or "Headset" in d.name for d in devs)


def test_resolve_fragment(devs):
    assert resolve("6&1ec6b2f7", devs).index == 2
    with pytest.raises(AmbiguousDevice):
        resolve("USB Camera", devs)
    with pytest.raises(DeviceNotFound):
        resolve("nope", devs)
