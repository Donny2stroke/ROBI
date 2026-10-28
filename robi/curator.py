"""Autonomous, auditable Memory Curator. Never trusts unverified suggestions."""
import json
from urllib.request import Request, urlopen

SCHEMA={"type":"object","properties":{"decisions":{"type":"array","items":{
"type":"object","properties":{"index":{"type":"integer"},"decision":{"type":"string"},
"confidence":{"type":"number"},"sensitive":{"type":"boolean"},"supported":{"type":"boolean"},
"reason":{"type":"string"},"relation":{"type":"string"},"related_id":{"type":"integer"},"category":{"type":"string"}},"required":["index","decision","confidence","sensitive","supported","reason","relation","related_id","category"],
"additionalProperties":False}}},"required":["decisions"],"additionalProperties":False}

def curate(proposals, memory, model="gemma3:4b",
           endpoint="http://127.0.0.1:11434/api/chat", transport=urlopen):
    """Independent evaluation; auto-create only strongly grounded non-sensitive facts.

    Updates remain suggestions until an explicit, auditable correction workflow exists.
    """
    valid=[p for p in proposals if isinstance(p,dict) and isinstance(p.get("candidate"),dict)
           and isinstance(p["candidate"].get("fact"),str) and p["candidate"]["fact"].strip()
           and isinstance(p["candidate"].get("evidence"),str) and p["candidate"]["evidence"].strip()
           and p.get("action") in ("add","duplicate","update")]
    if not valid:
        return {"accepted":[],"rejected":[],"review":[]}
    existing=memory.list()
    prompt=("Sei il responsabile indipendente della memoria di un assistente. "
            "Per ogni proposta, controlla SOLTANTO la fonte testuale dell'utente; "
            "non usare inferenze su altri messaggi. "
            "Scegli accept oppure reject. supported=true SOLO se tutta la frase "
            "e' pienamente giustificata dalla fonte, senza aggiunte. "
            "sensitive=true per dati privati delicati (salute, religione, politica, "
            "credenziali, dati finanziari, intimità, identificativi) o se incerto. "
            "confidence 0..1 indica sicurezza sulla fonte e utilità a lungo termine. "
            "Scarta dubbi, richieste momentanee, speculazioni, domande e ridondanze. "
            "Confronta ogni proposta con tutti i ricordi esistenti. "
            "relation: independent, duplicate, conflict o update. "
            "related_id: ID del ricordo collegato, oppure 0. "
            "Un cambiamento di preferenza va classificato come conflict o update. "
            "category: identity per informazioni personali o professionali, "
            "preference per gusti e obiettivi, interaction per stile di dialogo. "
            "Non confondere un testo plausibile con un fatto confermato.")
    request=Request(endpoint,data=json.dumps({"model":model,"stream":False,"think":False,
        "format":SCHEMA,"messages":[{"role":"system","content":prompt},
        {"role":"user","content":json.dumps({"proposals":[{"index":i,"proposal":p} for i,p in enumerate(valid)],"existing_memories":existing[-100:]},ensure_ascii=False)}],
        "options":{"num_ctx":4096,"num_predict":450}}).encode(),
        headers={"Content-Type":"application/json"},method="POST")
    with transport(request,timeout=45) as response:
        verdict=json.loads(json.load(response)["message"]["content"])
    decisions={d.get("index"):d for d in verdict.get("decisions",[])
               if isinstance(d,dict) and type(d.get("index")) is int}
    result={"accepted":[],"rejected":[],"review":[]}
    for i,p in enumerate(valid):
        d=decisions.get(i,{})
        confidence=d.get("confidence",0)
        approved=(d.get("decision")=="accept" and d.get("supported") is True
                  and d.get("sensitive") is False and type(confidence) in (int,float)
                  and 0.95<=confidence<=1)
        fact=p["candidate"]["fact"].strip()
        category=d.get("category")
        if category not in ("identity","preference","interaction"):
            category=p["candidate"].get("category")
        relation=d.get("relation")
        related=d.get("related_id")
        linked=type(related) is int and related in {m["id"] for m in existing}
        if category!=p["candidate"].get("category"):
            p={**p,"candidate":{**p["candidate"],"category":category}}
        if p["action"]=="duplicate":
            outcome="rejected"
        elif relation in ("duplicate","conflict","update") and linked:
            outcome="rejected" if relation=="duplicate" else "review"
            p={**p,"target_id":related,"reason":str(d.get("reason",""))[:250]}
        elif relation!="independent":
            outcome="review"
        elif p["action"]=="update":
            outcome="review"  # No silent overwrites while conflict handling is experimental.
        elif approved and category in ("identity","preference","interaction"):
            # Avoid exact duplicates even if the upstream model missed them.
            exists=any(m["category"]==category and m["fact"].casefold()==fact.casefold()
                       for m in memory.list())
            if exists:
                outcome="rejected"
            else:
                saved=memory.add(category,fact)
                outcome="accepted"
                p={**p,"saved_id":saved["id"]}
        else:
            outcome="rejected"
        memory.record_curator_event(outcome, p, d)
        result[outcome].append(p)
    return result
