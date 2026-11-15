"""Speech output. SAPI (built into Windows) is offline and starts speaking in ~50 ms once warm."""

import time
from typing import Protocol

SVSF_ASYNC = 1
SVSF_PURGE_BEFORE_SPEAK = 2
SRSE_IS_SPEAKING = 2


class Voice(Protocol):
    def say(self, text: str, interrupt: bool) -> int: ...
    def busy(self) -> bool: ...


class SapiVoice:
    def __init__(self, rate: int = 2):
        import win32com.client

        self.v = win32com.client.Dispatch("SAPI.SpVoice")
        self.v.Rate = rate
        # The first utterance opens the audio device (~230 ms); pay that now, silently.
        self.v.Volume = 0
        self.v.Speak("ready", 0)
        self.v.Volume = 100

    def say(self, text: str, interrupt: bool) -> int:
        t = time.perf_counter_ns()
        self.v.Speak(text, SVSF_ASYNC | (SVSF_PURGE_BEFORE_SPEAK if interrupt else 0))
        return t

    def busy(self) -> bool:
        return self.v.Status.RunningState == SRSE_IS_SPEAKING


def measure_start_ms(voice: SapiVoice, n: int = 10, text: str = "chair, one metre, ahead") -> list[float]:
    out = []
    for _ in range(n):
        t0 = time.perf_counter()
        voice.say(text, interrupt=True)
        while not voice.busy() and time.perf_counter() - t0 < 2:
            time.sleep(0.0005)
        out.append((time.perf_counter() - t0) * 1000)
        time.sleep(0.3)
    voice.say("", interrupt=True)
    return out


class RecordingVoice:
    """Test double: records what would be said; the test sets `is_busy`."""

    def __init__(self, busy: bool = False):
        self.said: list[tuple[str, bool]] = []
        self.is_busy = busy

    def say(self, text: str, interrupt: bool) -> int:
        self.said.append((text, interrupt))
        return time.perf_counter_ns()

    def busy(self) -> bool:
        return self.is_busy


class MutableVoice:
    """Wraps a voice so the dashboard can mute it; muting also stops speech in progress."""

    def __init__(self, inner):
        self.inner = inner
        self._muted = False

    @property
    def muted(self) -> bool:
        return self._muted

    @muted.setter
    def muted(self, value: bool) -> None:
        if value and not self._muted:
            self.inner.say("", interrupt=True)
        self._muted = value

    def say(self, text: str, interrupt: bool) -> int:
        if self._muted:
            return time.perf_counter_ns()
        return self.inner.say(text, interrupt)

    def busy(self) -> bool:
        return False if self._muted else self.inner.busy()
