"""Select a configured local model for agent reasoning requests."""

import os
import re

_COMPLEX_TASK = re.compile(
    r'\b(?:analy[sz]e|compare|evaluate|plan|reason|summari[sz]e|explain in detail)\b',
    re.IGNORECASE,
)


def select_model(prompt: str) -> str:
    fast_model = os.getenv('OLLAMA_MODEL', 'qwen3-vl:4b-instruct').strip() or 'qwen3-vl:4b-instruct'
    complex_model = os.getenv('OLLAMA_COMPLEX_MODEL', '').strip()
    if complex_model and (len(prompt) >= 250 or _COMPLEX_TASK.search(prompt)):
        return complex_model
    return fast_model
