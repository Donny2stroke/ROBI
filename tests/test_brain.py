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

def test_clean_answer_rejects_reasoning():
    from robi.brain import clean_answer
    assert clean_answer("<think>Draft</think>Ciao!") == "Ciao!"
    for text in ("Okay, the user said hello.", "Thinking... draft"):
        try:
            clean_answer(text)
            assert False, "reasoning exposed"
        except RuntimeError:
            pass
