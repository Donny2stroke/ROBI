"""Classificazione locale *di espressioni*, non delle emozioni vissute.

Il backend DeepFace è importato in modo lazy nel worker dedicato; non blocca
CameraCapture/VideoStreamer. I punteggi non sono calibrati come probabilità.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
import threading
import time

LABELS = ("angry", "disgust", "fear", "happy", "sad", "surprise", "neutral")

class ExpressionClassifier(Protocol):
    def predict(self, face_bgr) -> dict[str, float]: ...


def normalize_scores(raw: dict) -> dict[str, float]:
    """DeepFace di norma restituisce punteggi 0..100, non confidence calibrate."""
    return {key: max(0.0, min(100.0, float(raw.get(key, 0.0)))) for key in LABELS}

class DeepFaceClassifier:
    def __init__(self):
        from deepface import DeepFace  # opzionale: installato via extra emotion
        self._deepface = DeepFace

    def predict(self, face_bgr):
        response = self._deepface.analyze(
            img_path=face_bgr, actions=["emotion"], detector_backend="skip",
            enforce_detection=False, silent=True,
        )
        if isinstance(response, list):
            response = response[0]
        return normalize_scores(response["emotion"])


class ExpressionWorker:
    """Mailbox latest-only: il thread inferenza scarta frame obsoleti."""
    def __init__(self, classifier_factory=DeepFaceClassifier, hz=3.0):
        self._factory = classifier_factory
        self._period = 1 / max(0.2, min(10.0, float(hz)))
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        self._pending = None
        self._result = None
        self._error = None
        self._latency_ms = 0.0
        self._running = False

    def start(self):
        if self._thread and self._thread.is_alive(): return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="robi-ai-expression", daemon=True)
        self._thread.start()

    def publish(self, face_bgr):
        # Il chiamante passa un crop già copiato: nessuna modifica ai frame condivisi.
        with self._lock:
            self._pending = face_bgr
        self._wake.set()

    def clear(self):
        with self._lock:
            self._pending = None
            self._result = None

    def snapshot(self):
        with self._lock:
            age = None if not self._result else round(time.monotonic()-self._result["timestamp"], 1)
            return {"enabled": True, "running": self._running, "error": self._error,
                    "scores": None if not self._result or (age is not None and age > 2.0) else self._result["scores"],
                    "age_s": age, "inference_ms": round(self._latency_ms, 1)}

    def stop(self):
        self._stop.set()
        self._wake.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _run(self):
        try:
            classifier = self._factory()
            with self._lock: self._running = True
            next_at = 0.0
            while not self._stop.is_set():
                self._wake.wait(timeout=.25)
                self._wake.clear()
                if self._stop.is_set(): break
                delay = next_at - time.monotonic()
                if delay > 0 and self._stop.wait(delay): break
                with self._lock:
                    frame, self._pending = self._pending, None
                if frame is None: continue
                t0=time.monotonic()
                scores=classifier.predict(frame)
                finished=time.monotonic()
                with self._lock:
                    self._result={"timestamp":finished,"scores":scores}
                    self._latency_ms=(finished-t0)*1000
                next_at=finished+self._period
        except Exception as exc:
            with self._lock: self._error = f"AI Expression non disponibile: {exc}"
        finally:
            with self._lock: self._running=False
