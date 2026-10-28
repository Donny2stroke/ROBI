from unittest.mock import patch
from robi.brain import Conversation

def test_rejects_empty_and_oversized_messages():
    c=Conversation()
    for text in ("", "  ", "x"*2001):
        try:
            c.reply(text)
            assert False, "messaggio non rifiutato"
        except ValueError:
            pass

def test_history_can_be_cleared():
    c=Conversation()
    c._history=[{"role":"user","content":"ciao"}]
    assert len(c.history())==1
    c.clear()
    assert c.history()==[]

def test_model_default():
    assert Conversation().model=="gemma3:4b"

def test_clean_answer_rejects_reasoning():
    from robi.brain import clean_answer
    assert clean_answer("<think>Draft</think>Ciao!") == "Ciao!"
    for text in ("Okay, the user said hello.", "Thinking... draft"):
        try:
            clean_answer(text)
            assert False, "reasoning exposed"
        except RuntimeError:
            pass

def test_extract_structured_final_reply():
    from robi.brain import extract_reply
    assert extract_reply({"message":{"content":'{"reply":"Ciao, sono ROBI!"}'}}) == "Ciao, sono ROBI!"
    try:
        extract_reply({"message":{"content":'{"reply":"Okay, the user said hello."}'}})
        assert False
    except RuntimeError:
        pass

def test_followup_includes_user_facts_in_model_context():
    """Il backend deve ricevere il turno precedente e la domanda corrente."""
    import io
    import json
    from unittest.mock import patch
    from robi.brain import Conversation

    class FakeResponse:
        def __init__(self, answer):
            self.data = io.BytesIO(json.dumps({"message":{"content":json.dumps({"reply":answer})}}).encode())
        def __enter__(self): return self.data
        def __exit__(self, *_): return False

    sent = []
    def fake_urlopen(request, timeout):
        payload = json.loads(request.data)
        sent.append(payload)
        return FakeResponse("Risposta di prova")

    c = Conversation()
    with patch("robi.brain.urlopen", side_effect=fake_urlopen):
        c.reply("Mi chiamo Marco e mi piace la pizza")
        c.reply("Chi sono e cosa mi piace?")

    messages = sent[-1]["messages"]
    assert [m["role"] for m in messages] == ["system", "system", "system", "user", "assistant", "user"]
    assert messages[3]["content"] == "Mi chiamo Marco e mi piace la pizza"
    assert messages[-1]["content"] == "Chi sono e cosa mi piace?"
    assert "TU sei ROBI" in messages[0]["content"]

def test_switch_model_clears_history():
    c=Conversation()
    c._history=[{"role":"user","content":"Mi chiamo Marco"}]
    info=c.set_model("qwen3:4b")
    assert info["model"]=="qwen3:4b"
    assert info["messages"]==[]
    assert c.model_status()["model"]=="qwen3:4b"

def test_switch_to_same_model_preserves_history():
    c=Conversation()
    c._history=[{"role":"user","content":"Ciao"}]
    assert len(c.set_model("gemma3:4b")["messages"])==1

def test_rejects_unsupported_model():
    c=Conversation()
    try:
        c.set_model("http://untrusted.example/model")
        assert False
    except ValueError:
        pass

def test_gemma_multimodal_markers_are_cleaned():
    from robi.brain import clean_answer
    assert clean_answer("Python è semplice. <start_of_image> È leggibile.") == "Python è semplice. È leggibile."
    assert clean_answer("<start_of_image> Ciao.") == "Ciao."
