"""Proposte non distruttive per consolidare i ricordi estratti dalla chat."""
import json
from urllib.request import Request, urlopen
from .learning import suggest_memories

SCHEMA={"type":"object","properties":{"decisions":{"type":"array","items":{
"type":"object","properties":{"index":{"type":"integer"},"action":{"type":"string"},
"target_id":{"type":"integer"},"reason":{"type":"string"}},
"required":["index","action","target_id","reason"],"additionalProperties":False}}},
"required":["decisions"],"additionalProperties":False}

def propose_consolidation(history, memory, model="gemma3:4b", endpoint="http://127.0.0.1:11434/api/chat", candidates=None, transport=urlopen):
    """L'AI classifica ma NON applica modifiche. Ogni aggiornamento richiede conferma."""
    candidates=suggest_memories(history,model,endpoint) if candidates is None else candidates
    if not candidates:
        return []
    candidates=[c for c in candidates if isinstance(c,dict)
                and c.get("category") in ("identity","preference","interaction")
                and isinstance(c.get("fact"),str) and 1<=len(c["fact"].strip())<=300
                and isinstance(c.get("evidence"),str) and c["evidence"].strip()]
    if not candidates:
        return []
    existing=memory.list()
    by_id={item["id"]:item for item in existing}
    # Collisioni esatte vengono identificate senza ulteriore inferenza.
    proposals=[]
    undecided=[]
    for i,c in enumerate(candidates):
        match=next((m for m in existing if m["category"]==c["category"] and
                    m["fact"].strip().casefold()==c["fact"].strip().casefold()),None)
        if match:
            proposals.append({"candidate":c,"action":"duplicate","target_id":match["id"],
                              "reason":"Ricordo identico già presente."})
        else:
            undecided.append((i,c))
    if not undecided:
        return proposals
    # Il modello vede solo candidati già ancorati a una citazione dell'utente.
    prompt=("Sei il consolidatore della memoria personale. Per ogni candidato, "
            "scegli add, update o duplicate. update/duplicate richiedono un target_id "
            "presente nei ricordi attuali. Non confondere preferenze diverse o dedurre "
            "sostituzioni senza un'esplicita correzione dell'utente. "
            "In caso di dubbio scegli add. Restituisci solo JSON.")
    payload={"model":model,"stream":False,"think":False,"format":SCHEMA,
             "messages":[{"role":"system","content":prompt},
             {"role":"user","content":json.dumps({
                 "candidates":[{"index":i,**c} for i,c in undecided],
                 "existing":existing[-100:]},ensure_ascii=False)}],
             "options":{"num_ctx":4096,"num_predict":450}}
    request=Request(endpoint,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},method="POST")
    with transport(request,timeout=90) as response:
        decisions=json.loads(json.load(response)["message"]["content"]).get("decisions",[])
    decisions_by_index={d.get("index"):d for d in decisions if isinstance(d,dict) and type(d.get("index")) is int}
    for i,c in undecided:
        d=decisions_by_index.get(i,{})
        action=d.get("action")
        target=d.get("target_id")
        valid=(type(target) is int and target in by_id and
               by_id[target]["category"]==c["category"])
        if action not in ("update","duplicate") or not valid:
            action,target="add",None
        reason=d.get("reason","")
        if not isinstance(reason,str):
            reason=""
        proposals.append({"candidate":c,"action":action,"target_id":target,
                          "reason":reason[:250]})
    return proposals
