"""Valutazione AI esplicita, separata dalla risposta e senza autoapprendimento dei pesi."""
import json
from urllib.request import Request, urlopen

SCHEMA={"type":"object","properties":{"relevance":{"type":"integer"},"clarity":{"type":"integer"},
"tone":{"type":"integer"},"grounding":{"type":"integer"},"reason":{"type":"string"}},
"required":["relevance","clarity","tone","grounding","reason"],"additionalProperties":False}

def evaluate(history,model="gemma3:4b",endpoint="http://127.0.0.1:11434/api/chat",transport=urlopen):
    if len(history)<2 or history[-2].get("role")!="user" or history[-1].get("role")!="assistant":
        raise ValueError("Occorre almeno uno scambio domanda-risposta completo.")
    prompt=("Sei un revisore indipendente della qualità di una risposta. "
            "Valuta da 1 a 5 pertinenza, chiarezza, adeguatezza del tono e supporto nei messaggi. "
            "Non presumere che il modello abbia sempre ragione: verifica la risposta rispetto al contesto. "
            "Non accertare fatti esterni che non puoi verificare. Motiva brevemente in italiano.")
    data={"model":model,"stream":False,"think":False,"format":SCHEMA,
          "messages":[{"role":"system","content":prompt},
                      {"role":"user","content":json.dumps(history[-8:],ensure_ascii=False)}],
          "options":{"num_ctx":4096,"num_predict":240}}
    req=Request(endpoint,data=json.dumps(data).encode(),headers={"Content-Type":"application/json"},method="POST")
    with transport(req,timeout=90) as response:
        result=json.load(response)
    scores=json.loads(result["message"]["content"])
    if any(type(scores.get(key)) is not int or not 1<=scores[key]<=5
           for key in ("relevance","clarity","tone","grounding")):
        raise ValueError("Punteggi AI non validi.")
    if not isinstance(scores.get("reason"),str) or len(scores["reason"])>1000:
        raise ValueError("Motivazione AI non valida.")
    return {**scores,"model":model,"automatic":True}
