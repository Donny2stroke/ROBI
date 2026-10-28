import pytest
from robi.memory import MemoryStore

def test_memory_persists_after_reopen(tmp_path):
    path=tmp_path/"mem.sqlite3"
    first=MemoryStore(path)
    item=first.add("preference","Mi piace programmare")
    first.close()
    second=MemoryStore(path)
    assert second.list()[0]["fact"]=="Mi piace programmare"
    assert "Mi piace programmare" in second.context()
    assert second.delete(item["id"])=={"deleted":True}
    assert second.list()==[]
    second.close()

def test_validation_and_clear():
    m=MemoryStore(":memory:")
    with pytest.raises(ValueError): m.add("unknown","test")
    with pytest.raises(ValueError): m.add("identity","")
    with pytest.raises(ValueError): m.add("identity","x"*301)
    m.add("identity","Mi chiamo Alessandro")
    assert m.clear()=={"memories":[]}
    m.close()

def test_update_and_reopen_old_schema(tmp_path):
    import sqlite3
    path=tmp_path/"old.sqlite3"
    db=sqlite3.connect(path)
    db.execute("CREATE TABLE memories (id INTEGER PRIMARY KEY AUTOINCREMENT,category TEXT NOT NULL,fact TEXT NOT NULL,source TEXT NOT NULL DEFAULT 'user_confirmed',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    db.execute("INSERT INTO memories(category,fact) VALUES('preference','Vecchia preferenza')")
    db.commit()
    db.close()
    m=MemoryStore(path)
    assert len(m.list())==1
    result=m.update(1,"preference","Nuova preferenza","Corretto dall'utente")
    assert result["fact"]=="Nuova preferenza"
    assert m.list()[0]["fact"]=="Nuova preferenza"
    m.close()

def test_relevant_context_filters_unrelated_preferences():
    m=MemoryStore(":memory:")
    m.add("preference","Mi piace il gelato al pistacchio")
    m.add("preference","Adoro programmare in Python")
    m.add("interaction","Preferisco risposte dirette")
    ctx=m.relevant_context("Come funziona Python?")
    assert "Python" in ctx
    assert "risposte dirette" in ctx
    assert "pistacchio" not in ctx
    m.close()

def test_search_handles_punctuation_and_unicode_words():
    m=MemoryStore(":memory:")
    m.add("preference","Adoro programmare in Python")
    m.add("preference","Preferisco il caffè")
    assert any("Python" in x["fact"] for x in m.search("Come funziona Python?"))
    assert any("caffè" in x["fact"] for x in m.search("Ti piace il caffè?"))
    assert not m.search("??!!")
    m.close()
