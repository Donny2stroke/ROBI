import io
import json
from robi.consolidation import propose_consolidation
from robi.memory import MemoryStore

def test_identical_memory_is_duplicate_without_ai_call():
    mem=MemoryStore(":memory:")
    item=mem.add("preference","Mi piace il gelato al pistacchio")
    candidates=[{"category":"preference","fact":"Mi piace il gelato al pistacchio","evidence":"Mi piace il gelato al pistacchio"}]
    proposals=propose_consolidation([],mem,candidates=candidates,
                                    transport=lambda *_args,**_kwargs: (_ for _ in ()).throw(AssertionError("unexpected call")))
    assert proposals[0]["action"]=="duplicate"
    assert proposals[0]["target_id"]==item["id"]
    assert len(mem.list())==1
    mem.close()

def test_update_is_proposed_without_modifying_db():
    mem=MemoryStore(":memory:")
    item=mem.add("preference","Mi piace il gelato al pistacchio")
    candidates=[{"category":"preference","fact":"Ora preferisco il cioccolato","evidence":"Ora preferisco il cioccolato"}]
    class Reply:
        def __enter__(self):
            data={"message":{"content":json.dumps({"decisions":[{"index":0,"action":"update","target_id":item["id"],"reason":"Correzione esplicita"}]})}}
            return io.BytesIO(json.dumps(data).encode())
        def __exit__(self,*_): return False
    result=propose_consolidation([],mem,candidates=candidates,transport=lambda *_args,**_kw:Reply())
    assert result[0]["action"]=="update"
    assert mem.list()[0]["fact"]=="Mi piace il gelato al pistacchio"
    mem.close()

def test_invalid_ai_target_downgrades_to_add():
    mem=MemoryStore(":memory:")
    candidates=[{"category":"preference","fact":"Mi piace la pizza","evidence":"Mi piace la pizza"}]
    class Reply:
        def __enter__(self):
            data={"message":{"content":json.dumps({"decisions":[{"index":0,"action":"update","target_id":999,"reason":"Cambio"}]})}}
            return io.BytesIO(json.dumps(data).encode())
        def __exit__(self,*_): return False
    result=propose_consolidation([],mem,candidates=candidates,transport=lambda *_args,**_kw:Reply())
    assert result[0]["action"]=="add" and result[0]["target_id"] is None
    mem.close()

def test_vector_map_and_deletion():
    class Embedder:
        model="fake"
        def embed(self,texts):
            return [[float("gelato" in t),float("python" in t),1.0] for t in texts]
    mem=MemoryStore(":memory:",embedder=Embedder())
    first=mem.add("preference","gelato")
    mem.add("preference","python")
    mem.retrieve("gelato")
    result=mem.vector_map()
    assert len(result["points"])==2
    assert all(-1<=p["x"]<=1 and -1<=p["y"]<=1 for p in result["points"])
    mem.delete(first["id"])
    assert len(mem.vector_map()["points"])==1
    mem.close()
