"""Resolve approved browser executables without a command shell."""

import os
import shutil
from pathlib import Path


def resolve_browser(browser: str) -> str:
    relative = {
        'chrome': Path('Google/Chrome/Application/chrome.exe'),
        'edge': Path('Microsoft/Edge/Application/msedge.exe'),
    }.get(browser)
    if relative is None:
        raise ValueError(f'Unsupported browser: {browser}')
    for variable in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
        root = os.environ.get(variable)
        if root:
            candidate = Path(root) / relative
            if candidate.is_file():
                return str(candidate)
    executable = shutil.which(relative.name)
    if executable:
        return executable
    raise RuntimeError(f'{browser.title()} is not installed or could not be located.')
