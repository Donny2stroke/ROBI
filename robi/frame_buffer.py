"""Latest-only handoff: no queue, consumers may skip obsolete images."""
from threading import Condition

class LatestFrameBuffer:
    def __init__(self):
        self._condition = Condition()
        self._seq = 0
        self._frame = None

    def publish(self, frame):
        # Caller transfers ownership: it MUST NOT mutate this frame after publish.
        with self._condition:
            self._seq += 1
            self._frame = frame
            self._condition.notify_all()
            return self._seq

    def latest(self):
        with self._condition:
            return self._seq, self._frame

    def wait_next(self, last_seq, timeout=0.1):
        with self._condition:
            self._condition.wait_for(lambda: self._seq != last_seq, timeout=timeout)
            return self._seq, self._frame
