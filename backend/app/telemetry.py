"""In-memory rolling telemetry for the digital twin.

The simulator records each zone's density over time here so the Operations Copilot
can compute short-horizon trends and forecasts. Kept in-process (not the DB) because
it is high-frequency, ephemeral, and only needs the most recent window.
"""
import time
import threading
from collections import defaultdict, deque

# ~40 samples at a 3s tick ≈ 2 minutes of history — enough to fit a stable trend line.
DEFAULT_MAXLEN = 40


class ZoneTelemetry:
    def __init__(self, maxlen: int = DEFAULT_MAXLEN):
        self._lock = threading.Lock()
        self._maxlen = maxlen
        self._history = defaultdict(lambda: deque(maxlen=maxlen))

    def record(self, zone_id: str, density: float, current_crowd: int, ts: float = None):
        """Append a (timestamp, density, current_crowd) sample for a zone."""
        ts = ts if ts is not None else time.time()
        with self._lock:
            self._history[zone_id].append((ts, float(density), int(current_crowd)))

    def get(self, zone_id: str) -> list:
        """Return the recorded samples for a zone as a list of (ts, density, crowd)."""
        with self._lock:
            return list(self._history[zone_id])

    def zone_ids(self) -> list:
        with self._lock:
            return list(self._history.keys())

    def clear(self):
        with self._lock:
            self._history.clear()


# Module-level singleton shared between the simulator (writer) and copilot (reader).
_telemetry = ZoneTelemetry()


def get_telemetry() -> ZoneTelemetry:
    return _telemetry
