import time
from robi.ai_expression import normalize_scores, ExpressionWorker

def test_normalization():
    scores=normalize_scores({"happy":150,"sad":-2,"neutral":40})
    assert scores["happy"]==100 and scores["sad"]==0 and scores["neutral"]==40
    assert len(scores)==7

def test_worker_isolated():
    class Fake:
        def predict(self, frame): return {"happy":42}
    worker=ExpressionWorker(classifier_factory=Fake,hz=10)
    worker.start()
    worker.publish("dummy-frame")
    for _ in range(100):
        if worker.snapshot()["scores"]: break
        time.sleep(.01)
    assert worker.snapshot()["scores"]=={"happy":42}
    worker.clear()
    assert worker.snapshot()["scores"] is None
    worker.stop()


def test_sequence_increments_only_after_inference():
    class Fake:
        def predict(self, frame):
            return {"neutral": 72.0}
    worker = ExpressionWorker(classifier_factory=Fake, hz=10)
    assert worker.snapshot()["sequence"] == 0
    worker.start()
    worker.publish("frame-1")
    for _ in range(100):
        if worker.snapshot()["sequence"] >= 1:
            break
        time.sleep(0.01)
    first = worker.snapshot()["sequence"]
    assert first == 1
    assert worker.snapshot()["sequence"] == first
    worker.publish("frame-2")
    for _ in range(100):
        if worker.snapshot()["sequence"] >= 2:
            break
        time.sleep(0.01)
    assert worker.snapshot()["sequence"] == 2
    worker.clear()
    assert worker.snapshot()["scores"] is None
    worker.stop()
