"""Client Ollama locale e cronologia della sessione (nessuna persistenza su disco)."""
import json
import threading
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from .personality import build_system_prompt

def clean_answer(content: str) -> str:
    """Non pubblicare testo deliberativo invece della risposta finale."""
    import re
    value = re.sub(r"<think>.*?</think>", "", content, flags=re.IGNORECASE | re.DOTALL).strip()
    lower = value.casefold()
    if (not value or "<think>" in lower or "thinking..." in lower
            or lower.startswith(("okay, the user", "the user said", "let me think",
                                 "i need to respond", "first, i should"))):
        raise RuntimeError("ROBI ha prodotto ragionamento invece della risposta finale. Riprova.")
    return value


def extract_reply(data):
    """Parse structured, user-facing output; never return model analysis."""
    content = data.get("message", {}).get("content", "")
    try:
        obj = json.loads(content)
    except (ValueError, TypeError):
        return clean_answer(content)
    if not isinstance(obj, dict) or not isinstance(obj.get("reply"), str):
        raise RuntimeError("Formato risposta AI non valido.")
    return clean_answer(obj["reply"])


class Conversation:
    def __init__(self, model="qwen3:4b", endpoint="http://127.0.0.1:11434/api/chat"):
        self.model, self.endpoint = model, endpoint
        self._lock = threading.Lock()
        self._history = []
    def history(self):
        with self._lock:
            return list(self._history)
    def clear(self):
        with self._lock:
            self._history.clear()
    def reply(self, message):
        if not isinstance(message, str) or not message.strip() or len(message)>2000:
            raise ValueError("Messaggio richiesto (massimo 2000 caratteri).")
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("ROBI sta ancora rispondendo: riprova tra poco.")
        try:
            user={"role":"user","content":message.strip()}
            payload={"model":self.model,"stream":False,"think":False,
                     "messages":[{"role":"system","content":build_system_prompt()}]+self._history[-16:]+[user],
                     "options":{"num_ctx":4096,"num_predict":350},
                     "format":{"type":"object","properties":{"reply":{"type":"string"}},"required":["reply"],"additionalProperties":False}}
            request=Request(self.endpoint,data=json.dumps(payload).encode("utf-8"),
                            headers={"Content-Type":"application/json"},method="POST")
            try:
                with urlopen(request,timeout=120) as response:
                    data=json.load(response)
            except (URLError, HTTPError, TimeoutError, OSError) as exc:
                raise RuntimeError("Ollama non disponibile: verifica che sia avviato e che qwen3:4b sia installato.") from exc
            answer=extract_reply(data)
            if not answer:
                raise RuntimeError("Ollama ha restituito una risposta vuota.")
            self._history.extend([user,{"role":"assistant","content":answer}])
            self._history=self._history[-16:]
            return {"reply":answer,"messages":list(self._history),"model":self.model}
        finally:
            self._lock.release()
