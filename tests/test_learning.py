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


def test_five_distinct_explicit_facts_are_accepted():
    history=[{"role":"user","content":"fact "+str(i)} for i in range(5)]
    candidates=[{"category":"identity","fact":"fact "+str(i),"evidence":"fact "+str(i)} for i in range(5)]
    class Response:
        def __enter__(self):
            return io.BytesIO(json.dumps({"message":{"content":json.dumps({"suggestions":candidates})}}).encode())
        def __exit__(self,*args): pass
    with patch("robi.learning.urlopen",return_value=Response()):
        assert len(suggest_memories(history))==5


def test_empty_model_output_falls_back_to_explicit_work_facts():
    history=[
        {"role":"user","content":"Conosci IBM? Io lavoro per questa azienda da 1 anno"},
        {"role":"assistant","content":"Cosa fai lì?"},
        {"role":"user","content":"sviluppo web per il cliente Campari"},
        {"role":"user","content":"uso wordpress e gutenberg come principale tecnologia"},
        {"role":"user","content":"Mi piacerebbe imparare meglio React"},
    ]
    class Response:
        def __enter__(self):
            return io.BytesIO(json.dumps({"message":{"content":'{"suggestions":[]}'}}).encode())
        def __exit__(self,*args): pass
    with patch("robi.learning.urlopen",return_value=Response()):
        results=suggest_memories(history)
    assert len(results)==4
    assert any("IBM" in x["fact"] for x in results)
    assert any("Campari" in x["fact"] for x in results)
    assert any("gutenberg" in x["fact"] for x in results)
    assert any("React" in x["fact"] for x in results)
    assert all(x["evidence"] in [m["content"] for m in history if m["role"]=="user"] for x in results)

def test_fallback_normalizes_wordpress_gutenberg_campari():
    from robi.learning import explicit_fallback
    proposals=explicit_fallback(["si sviluppo in wordpress + gutenberg per Campari"])
    assert proposals[0]["fact"]=="Utilizzo WordPress e Gutenberg per lo sviluppo web del cliente Campari"
    assert proposals[0]["evidence"]=="si sviluppo in wordpress + gutenberg per Campari"
