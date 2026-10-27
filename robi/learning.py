"""Suggerimenti di memoria AI: mai salvati senza conferma."""
import json
from urllib.request import Request, urlopen

CATEGORIES = {"identity", "preference", "interaction"}
SCHEMA = {"type":"object","properties":{"suggestions":{"type":"array","items":{"type":"object",
          "properties":{"category":{"type":"string"},"fact":{"type":"string"},"evidence":{"type":"string"}},
          "required":["category","fact","evidence"],"additionalProperties":False}}},
          "required":["suggestions"],"additionalProperties":False}

def suggest_memories(history, model="gemma3:4b", endpoint="http://127.0.0.1:11434/api/chat"):
    user_messages = [m["content"] for m in history if m.get("role")=="user" and isinstance(m.get("content"),str)]
    if not user_messages:
        return []
    prompt = ("Estrai massimo TRE possibili ricordi SOLO da dichiarazioni esplicite dell'utente. "
              "Non inferire nome, hobby, salute, emozioni o preferenze da domande, supposizioni, "
              "o dalle risposte dell'assistente. Evita informazioni sensibili. "
              "Ogni candidato deve contenere categoria identity/preference/interaction, "
              "una frase sintetica fact ed evidence COPIATA ESATTAMENTE da un messaggio utente. "
              "Se non vi sono dichiarazioni utili, restituisci lista vuota.")
    body={"model":model,"stream":False,"think":False,"format":SCHEMA,
          "messages":[{"role":"system","content":prompt},{"role":"user","content":json.dumps(user_messages[-12:],ensure_ascii=False)}],
          "options":{"num_predict":320,"num_ctx":4096}}
    request=Request(endpoint,data=json.dumps(body).encode("utf-8"),headers={"Content-Type":"application/json"},method="POST")
    with urlopen(request,timeout=90) as response:
        result=json.load(response)
    content=result.get("message",{}).get("content","")
    data=json.loads(content)
    output=[]
    for candidate in data.get("suggestions",[])[:3]:
        if not isinstance(candidate,dict): continue
        category,fact,evidence=(candidate.get(k) for k in ("category","fact","evidence"))
        if (category not in CATEGORIES or not isinstance(fact,str) or not 1<=len(fact.strip())<=300
            or not isinstance(evidence,str) or not evidence.strip()
            or not any(evidence in msg for msg in user_messages)):
            continue
        output.append({"category":category,"fact":fact.strip(),"evidence":evidence})
    return output
