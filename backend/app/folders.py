"""Read-only resolution of user-requested local folders (never file execution)."""

import os
from pathlib import Path


KNOWN_FOLDERS = {
    'desktop': 'Desktop', 'documents': 'Personal',
    'downloads': '{374DE290-123F-4565-9164-39C4925E467B}',
    'pictures': 'My Pictures', 'music': 'My Music', 'videos': 'My Video',
}


def resolve_folder(value: str) -> str:
    target = value.strip().strip('"')
    alias = target.lower()
    if alias == 'home':
        target = str(Path.home())
    elif alias in KNOWN_FOLDERS:
        # Registry respects redirected/OneDrive known folders, unlike home/name guesses.
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
            target = os.path.expandvars(winreg.QueryValueEx(key, KNOWN_FOLDERS[alias])[0])
    path = Path(target)
    if target.startswith(('\\\\', '//')) or not path.is_absolute():
        raise ValueError('Please provide an absolute local folder path or a known folder such as downloads.')
    resolved = path.resolve(strict=True)
    if str(resolved).startswith(('\\\\', '//')):
        raise ValueError('Network folders are not supported yet.')
    if not resolved.is_dir():
        raise ValueError('The requested path is not a folder. Files cannot be launched by this tool.')
    return str(resolved)
