"""Client Ollama locale e cronologia della sessione (nessuna persistenza su disco)."""
import json
import threading
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

SYSTEM_PROMPT = ("Rispondi direttamente senza descrivere ragionamenti o istruzioni. /no_think\n" 
                 "Sei ROBI, un piccolo robot da scrivania. Parli italiano in modo naturale, "
                 "caldo e conciso. Non fingere di aver visto o sentito cose non disponibili "
                 "nei messaggi. Se non sei sicuro, dillo. Evita di attribuire emozioni "
                 "alle persone sulla base di espressioni facciali.")
def clean_answer(content: str) -> str:
    """Non pubblicare testo deliberativo invece della risposta finale."""
    import re
    value = re.sub(r"<think>[\\s\\S]*?</think>", "", content, flags=re.IGNORECASE).strip()
    lower = value.casefold()
    if (not value or "<think>" in lower or "thinking..." in lower
            or lower.startswith(("okay, the user", "the user said", "let me think",
                                 "i need to respond", "first, i should"))):
        raise RuntimeError("ROBI ha prodotto ragionamento invece della risposta finale. Riprova.")
    return value


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
                     "messages":[{"role":"system","content":SYSTEM_PROMPT}]+self._history[-16:]+[user],
                     "options":{"num_ctx":4096,"num_predict":220}}
            request=Request(self.endpoint,data=json.dumps(payload).encode("utf-8"),
                            headers={"Content-Type":"application/json"},method="POST")
            try:
                with urlopen(request,timeout=120) as response:
                    data=json.load(response)
            except (URLError, HTTPError, TimeoutError, OSError) as exc:
                raise RuntimeError("Ollama non disponibile: verifica che sia avviato e che qwen3:4b sia installato.") from exc
            answer=clean_answer(data.get("message",{}).get("content",""))
            if not answer:
                raise RuntimeError("Ollama ha restituito una risposta vuota.")
            self._history.extend([user,{"role":"assistant","content":answer}])
            self._history=self._history[-16:]
            return {"reply":answer,"messages":list(self._history),"model":self.model}
        finally:
            self._lock.release()
