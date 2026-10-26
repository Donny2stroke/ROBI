"""Simple local settings. Standard library only; .env is parsed explicitly."""
import os
from pathlib import Path


def load_env():
    path = Path.cwd() / '.env'
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        name, value = line.split('=', 1)
        name = name.strip()
        if name.startswith('ROBI_'):
            os.environ.setdefault(name, value.strip().strip('"').strip("'"))


def setting(name, default, cast=str):
    return cast(os.getenv(name, default))


def backend_id(cv2, name):
    names = {'DSHOW': cv2.CAP_DSHOW, 'MSMF': cv2.CAP_MSMF, 'ANY': cv2.CAP_ANY}
    if name.upper() not in names:
        raise ValueError(f'Backend {name!r} non valido: DSHOW, MSMF, ANY')
    return names[name.upper()]


def capture_config(cv2, cap, width, height, fps, fourcc):
    """Set requested values; driver may refuse or negotiate other values."""
    if fourcc.upper() != 'AUTO':
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc.upper()))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)


def capture_info(cv2, cap):
    raw = int(cap.get(cv2.CAP_PROP_FOURCC))
    codec = ''.join(chr((raw >> (8 * i)) & 255) for i in range(4)).strip('\x00')
    return {'backend': cap.getBackendName(),
            'resolution': f'{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}',
            'reported_fps': round(cap.get(cv2.CAP_PROP_FPS), 2), 'fourcc': codec}
