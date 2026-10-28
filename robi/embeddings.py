"""Embedding locale opzionale via Ollama. Nessun servizio cloud e nessuna API key."""
import json
import math
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

MODEL = "embeddinggemma"
ENDPOINT = "http://127.0.0.1:11434/api/embed"

class EmbeddingClient:
    def __init__(self, model=MODEL, endpoint=ENDPOINT, timeout=4):
        self.model, self.endpoint, self.timeout = model, endpoint, timeout

    def embed(self, texts):
        if not texts:
            return []
        payload=json.dumps({"model":self.model,"input":texts}).encode("utf-8")
        request=Request(self.endpoint,data=payload,headers={"Content-Type":"application/json"},method="POST")
        with urlopen(request,timeout=self.timeout) as response:
            vectors=json.load(response)["embeddings"]
        if len(vectors)!=len(texts):
            raise ValueError("Numero embedding diverso dai testi richiesti.")
        if not all(isinstance(v,list) and v and all(isinstance(x,(int,float)) and math.isfinite(x) for x in v) for v in vectors):
            raise ValueError("Embedding non valido.")
        return vectors

def cosine(a,b):
    if len(a)!=len(b) or not a:
        return 0.0
    dot=sum(x*y for x,y in zip(a,b))
    norm=math.sqrt(sum(x*x for x in a)*sum(y*y for y in b))
    return dot/norm if norm else 0.0
