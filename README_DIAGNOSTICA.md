# ROBI v0.2.3 — Performance Lab

## Cosa abbiamo confermato
`doctor` e `settings` leggono MSMF e YUY2. Non è quindi utile ripetere la verifica dell’ambiente.

## Ipotesi da distinguere
- `cap.read()` si comporta diversamente quando eseguiamo anche elaborazioni video;
- la dashboard potrebbe richiedere risorse o influire sui tempi del driver;
- `VideoCapture` potrebbe negoziare diversamente a seconda del contesto;
- differenze di esposizione, illuminazione e comportamento del driver tra le prove.

## Prove controllate
Chiudi ROBI e ogni altra applicazione che usa la webcam. Avvia dal terminale del progetto:

```powershell
.\.venv\Scripts\robi.exe camera-bench --from-env --pipeline raw
.\.venv\Scripts\robi.exe camera-bench --from-env --pipeline preview
.\.venv\Scripts\robi.exe camera-bench --from-env --pipeline jpeg
```

La prima misura solo `cap.read()`; la seconda aggiunge le operazioni di copia, rettangolo e flip; la terza aggiunge `imencode`. NON vengono eseguiti MediaPipe, streaming e browser. Ripeti eventualmente ogni prova 2–3 volte perché il driver può avere jitter.

Poi avvia `robi start` (con il comando completo dalla `.venv`), attiva la camera e controlla il terminale: stampa la configurazione richiesta e quella negoziata. Consulta inoltre `http://127.0.0.1:8765/api/status` per il campo `camera.camera_mode`.

## Interpretazione
Se `raw` si avvicina a 28 FPS e `jpeg` scende a 7–9, il lavoro nel ciclo video interferisce con l'acquisizione. Se tutti sono vicini a 28 FPS, il collo di bottiglia è probabilmente legato alla pipeline concorrente (MediaPipe, streaming o server). Se già `raw` è lento, ricontrollare formato, esposizione, driver e ripetibilità.

Nota: il FOURCC restituito da MSMF potrebbe non essere una stringa leggibile. `cap.set()` non garantisce l'accettazione dei parametri.

## Prossimo refactoring
Sulla base delle misure, separare `CameraCapture`, `FaceDetector`, `VideoStreamer` e `GazeController`, con test di integrazione e metriche per stadio. Non riscrivere moduli prima di sapere quale stadio limita la frequenza.
