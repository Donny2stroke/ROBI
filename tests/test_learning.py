from robi.learning import suggest_memories
from unittest.mock import patch
import io,json

def test_suggestions_require_exact_user_evidence():
    history=[{"role":"user","content":"Mi piace programmare in Python"},
             {"role":"assistant","content":"Adori i videogiochi"}]
    class Response:
        def __enter__(self): return io.BytesIO(json.dumps({"message":{"content":json.dumps({"suggestions":[
            {"category":"preference","fact":"Mi piace Python","evidence":"Mi piace programmare in Python"},
            {"category":"preference","fact":"Adoro videogiochi","evidence":"Adori i videogiochi"}
        ]})}}).encode())
        def __exit__(self,*args): pass
    with patch("robi.learning.urlopen",return_value=Response()):
        result=suggest_memories(history)
    assert len(result)==1
    assert result[0]["fact"]=="Mi piace Python"

def test_no_user_messages_no_request():
    assert suggest_memories([{"role":"assistant","content":"Ciao"}])==[]
