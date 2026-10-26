# ROBI v0.3.1 — AI Expression Lab

## Intento
Lavorare su classificazioni locali di **espressioni facciali visibili**, non sulla determinazione dei sentimenti. Classificazioni soggette a errori, distorsioni del dataset, illuminazione, posa e differenze individuali. Non conserviamo risultati su disco e non facciamo identificazione.

## Installazione (Windows PowerShell)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,emotion]"
Copy-Item .env.example .env
```
In `.env`: `ROBI_AI_EXPRESSION_ENABLED=1`, `ROBI_AI_EXPRESSION_HZ=3`, `ROBI_CAMERA_BACKEND=MSMF`, `ROBI_CAMERA_FOURCC=YUY2`.

```powershell
.\.venv\Scripts\robi.exe doctor
.\.venv\Scripts\robi.exe start
.\.venv\Scripts\python.exe -m pytest
```
Modelli Face Detector e Face Landmarker vanno inseriti in `models/` come prima. DeepFace installa altre dipendenze e **può scaricare i pesi al primo utilizzo**: dopo quel passaggio l'inferenza è locale. Controllare termini e licenze dei modelli prima di distribuirli.

## Come leggere il codice
- `robi/ai_expression.py`: `ExpressionClassifier` è un Protocol: si può sostituire DeepFace con ONNX più avanti. `DeepFaceClassifier` fa l'inferenza su un crop BGR del volto. `ExpressionWorker` ha una mailbox latest-only e un thread dedicato: il classificatore non blocca webcam né streaming. Il limite Hz è il tempo minimo tra inferenze completate, non una garanzia sugli FPS.
- `robi/camera.py`: MediaPipe localizza il volto; solo il ritaglio viene copiato e pubblicato al worker. Se il volto non è presente, il risultato viene cancellato. `status()` espone output e latenza alla dashboard.
- `robi/static/index.html`: visualizzazione diagnostica; gli score NON sono probabilità calibrate di emozioni.

## Esperimento
1. Avvia con AI disattivata, annota `acquisizione FPS`, `visione FPS`, `lettura ms`.
2. Attiva AI, riavvia, e annota le stesse metriche + `Inferenza ms`.
3. Prova diversi gesti facciali e diverse angolazioni: osserva dove il classificatore sbaglia.
4. Se perde troppi FPS, riduci `ROBI_AI_EXPRESSION_HZ` a 1; per il Raspberry Pi valuteremo un modello ONNX più leggero.

## Limiti progettuali
Non usare output per diagnosi, profili psicologici, decisioni ad alto impatto, o attribuzioni certe di emozioni. Per la conversazione futura useremo solo osservazioni deboli e conferme verbali esplicite, con consenso. Il modello non riceve audio né invia video attraverso API remote.
