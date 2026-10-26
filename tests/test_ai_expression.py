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
