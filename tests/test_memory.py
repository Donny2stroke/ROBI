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
