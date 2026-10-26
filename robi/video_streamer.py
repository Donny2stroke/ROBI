"""Prepare camera previews off the capture thread."""
import threading
import time

class VideoStreamer:
    def __init__(self, input_buffer, face_provider, quality=60):
        self.input_buffer = input_buffer
        self.face_provider = face_provider
        self.quality = int(quality)
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()
        self._jpeg = None
        self._seq = 0
        self.encode_ms = 0.0
        self.fps = 0.0

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name='robi-video-stream')
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)

    def latest(self):
        with self._lock:
            return self._seq, self._jpeg

    def _run(self):
        import cv2
        last = 0
        count = 0
        tick = time.monotonic()
        while not self._stop.is_set():
            seq, frame = self.input_buffer.wait_next(last, .1)
            if seq == last or frame is None:
                continue
            last = seq
            h, w = frame.shape[:2]
            preview = frame.copy()
            face = self.face_provider()
            if face:
                x, y = int(face['x']*w), int(face['y']*h)
                fw, fh = int(face['width']*w), int(face['height']*h)
                cv2.rectangle(preview, (x,y), (x+fw,y+fh), (107,214,177), 2)
            preview = cv2.flip(preview, 1)
            started = time.monotonic()
            ok, encoded = cv2.imencode('.jpg', preview, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
            duration = (time.monotonic()-started)*1000
            now = time.monotonic()
            if ok:
                with self._lock:
                    self._jpeg = encoded.tobytes()
                    self._seq += 1
                    self.encode_ms = .8*self.encode_ms + .2*duration
                    count += 1
                    if now-tick>=1:
                        self.fps = count/(now-tick)
                        count = 0
                        tick = now
