import io
import json
from robi.memory import MemoryStore
from robi.curator import curate

class FakeResponse:
    def __init__(self, verdicts):
        self.verdicts=verdicts
    def __enter__(self):
        payload={"message":{"content":json.dumps({"decisions":self.verdicts})}}
        return io.BytesIO(json.dumps(payload).encode())
    def __exit__(self,*_): return False

def candidate(fact, action="add", target_id=None, category="preference"):
    return {"candidate":{"fact":fact,"category":category,"evidence":fact},
            "action":action,"target_id":target_id,"reason":""}

def decision(index, accepted=True, sensitive=False, confidence=0.99, supported=True):
    return {"index":index,"decision":"accept" if accepted else "reject",
            "confidence":confidence,"sensitive":sensitive,"supported":supported,"reason":"Controllo fonte"}

def test_curator_accepts_only_high_confidence_and_audits(tmp_path):
    m=MemoryStore(tmp_path/"memory.sqlite3")
    proposals=[candidate("Mi piace il mare"),candidate("Mi piace la montagna")]
    results=curate(proposals,m,transport=lambda *_args,**_kwargs:FakeResponse([
        decision(0),decision(1,confidence=.7)]))
    assert len(results["accepted"])==1
    assert len(m.list())==1
    assert m.list()[0]["fact"]=="Mi piace il mare"
    assert len(m.curator_events())==2
    m.close()

def test_curator_fails_closed_on_sensitive_and_unsupported():
    m=MemoryStore(":memory:")
    proposals=[candidate("Informazione privata"),candidate("Una deduzione")]
    results=curate(proposals,m,transport=lambda *_a,**_kw:FakeResponse([
        decision(0,sensitive=True),decision(1,supported=False)]))
    assert len(results["accepted"])==0
    assert m.list()==[]
    m.close()

def test_curator_does_not_silently_update_existing_memory():
    m=MemoryStore(":memory:")
    old=m.add("preference","Preferisco il mare")
    proposal=candidate("Preferisco la montagna",action="update",target_id=old["id"])
    outcome=curate([proposal],m,transport=lambda *_a,**_kw:FakeResponse([decision(0)]))
    assert len(outcome["review"])==1
    assert m.list()[0]["fact"]=="Preferisco il mare"
    m.close()
