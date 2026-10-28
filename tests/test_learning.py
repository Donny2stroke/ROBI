"""Tests for domain-agnostic memory extraction with grounded evidence."""
import io
import json
from unittest.mock import patch
from robi.learning import suggest_memories

def fake_response(candidates):
    class Response:
        def __enter__(self):
            return io.BytesIO(json.dumps({"message":{"content":json.dumps(
                {"suggestions":candidates})}}).encode())
        def __exit__(self,*args):
            return False
    return Response()

def test_evidence_is_original_user_message_not_assistant():
    history=[{"role":"user","content":"Mi piace programmare in Python"},
             {"role":"assistant","content":"Adori i videogiochi"}]
    candidates=[
        {"category":"preference","fact":"Mi piace Python","evidence_index":0},
        {"category":"preference","fact":"Adoro videogiochi","evidence_index":1},
    ]
    with patch("robi.learning.urlopen",return_value=fake_response(candidates)):
        result=suggest_memories(history)
    assert len(result)==1
    assert result[0]["evidence"]=="Mi piace programmare in Python"

def test_no_user_messages_no_request():
    assert suggest_memories([{"role":"assistant","content":"Ciao"}])==[]

def test_generic_multiple_topics_and_source_indices():
    statements=[
        "Studio botanica da due anni",
        "Vorrei imparare a suonare il pianoforte",
        "Lavoro a un progetto di robotica",
        "Preferisco risposte brevi",
        "Ho adottato un cane di nome Rex",
    ]
    candidates=[{"category":"identity","fact":x,"evidence_index":i}
                for i,x in enumerate(statements)]
    history=[{"role":"user","content":x} for x in statements]
    with patch("robi.learning.urlopen",return_value=fake_response(candidates)):
        found=suggest_memories(history)
    assert len(found)==5
    assert all(found[i]["evidence"]==statements[i] for i in range(5))

def test_empty_model_output_does_not_invent_or_apply_regex_facts():
    history=[{"role":"user","content":"Lavoro in un'azienda"},
             {"role":"user","content":"Mi piace la musica"}]
    with patch("robi.learning.urlopen",return_value=fake_response([])):
        assert suggest_memories(history)==[]

def test_invalid_indices_and_duplicate_candidates_ignored():
    history=[{"role":"user","content":"Mi piace il mare"}]
    candidates=[
        {"category":"preference","fact":"Mi piace il mare","evidence_index":0},
        {"category":"preference","fact":"Mi piace il mare","evidence_index":0},
        {"category":"preference","fact":"Mi piace la neve","evidence_index":20},
    ]
    with patch("robi.learning.urlopen",return_value=fake_response(candidates)):
        result=suggest_memories(history)
    assert len(result)==1
