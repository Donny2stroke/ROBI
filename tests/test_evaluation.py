import io,json
import pytest
from robi.evaluation import evaluate

def test_evaluation_validates_scores():
    class Fake:
        def __enter__(self):
            obj={"message":{"content":json.dumps({"relevance":5,"clarity":4,"tone":5,"grounding":4,"reason":"Coerente"})}}
            return io.BytesIO(json.dumps(obj).encode())
        def __exit__(self,*args): pass
    result=evaluate([{"role":"user","content":"Ciao"},{"role":"assistant","content":"Ciao!"}],
                    transport=lambda request,timeout: Fake())
    assert result["relevance"]==5 and result["automatic"] is True

def test_evaluation_requires_turn():
    with pytest.raises(ValueError):
        evaluate([])
