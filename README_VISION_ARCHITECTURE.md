# ROBI v0.3.0 — Vision Architecture + segnali facciali

## Avvio su Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Imposta `ROBI_CAMERA_BACKEND=MSMF` e `ROBI_CAMERA_FOURCC=YUY2` in `.env` (in base ai tuoi benchmark).

Copia `blaze_face_short_range.tflite` già scaricato nella cartella `models/`. In assenza del secondo modello ROBI usa Face Detector normale.

Per attivare gli indicatori facciali osservabili, scarica il bundle ufficiale Google (Face Landmarker):

```powershell
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task" -OutFile ".\models\face_landmarker.task"
```

Poi: `.\.venv\Scripts\robi.exe start`. Dal browser apri http://127.0.0.1:8765

Se il modello non è presente o non si inizializza, il fallback è il modello Face Detector. Per verificare il dispositivo usa `robi camera-bench --from-env --pipeline jpeg`.

## Architettura

- `frame_buffer.py`: un solo frame condiviso, mai una coda lunga; `wait_next()` permette ai consumer di saltare frame obsoleti.
- `video_streamer.py`: compressione JPEG in thread separato rispetto all'acquisizione.
- `camera.py`: acquisizione e coordinamento del rilevatore, mantenendo API precedenti. Il prossimo refactoring estrarrà anche `FaceDetector` e `GazeController` in moduli indipendenti.
- `expression.py`: conversione dei blendshape in cinque indicatori interpretabili; **nessuna classificazione emozionale**.

## Interpretazione

I coefficienti di un blendshape indicano somiglianza con determinate configurazioni facciali, non certezza di emozioni o intenzioni. Sorridere non significa automaticamente essere felici. Non si conservano immagini o cronologie emotive. Prima di usare osservazioni all'interno di dialoghi con altre persone serviranno consenso esplicito e controlli di privacy.

## Esperimento guidato

Confronta nella dashboard `acquisizione FPS` e `JPEG FPS`: lo streamer ora gira su un thread dedicato. Controlla che l'occhio segua il volto; prova a sorridere e ad aprire la bocca, verifica che i segnali cambino; non interpretare questi numeri come emozioni reali.

## Limiti

Questa release non è stata validata con webcam Windows o modello Face Landmarker nel runtime finale; i test locali verificano il buffer e la logica dei segnali. Le prestazioni reali possono differire dalla v0.2.3. In particolare i due thread di visione/streaming condividono CPU e potrebbero introdurre jitter.
