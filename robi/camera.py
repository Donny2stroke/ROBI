"""Webcam opzionale: acquisizione fluida e face detection a frequenza limitata."""
import threading
import time
import sys
from .settings import load_env, setting, backend_id, capture_config, capture_info
from .frame_buffer import LatestFrameBuffer
from .video_streamer import VideoStreamer
from .expression import from_blendshapes
from .ai_expression import ExpressionWorker


class CameraService:
    def __init__(self):
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread = None
        self._active = False
        self._error = None
        self._frame = None
        self._face = None
        self._gaze = (0.0, 0.0)
        self._last_seen = 0.0
        self._frame_id = 0
        self._frame_time = 0.0
        self._fps = 0.0
        self._capture_count = 0
        self._sensitivity = 1.55
        self._detector = "nessuno"
        self._vision = None
        self._vision_thread = None
        self._latest_input = None
        self._input_seq = 0
        self._detection_fps = 0.0
        self._encode_fps = 0.0
        self._read_ms = 0.0
        self._encode_ms = 0.0
        self._vision_ms = 0.0
        self._camera_mode = "non disponibile"
        self._buffer = LatestFrameBuffer()
        self._streamer = None
        self._expressions = None
        self._landmarker_active = False
        self._expression_worker = None

    def status(self):
        with self._lock:
            return {"active": self._active, "error": self._error,
                    "face_detected": self._face is not None, "capture_fps": round(self._fps, 1),
                    "detector": self._detector, "sensitivity": self._sensitivity,
                    "face": self._face, "gaze_x": self._gaze[0], "gaze_y": self._gaze[1],
                    "detection_fps": round(self._detection_fps,1),
                    "encode_fps": round(self._encode_fps,1), "read_ms": round(self._read_ms,1),
                    "encode_ms": round(self._encode_ms,1), "vision_ms": round(self._vision_ms,1),
                    "camera_mode": self._camera_mode, "engine": "MediaPipe" if self._vision else "OpenCV",
                    "expression_signals": self._expressions, "landmarker_active": self._landmarker_active,
                    "ai_expression": self._expression_worker.snapshot() if self._expression_worker else {"enabled": False}}

    def configure(self, sensitivity):
        value = float(sensitivity)
        if not 1.0 <= value <= 2.5:
            raise ValueError("sensitivity deve essere fra 1.0 e 2.5")
        with self._lock:
            self._sensitivity = value
        return self.status()

    def frame(self):
        with self._lock:
            return self._streamer.latest()[1] if self._streamer else self._frame

    def frame_with_id(self):
        with self._lock:
            return self._streamer.latest() if self._streamer else (self._frame_id, self._frame)

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return self.status()
            try:
                import cv2  # noqa: F401
            except ImportError:
                self._error = "OpenCV non installato: esegui pip install -e ."
                return self.status()
            self._stop.clear()
            self._error = None
            self._landmarker_active = False
            self._expressions = None
            self._buffer = LatestFrameBuffer()
            if setting("ROBI_AI_EXPRESSION_ENABLED", "0") == "1":
                self._expression_worker = ExpressionWorker(hz=setting("ROBI_AI_EXPRESSION_HZ", 3, float))
                self._expression_worker.start()
            else:
                self._expression_worker = None
            self._streamer = VideoStreamer(self._buffer, self._face_snapshot, setting("ROBI_JPEG_QUALITY",60,int))
            self._streamer.start()
            self._vision_thread = threading.Thread(target=self._vision_loop, daemon=True)
            self._vision_thread.start()
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        return self.status()

    def stop(self):
        self._stop.set()
        with self._lock:
            self._active = False
            self._face = None
            self._expressions = None
            self._gaze = (0.0, 0.0)
        if self._expression_worker: self._expression_worker.clear()
        return self.status()

    def close(self):
        self.stop()
        if self._thread:
            self._thread.join(timeout=2)
        if self._vision_thread:
            self._vision_thread.join(timeout=2)
        if self._streamer:
            self._streamer.stop()
        if self._expression_worker:
            self._expression_worker.stop()

    def _face_snapshot(self):
        with self._lock:
            return dict(self._face) if self._face else None

    def _loop(self):
        import cv2
        load_env()
        backend_name = setting('ROBI_CAMERA_BACKEND', 'DSHOW' if sys.platform == 'win32' else 'ANY')
        index = setting('ROBI_CAMERA_INDEX', 0, int)
        cap = cv2.VideoCapture(index, backend_id(cv2, backend_name))
        if not cap.isOpened():
            with self._lock:
                self._error = f'Impossibile aprire la webcam {index} con {backend_name}.'
            cap.release()
            return
        capture_config(cv2, cap,
                       setting('ROBI_CAMERA_WIDTH', 640, int),
                       setting('ROBI_CAMERA_HEIGHT', 480, int),
                       setting('ROBI_CAMERA_FPS', 30, int),
                       setting('ROBI_CAMERA_FOURCC', 'MJPG'))
        actual = capture_info(cv2, cap)
        fps_start = time.monotonic()
        fps_count = 0
        encode_count = 0
        encode_window = time.monotonic()
        with self._lock:
            self._camera_mode = f"{actual['backend']} | {actual['resolution']} | {actual['fourcc']!r} | driver dichiara {actual['reported_fps']} FPS"
            print('[ROBI camera] richiesta:', backend_name, index, setting('ROBI_CAMERA_FOURCC', 'MJPG'))
            print('[ROBI camera] negoziata:', actual)
        with self._lock:
            self._active = True
        try:
            while not self._stop.is_set():
                started = time.monotonic()
                ok, frame = cap.read()
                read_ms = (time.monotonic() - started) * 1000
                if not ok:
                    with self._lock:
                        self._error = 'Lettura webcam non riuscita.'
                    break
                h, w = frame.shape[:2]
                if w > 640:
                    frame = cv2.resize(frame, (640, max(1, round(h * 640 / w))))
                    h, w = frame.shape[:2]
                # Capture thread only publishes immutable-to-consumers frames.
                self._buffer.publish(frame)
                fps_count += 1
                elapsed = time.monotonic() - fps_start
                with self._lock:
                    self._read_ms = .8*self._read_ms + .2*read_ms
                    self._encode_ms = self._streamer.encode_ms
                    self._encode_fps = self._streamer.fps
                    if elapsed >= 1.0:
                        self._fps = fps_count / elapsed
                        fps_start = time.monotonic()
                        fps_count = 0
                self._stop.wait(max(0.0, .001 - (time.monotonic() - started)))  # niente limite artificiale a ~15 FPS
        except Exception as exc:
            with self._lock:
                self._error = f'Errore webcam: {exc}'
        finally:
            cap.release()
            self._stop.set()
            with self._lock:
                self._active = False
                self._face = None
                self._detector = "nessuno"
                self._frame = None
                self._fps = 0.0
            if self._streamer:
                self._streamer.stop()

    def _vision_loop(self):
        """Process most recent frame ~12 Hz, never blocking MJPEG camera capture."""
        import cv2
        import os
        from pathlib import Path
        vision = None
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        profile = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
        model = Path(__file__).resolve().parent.parent / 'models' / 'blaze_face_short_range.tflite'
        landmark_model = model.parent / 'face_landmarker.task'
        landmarker = None
        try:
            import mediapipe as mp
            if landmark_model.is_file():
                opts = mp.tasks.vision.FaceLandmarkerOptions(
                    base_options=mp.tasks.BaseOptions(model_asset_path=str(landmark_model)),
                    running_mode=mp.tasks.vision.RunningMode.IMAGE,
                    num_faces=1, output_face_blendshapes=True)
                landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(opts)
            elif model.is_file():
                opts = mp.tasks.vision.FaceDetectorOptions(
                    base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
                    running_mode=mp.tasks.vision.RunningMode.IMAGE,
                    min_detection_confidence=0.45)
                vision = mp.tasks.vision.FaceDetector.create_from_options(opts)
        except Exception as exc:
            # OpenCV fallback remains operational for machines without MediaPipe.
            with self._lock:
                self._error = 'MediaPipe non disponibile, rilevamento OpenCV: ' + str(exc)
        with self._lock:
            self._vision = vision or landmarker
            self._landmarker_active = landmarker is not None
        last_seq = -1
        detection_times=[]
        try:
            while not self._stop.is_set():
                cycle = time.monotonic()
                seq, img = self._buffer.wait_next(last_seq, .02)
                if img is None or seq == last_seq:
                    self._stop.wait(.02)
                    continue
                last_seq = seq
                h,w=img.shape[:2]
                target_w=min(384,w)
                small=cv2.resize(img,(target_w,max(1,round(h*target_w/w))))
                scale=w/target_w
                best=None
                label='nessuno'
                signals = None
                if landmarker is not None:
                    rgb=cv2.cvtColor(small,cv2.COLOR_BGR2RGB)
                    import mediapipe as mp
                    result=landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb))
                    if result.face_landmarks:
                        points=result.face_landmarks[0]
                        minx,maxx=min(p.x for p in points),max(p.x for p in points)
                        miny,maxy=min(p.y for p in points),max(p.y for p in points)
                        best=(minx*w,miny*h,(maxx-minx)*w,(maxy-miny)*h)
                        label='Face Landmarker'
                        if result.face_blendshapes:
                            signals=from_blendshapes(result.face_blendshapes[0]).to_dict()
                elif vision is not None:
                    rgb=cv2.cvtColor(small,cv2.COLOR_BGR2RGB)
                    import mediapipe as mp
                    result=vision.detect(mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb))
                    if result.detections:
                        item=max(result.detections,key=lambda d:d.bounding_box.width*d.bounding_box.height)
                        b=item.bounding_box
                        best=(b.origin_x*scale,b.origin_y*scale,b.width*scale,b.height*scale)
                        label='MediaPipe'
                else:
                    gray=cv2.equalizeHist(cv2.cvtColor(small,cv2.COLOR_BGR2GRAY))
                    faces=cascade.detectMultiScale(gray,scaleFactor=1.12,minNeighbors=4,minSize=(25,25)) if not cascade.empty() else []
                    if len(faces):
                        r=max(faces,key=lambda f:f[2]*f[3]);best=tuple(v*scale for v in r);label='frontale'
                    elif not profile.empty():
                        for flipped in (False,True):
                            g=cv2.flip(gray,1) if flipped else gray
                            candidates=profile.detectMultiScale(g,scaleFactor=1.12,minNeighbors=3,minSize=(25,25))
                            if len(candidates):
                                x,y,fw,fh=max(candidates,key=lambda f:f[2]*f[3])
                                if flipped:x=g.shape[1]-x-fw
                                best=tuple(v*scale for v in (x,y,fw,fh));label='profilo';break
                # L'AI riceve solo il ritaglio del volto e lavora su un thread separato.
                if self._expression_worker:
                    if best is not None:
                        bx, by, bw, bh = best
                        # Padding lieve e coordinate limitate alla dimensione del frame.
                        pad = 0.10
                        x1 = max(0, int(bx - pad*bw))
                        y1 = max(0, int(by - pad*bh))
                        x2 = min(w, int(bx + (1+pad)*bw))
                        y2 = min(h, int(by + (1+pad)*bh))
                        if x2 > x1+24 and y2 > y1+24:
                            self._expression_worker.publish(img[y1:y2, x1:x2].copy())
                    else:
                        self._expression_worker.clear()
                vision_ms = (time.monotonic() - cycle) * 1000
                with self._lock:
                    self._vision_ms = .8*self._vision_ms + .2*vision_ms
                    self._expressions = signals if best is not None else None
                    if best is not None:
                        x,y,fw,fh=best
                        cx=(x+fw/2)/w; cy=(y+fh/2)/h
                        gain=self._sensitivity
                        gx=max(-1,min(1,(.5-cx)*2*gain))
                        gy=max(-1,min(1,(cy-.5)*2*gain))
                        ox,oy=self._gaze
                        self._gaze=(round(.56*ox+.44*gx,3),round(.56*oy+.44*gy,3))
                        self._face={'x':round(x/w,3),'y':round(y/h,3),'width':round(fw/w,3),'height':round(fh/h,3)}
                        self._last_seen=cycle
                    elif cycle-self._last_seen > .7:
                        self._face=None
                        ox,oy=self._gaze
                        self._gaze=(round(ox*.85,3),round(oy*.85,3))
                    self._detector=label
                    detection_times=[t for t in detection_times if cycle-t<1]
                    detection_times.append(cycle)
                    self._detection_fps=float(len(detection_times))
                self._stop.wait(max(0,.085-(time.monotonic()-cycle)))
        except Exception as exc:
            with self._lock:
                self._error='Errore rilevamento: '+str(exc)
        finally:
            if vision is not None:vision.close()
            if landmarker is not None:landmarker.close()
            with self._lock:
                self._vision=None
                self._landmarker_active=False
