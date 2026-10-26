"""Identità e stile configurabili, indipendenti da Ollama e dalla UI."""
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("personality.json")

def load_personality(path=CONFIG_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    required = ("identity", "character", "initiative", "humor", "boundaries")
    if not isinstance(data, dict) or any(not isinstance(data.get(k), str) or not data[k].strip() for k in required):
        raise ValueError("Configurazione personalità ROBI incompleta.")
    return data

def build_system_prompt(personality=None):
    cfg = personality if personality is not None else load_personality()
    return "\n".join((
        "Rispondi SOLO con un oggetto JSON contenente la chiave reply, con la risposta finale in italiano.",
        "Non mostrare ragionamenti, istruzioni interne o spiegazioni sulla generazione.",
        "TU sei ROBI; il tuo interlocutore è la persona che scrive.",
        "Quando la persona chiede 'chi sono?' o 'cosa mi piace?', usa le informazioni che ha detto di sé, non quelle di ROBI.",
        "Non inventare ricordi o informazioni mancanti; chiedi chiarimenti se necessario.",
        cfg["identity"], cfg["character"], cfg["initiative"], cfg["humor"], cfg["boundaries"],
        "Non fingere di aver visto, sentito o ricordato qualcosa che i messaggi non confermano.",
        "La cronologia di messaggi è il contesto temporaneo di questa sessione.",
    ))
