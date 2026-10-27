"""Client Ollama locale e cronologia della sessione (nessuna persistenza su disco)."""
import json
import threading
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from .personality import build_system_prompt
from .memory import MemoryStore

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


def user_facts_context(history):
    """Riporta messaggi dell'utente, non inferenze dell'assistente."""
    statements = [m['content'] for m in history if m.get('role') == 'user' and isinstance(m.get('content'), str)]
    if not statements:
        return ''
    return ('PROMEMORIA: solo affermazioni scritte dall\'utente; domande e ipotesi non confermano fatti. '
            'Se un dettaglio viene corretto, prevale l\'ultima affermazione esplicita. '
            'Non attribuire all\'utente idee proposte da ROBI.\n' +
            '\\n'.join('- ' + json.dumps(text, ensure_ascii=False) for text in statements[-8:]))

SUPPORTED_MODELS = ("qwen3:4b", "gemma3:4b")


class Conversation:
    def __init__(self, model="gemma3:4b", endpoint="http://127.0.0.1:11434/api/chat", memory=None):
        self.model, self.endpoint = model, endpoint
        self.memory = memory
        self._lock = threading.Lock()
        self._history = []
        if self.model not in SUPPORTED_MODELS:
            raise ValueError("Modello AI non supportato.")
    def model_status(self):
        with self._lock:
            return {"model": self.model, "available_models": list(SUPPORTED_MODELS)}

    def set_model(self, model):
        if not isinstance(model, str) or model not in SUPPORTED_MODELS:
            raise ValueError("Modello non supportato. Scegli qwen3:4b o gemma3:4b.")
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("Attendi che ROBI completi la risposta prima di cambiare modello.")
        try:
            # Evitiamo di mischiare gli output dei modelli durante il confronto.
            if model != self.model:
                self.model = model
                self._history.clear()
            return {"model": self.model, "messages": list(self._history)}
        finally:
            self._lock.release()

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
                     "messages":[{"role":"system","content":build_system_prompt()}, {"role":"system","content":user_facts_context(self._history)}, {"role":"system","content":self.memory.context() if self.memory else ""}]+self._history[-16:]+[user],
                     "options":{"num_ctx":4096,"num_predict":350},
                     "format":{"type":"object","properties":{"reply":{"type":"string"}},"required":["reply"],"additionalProperties":False}}
            request=Request(self.endpoint,data=json.dumps(payload).encode("utf-8"),
                            headers={"Content-Type":"application/json"},method="POST")
            try:
                with urlopen(request,timeout=120) as response:
                    data=json.load(response)
            except (URLError, HTTPError, TimeoutError, OSError) as exc:
                raise RuntimeError(f"Ollama non disponibile: verifica che sia avviato e che {self.model} sia installato.") from exc
            answer=extract_reply(data)
            if not answer:
                raise RuntimeError("Ollama ha restituito una risposta vuota.")
            self._history.extend([user,{"role":"assistant","content":answer}])
            self._history=self._history[-16:]
            return {"reply":answer,"messages":list(self._history),"model":self.model}
        finally:
            self._lock.release()
