"""Server HTTP loopback-only. Solo Python standard; camera opzionale."""
import argparse
import json
import math
import mimetypes
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from .camera import CameraService
from .brain import Conversation
from .memory import MemoryStore
from .learning import suggest_memories
from .evaluation import evaluate

STATIC = Path(__file__).parent / 'static'
ALLOWED_STATES = {'idle','listening','thinking','speaking','curious','happy','sleepy'}

class Core:
    def __init__(self):
        self.lock = threading.RLock()
        self.camera = CameraService()
        self.memory = MemoryStore()
        self.conversation = Conversation(memory=self.memory)
        self.state = 'idle'
        self.gaze_x = 0.0
        self.gaze_y = 0.0
        self.camera_tracking = False
        self.blink_id = 0
        self.started = time.time()

    def snapshot(self):
        camera = self.camera.status()
        with self.lock:
            x, y = (camera['gaze_x'], camera['gaze_y']) if self.camera_tracking and camera['active'] else (self.gaze_x,self.gaze_y)
            return {'version':'0.4.4','state':self.state,'gaze_x':x,'gaze_y':y,
                    'camera_tracking':self.camera_tracking,'blink_id':self.blink_id,
                    'camera':camera,'uptime_seconds':int(time.time()-self.started)}

    def command(self, data):
        if not isinstance(data, dict):
            raise ValueError('È richiesto un oggetto JSON.')
        with self.lock:
            if 'state' in data:
                if data['state'] not in ALLOWED_STATES:
                    raise ValueError('Stato non valido.')
                self.state = data['state']
            for name in ('gaze_x','gaze_y'):
                if name in data:
                    v = data[name]
                    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not -1 <= v <= 1:
                        raise ValueError(name+' deve essere un numero tra -1 e 1.')
                    setattr(self,name,round(float(v),3))
            if 'camera_tracking' in data:
                if not isinstance(data['camera_tracking'],bool):
                    raise ValueError('camera_tracking deve essere booleano.')
                self.camera_tracking = data['camera_tracking']
            if data.get('blink') is True:
                self.blink_id += 1
        return self.snapshot()

core = Core()

class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body, content_type='application/json; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def json_reply(self, code, data):
        self.reply(code,json.dumps(data,ensure_ascii=False).encode('utf-8'))

    def mjpeg_stream(self):
        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=robi')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        last_id = -1
        try:
            while core.camera.status()['active']:
                frame_id, data = core.camera.frame_with_id()
                if data is not None and frame_id != last_id:
                    last_id = frame_id
                    self.wfile.write(b'--robi\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(data)).encode('ascii') + b'\r\n\r\n' + data + b'\r\n')
                    self.wfile.flush()
                time.sleep(0.035)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/camera/stream.mjpg':
            return self.mjpeg_stream()
        if path == '/api/memories':
            return self.json_reply(200,{'memories':core.memory.list()})
        if path == '/api/chat/model':
            return self.json_reply(200,core.conversation.model_status())
        if path == '/api/chat/history':
            return self.json_reply(200,{'messages':core.conversation.history()})
        if path == '/api/status':
            return self.json_reply(200,core.snapshot())
        if path == '/api/camera/frame.jpg':
            frame = core.camera.frame()
            if frame is None:
                return self.json_reply(404,{'error':'Nessun fotogramma disponibile.'})
            return self.reply(200,frame,'image/jpeg')
        path = '/index.html' if path == '/' else path
        allowed = {'/index.html','/eyes.html'}
        if path not in allowed:
            return self.json_reply(404, {'error':'Risorsa non trovata.'})
        data = (STATIC / path.lstrip('/')).read_bytes()
        return self.reply(200,data,'text/html; charset=utf-8')

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in ('/api/eyes','/api/camera/start','/api/camera/stop','/api/camera/config','/api/chat','/api/chat/clear','/api/chat/model','/api/memories','/api/memories/delete','/api/memories/clear','/api/learning/suggest','/api/evaluation/run'):
            return self.json_reply(404, {'error':'Risorsa non trovata.'})
        try:
            length = int(self.headers.get('Content-Length','0'))
            if not 0 <= length <= 8192:
                return self.json_reply(413,{'error':'Richiesta troppo grande.'})
            raw = self.rfile.read(length)
            data = json.loads(raw) if raw else {}
            if path == '/api/evaluation/run':
                out = evaluate(core.conversation.history(),core.conversation.model)
            elif path == '/api/learning/suggest':
                out = {'suggestions':suggest_memories(core.conversation.history(),core.conversation.model)}
            elif path == '/api/memories':
                out = core.memory.add(data.get('category'),data.get('fact'))
            elif path == '/api/memories/delete':
                out = core.memory.delete(data.get('id'))
            elif path == '/api/memories/clear':
                out = core.memory.clear()
            elif path == '/api/chat/model':
                out = core.conversation.set_model(data.get('model'))
            elif path == '/api/chat':
                out = core.conversation.reply(data.get('message'))
            elif path == '/api/chat/clear':
                core.conversation.clear()
                out = {'messages': []}
            elif path == '/api/eyes':
                out = core.command(data)
            elif path == '/api/camera/config':
                out = core.camera.configure(data['sensitivity'])
            elif path == '/api/camera/start':
                out = core.camera.start()
            else:
                out = core.camera.stop()
            return self.json_reply(200,out)
        except (OSError, TimeoutError) as exc:
            return self.json_reply(503,{'error':'Valutatore AI non disponibile: verifica Ollama.'})
        except RuntimeError as exc:
            return self.json_reply(503,{'error':str(exc)})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            return self.json_reply(400,{'error':str(exc)})

    def log_message(self, fmt, *args):
        if not self.path.startswith('/api/status') and not self.path.startswith('/api/camera/frame.jpg'):
            super().log_message(fmt,*args)


def main():
    parser = argparse.ArgumentParser(description='ROBI Core — server locale')
    parser.add_argument('--port',type=int,default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1',args.port), Handler)
    print(f'ROBI Core v0.4.4 | http://127.0.0.1:{args.port}',flush=True)
    print('Premi CTRL+C per fermare il server.',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        core.camera.close()
        core.memory.close()

if __name__ == '__main__':
    main()
