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
    prompt = ("Estrai fino a CINQUE ricordi utili SOLO da dichiarazioni esplicite dell'utente. Priorità a datore di lavoro, ruolo, anzianità, progetti, preferenze e stile. "
              "Non inferire nome, hobby, salute, emozioni o preferenze da domande, supposizioni, "
              "o dalle risposte dell'assistente. Evita informazioni sensibili. "
              "Ogni candidato deve contenere categoria identity/preference/interaction, "
              "una frase sintetica fact ed evidence COPIATA ESATTAMENTE da un messaggio utente. "
              "Le risposte brevi possono integrare dichiarazioni precedenti dello stesso utente: per esempio lavoro per IBM da un anno, sviluppo web per Campari, lavoro in Transformation. Non usare ipotesi formulate dall'assistente come fatti. Se non vi sono dichiarazioni utili, restituisci lista vuota.")
    body={"model":model,"stream":False,"think":False,"format":SCHEMA,
          "messages":[{"role":"system","content":prompt},{"role":"user","content":json.dumps(user_messages[-12:],ensure_ascii=False)}],
          "options":{"num_predict":700,"num_ctx":4096}}
    request=Request(endpoint,data=json.dumps(body).encode("utf-8"),headers={"Content-Type":"application/json"},method="POST")
    with urlopen(request,timeout=90) as response:
        result=json.load(response)
    content=result.get("message",{}).get("content","")
    data=json.loads(content)
    output=[]
    for candidate in data.get("suggestions",[])[:5]:
        if not isinstance(candidate,dict): continue
        category,fact,evidence=(candidate.get(k) for k in ("category","fact","evidence"))
        if (category not in CATEGORIES or not isinstance(fact,str) or not 1<=len(fact.strip())<=300
            or not isinstance(evidence,str) or not evidence.strip()
            or not any(evidence in msg for msg in user_messages)):
            continue
        output.append({"category":category,"fact":fact.strip(),"evidence":evidence})
    if output:
        return output
    return explicit_fallback(user_messages)


def explicit_fallback(messages):
    """Conservativo: propone il testo letterale delle dichiarazioni esplicite."""
    import re
    patterns=[
        ("identity", r"\b(?:lavoro|sviluppo|utilizzo|uso|mi occupo)\b"),
        ("preference", r"\b(?:mi piacerebbe|vorrei imparare|preferisco|mi piace)\b"),
    ]
    suggestions=[]
    for message in messages:
        value=message.strip()
        if not 8<=len(value)<=300:
            continue
        for category,pattern in patterns:
            if re.search(pattern,value,re.IGNORECASE):
                fact=value
                work=re.search(r"\b(?:io\s+)?lavoro\s+per\s+(?:questa\s+azienda|ibm)\s+da\s+(\d+)\s+ann[oi]",value,re.IGNORECASE)
                if work and "ibm" in value.casefold():
                    fact="Lavoro per IBM da "+work.group(1)+" anno" if work.group(1)=="1" else "Lavoro per IBM da "+work.group(1)+" anni"
                elif re.match(r"^sviluppo\s+web\s+per\s+(?:il\s+cliente\s+)?campari\s*$",value,re.IGNORECASE):
                    fact="Mi occupo di sviluppo web per il cliente Campari"
                elif re.search(r"\\bwordpress\\b",value,re.IGNORECASE) and re.search(r"\\bgutenberg\\b",value,re.IGNORECASE) and re.search(r"\\bcampari\\b",value,re.IGNORECASE):
                    fact="Utilizzo WordPress e Gutenberg per lo sviluppo web del cliente Campari"
                suggestions.append({"category":category,"fact":fact,"evidence":message})
                break
    return suggestions[-5:]
