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
    m=MemoryStore(":memory:",embedder=FakeEmbeddingClient())
    m.add("preference","Mi piace il gelato al pistacchio")
    m.add("preference","Adoro programmare in Python")
    m.add("interaction","Preferisco risposte dirette")
    ctx=m.relevant_context("Come funziona Python?")
    assert "Python" in ctx
    assert "risposte dirette" in ctx
    assert "pistacchio" not in ctx  # embedding: esclude temi non pertinenti
    m.close()

def test_search_handles_punctuation_and_unicode_words():
    m=MemoryStore(":memory:")
    m.add("preference","Adoro programmare in Python")
    m.add("preference","Preferisco il caffè")
    assert any("Python" in x["fact"] for x in m.search("Come funziona Python?"))
    assert any("caffè" in x["fact"] for x in m.search("Ti piace il caffè?"))
    assert not m.search("??!!")
    m.close()

def test_topic_followup_and_style_context():
    m=MemoryStore(":memory:")
    m.add("preference","Mi piace il gelato al pistacchio")
    m.add("interaction","Preferisco risposte naturali")
    ctx=m.relevant_context("Quale gusto di gelato mi piace? Ti ricordi se preferisco la vaniglia?")
    assert "gelato al pistacchio" in ctx
    assert "interaction regolano soltanto lo stile" in ctx
    assert m.search("Ti ricordi se preferisco la vaniglia?")==[]
    m.close()


def test_small_memory_retains_pistachio():
    m=MemoryStore(":memory:")
    m.add("preference","Il mio gusto preferito è pistacchio")
    m.add("interaction","Risposte naturali")
    assert "pistacchio" in m.relevant_context("Quale gusto di gelato mi piace?")
    m.close()

class FakeEmbeddingClient:
    def embed(self,texts):
        def vector(text):
            value=text.lower()
            if "gelato" in value or "pistacchio" in value or "gusto" in value:
                return [1.0,0.0,0.0]
            if "python" in value or "programmare" in value:
                return [0.0,1.0,0.0]
            return [0.0,0.0,1.0]
        return [vector(text) for text in texts]

def test_hybrid_semantic_retrieves_synonym_and_excludes_noise():
    m=MemoryStore(":memory:",embedder=FakeEmbeddingClient())
    m.add("preference","Il mio gusto preferito è pistacchio")
    m.add("preference","Adoro programmare in Python")
    results=m.retrieve("Che gelato dovrei ordinare?")
    assert results[0]["fact"]=="Il mio gusto preferito è pistacchio"
    assert all("Python" not in x["fact"] for x in results)
    m.close()

def test_hybrid_fallback_when_embedding_server_missing():
    class Offline:
        def embed(self,texts):
            raise OSError("offline")
    m=MemoryStore(":memory:",embedder=Offline())
    m.add("preference","Il mio gusto preferito è pistacchio")
    assert "pistacchio" in m.relevant_context("Quale gelato ti piace?")
    m.close()

def test_vector_cache_is_invalidated_after_edit():
    class Counting:
        model="fake"
        def __init__(self):
            self.calls=[]
        def embed(self,texts):
            self.calls.append(list(texts))
            return [[float("pistacchio" in text.lower()),float("python" in text.lower()),1.0] for text in texts]
    embedder=Counting()
    m=MemoryStore(":memory:",embedder=embedder)
    item=m.add("preference","Mi piace il pistacchio")
    m.retrieve("pistacchio")
    assert len(embedder.calls[-1])==2
    m.retrieve("pistacchio")
    assert len(embedder.calls[-1])==1
    m.update(item["id"],"preference","Mi piace Python")
    m.retrieve("Python")
    assert len(embedder.calls[-1])==2
    m.close()

def test_revised_preference_survives_restart_without_stale_vector(tmp_path):
    path=tmp_path/"smart.sqlite3"
    first=MemoryStore(path,embedder=FakeEmbeddingClient())
    saved=first.add("preference","Mi piace il gelato al pistacchio")
    first.retrieve("Che gelato mi consigli?")
    first.update(saved["id"],"preference","Mi piace il gelato al cioccolato")
    assert first.db.execute("SELECT count(*) FROM memory_vectors WHERE memory_id=?",(saved["id"],)).fetchone()[0]==0
    first.close()

    second=MemoryStore(path,embedder=FakeEmbeddingClient())
    context=second.relevant_context("Quale gusto di gelato preferisco?")
    assert "cioccolato" in context
    assert "pistacchio" not in context
    second.close()

def test_delete_clears_persisted_vector():
    m=MemoryStore(":memory:",embedder=FakeEmbeddingClient())
    item=m.add("preference","Mi piace il gelato al pistacchio")
    m.retrieve("gelato")
    assert m.db.execute("SELECT count(*) FROM memory_vectors").fetchone()[0]==1
    m.delete(item["id"])
    assert m.db.execute("SELECT count(*) FROM memory_vectors").fetchone()[0]==0
    m.close()
