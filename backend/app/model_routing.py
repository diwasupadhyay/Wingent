"""Select a configured local model for text-only requests."""

import os
import re

_COMPLEX_TASK = re.compile(
    r'\b(?:analy[sz]e|compare|evaluate|plan|reason|summari[sz]e|explain in detail)\b',
    re.IGNORECASE,
)


def select_model(prompt: str) -> str:
    fast_model = os.getenv('OLLAMA_MODEL', 'llama3.2:3b').strip() or 'llama3.2:3b'
    complex_model = os.getenv('OLLAMA_COMPLEX_MODEL', '').strip()
    if complex_model and (len(prompt) >= 250 or _COMPLEX_TASK.search(prompt)):
        return complex_model
    return fast_model
