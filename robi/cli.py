"""Command-line interface: `robi start`, `robi camera-bench`, `robi doctor`."""
import argparse
import json
import statistics
import time
from pathlib import Path


def camera_bench(args):
    """Confronta cattura pura e pipeline JPEG con la STESSA configurazione."""
    import cv2
    from .settings import backend_id, capture_config, capture_info, load_env, setting
    if args.from_env:
        load_env()
        backend = setting('ROBI_CAMERA_BACKEND', 'DSHOW')
        index = setting('ROBI_CAMERA_INDEX', 0, int)
        width = setting('ROBI_CAMERA_WIDTH', 640, int)
        height = setting('ROBI_CAMERA_HEIGHT', 480, int)
        fps = setting('ROBI_CAMERA_FPS', 30, int)
        fourcc = setting('ROBI_CAMERA_FOURCC', 'MJPG')
        quality = setting('ROBI_JPEG_QUALITY', 60, int)
    else:
        backend, index, width, height, fps, fourcc, quality = (
            args.backend, args.index, args.width, args.height, args.fps, args.fourcc, args.quality
        )
    cap = cv2.VideoCapture(index, backend_id(cv2, backend))
    if not cap.isOpened():
        raise SystemExit(f'Impossibile aprire webcam {index} con backend {backend}.')
    try:
        capture_config(cv2, cap, width, height, fps, fourcc)
        info = capture_info(cv2, cap)
        print('Richiesta:', json.dumps({'backend':backend,'index':index,'width':width,
             'height':height,'fps':fps,'fourcc':fourcc,'jpeg_quality':quality,
             'pipeline':args.pipeline}, indent=2))
        print('Camera negoziata:', json.dumps(info, indent=2))
        print(f'Warmup {args.warmup} frame; misuro {args.seconds} secondi...')
        for _ in range(args.warmup):
            cap.read()
        reads, works = [], []
        count = 0
        start = time.perf_counter()
        while time.perf_counter() - start < args.seconds:
            t0 = time.perf_counter()
            ok, frame = cap.read()
            t1 = time.perf_counter()
            if not ok:
                print('Frame non disponibile; interrompo.')
                break
            if args.pipeline != 'raw':
                h, w = frame.shape[:2]
                if w > 640:
                    frame = cv2.resize(frame, (640, max(1, round(h*640/w))))
                preview = frame.copy()
                cv2.rectangle(preview,(90,80),(280,310),(107,214,177),2)
                preview = cv2.flip(preview,1)
                if args.pipeline == 'jpeg':
                    success, _ = cv2.imencode('.jpg',preview,[cv2.IMWRITE_JPEG_QUALITY,quality])
                    if not success:
                        raise RuntimeError('Codifica JPEG non riuscita')
            t2 = time.perf_counter()
            reads.append((t1-t0)*1000)
            works.append((t2-t1)*1000)
            count += 1
        total = time.perf_counter()-start
        if count:
            print(json.dumps({'frames':count,'elapsed_s':round(total,2),
                'actual_fps':round(count/total,2),
                'read_mean_ms':round(statistics.mean(reads),1),
                'read_median_ms':round(statistics.median(reads),1),
                'read_max_ms':round(max(reads),1),
                'processing_mean_ms':round(statistics.mean(works),1),
                'processing_median_ms':round(statistics.median(works),1)},indent=2))
    finally:
        cap.release()


def doctor(_args):
    from .settings import load_env, setting
    load_env()
    for module in ('cv2', 'mediapipe'):
        try:
            imported = __import__(module)
            print(f'{module}: {imported.__version__}')
        except Exception as e:
            print(f'{module}: ERRORE {e}')
    model = Path(__file__).resolve().parent.parent / 'models' / 'blaze_face_short_range.tflite'
    print(f'Modello MediaPipe: {model} | presente: {model.is_file()}')
    print('Backend configurato:', setting('ROBI_CAMERA_BACKEND', 'DSHOW'))
    print('Python in uso:')
    import sys
    print(sys.executable)


def main():
    parser = argparse.ArgumentParser(prog='robi', description='ROBI Core — strumenti per sviluppatori')
    commands = parser.add_subparsers(dest='command', required=True)
    start = commands.add_parser('start', help='Avvia la dashboard locale')
    start.add_argument('--port', type=int, default=8765)
    start.set_defaults(action='start')
    bench = commands.add_parser('camera-bench', help='Misura SOLO acquisizione webcam, senza server e senza IA')
    bench.add_argument('--backend', choices=['DSHOW','MSMF','ANY'], default='DSHOW')
    bench.add_argument('--index', type=int, default=0)
    bench.add_argument('--width', type=int, default=640)
    bench.add_argument('--height', type=int, default=480)
    bench.add_argument('--fps', type=int, default=30)
    bench.add_argument('--fourcc', default='MJPG', choices=['MJPG','YUY2','AUTO'])
    bench.add_argument('--seconds', type=float, default=6)
    bench.add_argument('--warmup', type=int, default=12)
    bench.add_argument('--pipeline', choices=['raw','preview','jpeg'], default='raw')
    bench.add_argument('--from-env', action='store_true', help='Leggi le stesse impostazioni .env della dashboard')
    bench.add_argument('--quality', type=int, default=60)
    bench.set_defaults(action='bench')
    check = commands.add_parser('doctor', help='Controlla installazione e modello')
    check.set_defaults(action='doctor')
    args = parser.parse_args()
    if args.action == 'start':
        from .settings import load_env
        from .server import main as server_main
        import sys
        load_env()
        sys.argv = ['robi start', '--port', str(args.port)]
        server_main()
    elif args.action == 'bench': camera_bench(args)
    else: doctor(args)

if __name__ == '__main__': main()
