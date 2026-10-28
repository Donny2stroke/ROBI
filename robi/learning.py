"""Estrazione generale di ricordi: il modello propone, il codice verifica la provenienza."""
import json
from urllib.request import Request, urlopen

CATEGORIES = {"identity", "preference", "interaction"}
SCHEMA = {"type":"object","properties":{"suggestions":{"type":"array","items":{
    "type":"object","properties":{"category":{"type":"string"},
    "fact":{"type":"string"},"evidence_index":{"type":"integer"}},
    "required":["category","fact","evidence_index"],"additionalProperties":False}}},
    "required":["suggestions"],"additionalProperties":False}

def suggest_memories(history, model="gemma3:4b",
                     endpoint="http://127.0.0.1:11434/api/chat"):
    user_messages=[m["content"] for m in history
                   if m.get("role")=="user" and isinstance(m.get("content"),str)][-12:]
    if not user_messages:
        return []
    prompt=(
        "Estrai fino a 5 informazioni personali utili e durevoli esplicitamente "
        "comunicate dall'utente, indipendentemente dall'argomento. "
        "Possono riguardare identità e contesto (identity), gusti e obiettivi "
        "(preference), oppure indicazioni sul modo di interagire (interaction). "
        "Riscrivi ogni fatto come proposizione autonoma, breve e fedele, "
        "eliminando domande introduttive, esitazioni e ripetizioni. "
        "Quando un messaggio contiene più fatti distinti, separali. "
        "Usa gli altri messaggi utente per risolvere riferimenti contestuali, "
        "senza inventare collegamenti o attribuire all'utente ipotesi dell'assistente. "
        "Evita dati sensibili non richiesti. "
        "Per ogni fatto indica evidence_index: indice zero-based del messaggio "
        "utente che fornisce prova diretta del fatto. "
        "Se non ci sono fatti verificabili, restituisci suggestions vuoto. "
        "Non aggiungere contenuti non sostenuti dalla fonte."
    )
    payload={"model":model,"stream":False,"think":False,"format":SCHEMA,
             "messages":[{"role":"system","content":prompt},
                         {"role":"user","content":json.dumps(user_messages,ensure_ascii=False)}],
             "options":{"num_predict":700,"num_ctx":4096}}
    request=Request(endpoint,data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type":"application/json"},method="POST")
    with urlopen(request,timeout=90) as response:
        result=json.load(response)
    data=json.loads(result.get("message",{}).get("content","{}"))
    output=[]
    for candidate in data.get("suggestions",[])[:12]:
        if not isinstance(candidate,dict):
            continue
        category=candidate.get("category")
        fact=candidate.get("fact")
        index=candidate.get("evidence_index")
        if (category not in CATEGORIES or not isinstance(fact,str)
                or not 1<=len(fact.strip())<=300
                or type(index) is not int or not 0<=index<len(user_messages)):
            continue
        entry={"category":category,"fact":fact.strip(),
               "evidence":user_messages[index]}
        if not any(x["category"]==entry["category"] and
                   x["fact"].casefold()==entry["fact"].casefold() for x in output):
            output.append(entry)
        if len(output)==5:
            break
    return output
