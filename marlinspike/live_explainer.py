import os
LIVE_LLM_URL = os.environ.get("LIVE_LLM_URL", "").strip()

def explain(alert):
    if LIVE_LLM_URL:
        try:
            llm_text = _llm_explain(alert)
            if llm_text: return llm_text
        except Exception: pass
    return alert.get("text", "")

def _llm_explain(alert):
    return None
