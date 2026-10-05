"""General file primitives. Exact-path approval, bounded reads, no overwrite/delete."""

import hashlib
import os
from itertools import islice
from pathlib import Path

from pydantic import Field

from app.capabilities import Arguments, Capability
from app.tools import ToolPermission
from app.folders import resolve_folder
from typing import Literal

PAGE_BYTES = 2048

class FilePath(Arguments):
    path: str = Field(min_length=1, max_length=2048)


class KnownFolder(Arguments):
    name: Literal['home', 'desktop', 'documents', 'downloads', 'pictures', 'music', 'videos']


def create_directory(params):
    path = Path(local_path(params)['path'])
    try:
        path.mkdir()
    except FileExistsError:
        return {'ok': path.is_dir(), 'path': str(path), 'already_exists': True}
    return {'ok': path.is_dir(), 'path': str(path), 'effect': 'accepted'}


class ReadText(FilePath):
    offset: int = Field(default=0, ge=0, le=10_000_000)


class CreateText(FilePath):
    text: str = Field(max_length=32000)


def local_path(params):
    path = Path(params['path'])
    if not path.is_absolute() or str(path).startswith(('\\\\', '//')):
        raise ValueError('An absolute local path is required; network/device paths are not supported.')
    # Reject device names, alternate streams and Windows path normalization aliases.
    parts = path.parts[1:]
    if any(':' in p or p.endswith((' ', '.')) or p.split('.')[0].upper() in
           {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}
           for p in parts):
        raise ValueError('Device names, alternate streams, and ambiguous path components are not supported.')
    # Do not authorize a link/junction and silently access another directory.
    for item in (path, *path.parents):
        if item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction()):
            raise ValueError('Linked paths are not supported.')
    return {**params, 'path': str(path.resolve(strict=False))}


def list_directory(params):
    path = Path(local_path(params)['path'])
    with os.scandir(path) as entries:
        items = list(islice(entries, 201))
    return {'ok': True, 'path': str(path), 'truncated': len(items) > 200,
            'entries': [{'name': e.name, 'path': e.path, 'directory': e.is_dir(follow_symlinks=False)}
                        for e in items[:200]]}


def read_text(params):
    path = Path(local_path(params)['path'])
    if not path.is_file():
        raise ValueError('Target must be a regular local file.')
    # Byte offsets make bounded pagination predictable; reject binary/invalid UTF-8.
    with path.open('rb') as source:
        before = os.fstat(source.fileno())
        source.seek(params['offset'])
        data = source.read(PAGE_BYTES + 1)
        after = os.fstat(source.fileno())
    def identity(stat):
        return [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns]
    if identity(before) != identity(after):
        return {'ok': False, 'effect': 'no_effect', 'error': 'File changed during reading; observe it again.'}
    clipped = data[:PAGE_BYTES]
    if b'\x00' in clipped:
        raise ValueError('Binary content is not supported by read_text.')
    # A UTF-8 character may cross the page boundary. Leave it for the next page.
    for tail in range(4):
        try:
            page = clipped[:len(clipped)-tail] if tail else clipped
            content = page.decode('utf-8-sig' if params['offset'] == 0 else 'utf-8')
            break
        except UnicodeDecodeError as exc:
            if exc.reason != 'unexpected end of data' or tail == 3:
                raise ValueError('File is not valid UTF-8 text at this offset.') from exc
    if data and not page:
        raise ValueError('Page size is too small for this UTF-8 character.')
    return {'ok': True, 'path': str(path), 'text': content,
            'offset': params['offset'], 'size_bytes': after.st_size,
            'source_version': hashlib.sha256(str(identity(after)).encode()).hexdigest(),
            'next_offset': params['offset'] + len(page), 'truncated': len(data) > len(page)}


def create_text(params):
    path = Path(local_path(params)['path'])
    data = params['text'].encode('utf-8')
    try:
        # Exclusive creation: even a file appearing after approval cannot be overwritten.
        with path.open('xb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError:
        return {'ok': False, 'effect': 'no_effect', 'error': 'File already exists. Choose a new output path.'}
    observed = path.read_bytes()
    return {'ok': observed == data, 'effect': 'accepted' if observed == data else 'unknown',
            'path': str(path), 'bytes': len(observed), 'sha256': hashlib.sha256(observed).hexdigest(),
            'content_matches': observed == data}


def register(registry):
    registry.register('resolve_known_folder', 'Get the actual Windows user folder path, including OneDrive redirection. Use before file operations; never guess a username.',
                      ToolPermission.SAFE, {}, lambda p: {'ok': True, 'path': resolve_folder(p['name'])},
                      input_model=KnownFolder, capability='files', retry_safe=True)
    registry.register('create_directory', 'Create one new directory under an existing observed parent. Does not overwrite or recurse.',
                      ToolPermission.SAFE, {}, create_directory, input_model=FilePath,
                      capability='files', precondition=local_path)
    registry.capabilities['files'] = Capability('files',
        'Discover directory entries, read UTF-8 text in bounded pages, and create new text artifacts. '
        'First resolve_known_folder for Desktop/Documents/Downloads to obtain the real user path. '
        'create_directory creates a missing output directory under an existing parent. '
        'list_directory returns paths; read_text reads a returned path; create_text creates a new output. '
        'Choose read_text when you know a file path but need its content; do not ask the user for content. '
        'When read_text returns truncated=false, reading is finished. If the goal requests a report or new file, '
        'the next step is create_text using the observed content and requested output path, NOT another read. '
        'After create_text returns content_matches=true, that artifact was written and checked; report its path. '
        'Exact local paths require host-managed approval. No overwrite, deletion, links or implicit recursive scans.')
    for name, description, model, execute, repeat in [
        ('list_directory', 'List up to 200 immediate entries of an approved absolute directory. Does not recurse.', FilePath, list_directory, True),
        ('read_text', 'Read a 2048-byte UTF-8 file page. Start at offset 0; if truncated, continue at returned next_offset. No other arguments.', ReadText, read_text, True),
        ('create_text', 'Create a NEW UTF-8 file and read it back to compare content. Never overwrites. Approval previews full text.', CreateText, create_text, False),
    ]:
        def guarded(params, function=execute, read_only=repeat):
            try:
                return function(params)
            except (OSError, ValueError) as exc:
                if not read_only:
                    raise  # A partially created file is an unknown effect, not safely retryable.
                return {'ok': False, 'effect': 'no_effect', 'error': str(exc)[:1000]}
        registry.register(name, description, ToolPermission.CONFIRMATION_REQUIRED, {}, guarded,
                          input_model=model, capability='files', precondition=local_path, retry_safe=repeat)
