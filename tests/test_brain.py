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
    assert Conversation().model=="qwen3:4b"
