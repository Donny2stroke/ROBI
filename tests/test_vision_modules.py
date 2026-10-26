from robi.frame_buffer import LatestFrameBuffer
from robi.expression import from_blendshapes
from types import SimpleNamespace

def test_latest_only():
    buf=LatestFrameBuffer()
    buf.publish("one")
    buf.publish("two")
    assert buf.latest()==(2,"two")
    assert buf.wait_next(1, .01)==(2,"two")

def test_observable_signals_not_emotions():
    data=[SimpleNamespace(category_name="mouthSmileLeft",score=.6),SimpleNamespace(category_name="mouthSmileRight",score=.8)]
    result=from_blendshapes(data).to_dict()
    assert round(result['smile'],2)==.7
    assert 'happy' not in result and 'angry' not in result
