# ROBI Core v0.3.1 — Developer Edition

Questa versione aggiunge AI Expression Lab opzionale. Inizia da [README_AI_EXPRESSION.md](README_AI_EXPRESSION.md).

# ROBI Core v0.2.2 — Developer Edition

Il nostro primo repository Python installabile. Occhi e interfaccia della v0.2.1, MediaPipe e webcam opzionali.

## Windows / PowerShell (consigliato Python 3.11 o 3.12)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\robi.exe doctor
.\.venv\Scripts\robi.exe start
```

Se hai Python 3.11 invece di 3.12, sostituisci `py -3.12` con `py -3.11` (controlla `py -0p`).

Apri `http://127.0.0.1:8765`. Interrompi con Ctrl+C. Questi comandi invocano sempre l'interprete isolato, quindi **non serve attivare** la venv né modificare PowerShell ExecutionPolicy.

### Equivalenze Node.js

| Node.js | Python | 
|---|---|
| `npm install` | `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"` |
| `npm run start` | `.\.venv\Scripts\robi.exe start` |
| `npm run test` | `.\.venv\Scripts\python.exe -m pytest -q` |
| `npm run lint` | `.\.venv\Scripts\python.exe -m ruff check robi tests` |

Il file `pyproject.toml` dichiara dipendenze, metadata e comando CLI `robi`.
`pip install -e` installa in **editable mode**: le modifiche nei `.py` non richiedono una nuova installazione, ma **riavvia il server** per ricaricarle.

## Modello MediaPipe

Per trasferire il modello locale già scaricato, copia il tuo `models/blaze_face_short_range.tflite` nella cartella `models/` di questo progetto.
Oppure scaricalo dalla fonte Google:

```powershell
Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite' -OutFile '.\models\blaze_face_short_range.tflite'
```

Verifica sempre con `robi doctor`. Se non presente, il rilevamento ripiega su OpenCV.

## Primo esperimento: isolamento del collo di bottiglia

Chiudi la dashboard e **tutte le altre app che utilizzano la webcam**, poi esegui:

```powershell
.\.venv\Scripts\robi.exe camera-bench --backend DSHOW --fourcc MJPG
.\.venv\Scripts\robi.exe camera-bench --backend MSMF --fourcc MJPG
.\.venv\Scripts\robi.exe camera-bench --backend DSHOW --fourcc YUY2
```

Confronta `actual_fps`, `read_median_ms`, risoluzione e FOURCC effettivi. Sono misure del driver **senza IA, JPEG e browser**. Alcuni driver non supportano tutte le combinazioni. Il `reported_fps` è solo ciò che dichiara il driver, non una misura effettiva.

Per utilizzare il backend più veloce nella dashboard, modifica `.env`:

```dotenv
ROBI_CAMERA_BACKEND=MSMF
ROBI_CAMERA_FOURCC=MJPG
```

Riavvia `robi start` dopo ogni modifica. Se MSMF funziona peggio, rimetti DSHOW.

## Struttura

```text
robi/             # package Python: server HTTP, camera e visione, CLI, configurazione
robi/static/      # dashboard ed Eye Studio
models/           # modello MediaPipe locale, non incluso
 tests/           # unit tests
pyproject.toml    # dipendenze, installazione editable, script CLI
.env.example      # template configurazione locale
```

## Cosa NON abbiamo ancora fatto

Non è stato testato un dispositivo video reale in questa sessione; i risultati su Windows dipendono da webcam, USB, driver e luce. La nuova versione NON promette 30 FPS. Le metriche serviranno a capire se il problema è fisico/driver o software.

## Sviluppo: esercizio

Leggi `robi/settings.py` e `robi/cli.py`: nota come un argomento `--backend` viene trasformato in una costante `cv2.CAP_*`, e perché il benchmark non esegue né il riconoscimento né l'encoding. Prova a modificare il valore `ROBI_CAMERA_BACKEND` in `.env`, esegui `robi doctor`, poi riavvia la dashboard.


## Diagnostica v0.2.3
Leggi `README_DIAGNOSTICA.md` per il confronto raw/preview/jpeg e la stampa della camera negoziata.
