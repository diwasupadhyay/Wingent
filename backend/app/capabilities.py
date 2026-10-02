"""Trusted application knowledge and typed tool contracts; knowledge grants no permissions."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, create_model


class Arguments(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class UrlArguments(Arguments):
    url: str = Field(min_length=1, max_length=2048)
    browser: Literal['chrome', 'edge'] | None = None


class ApplicationArguments(Arguments):
    application: Literal['chrome', 'google chrome', 'edge', 'msedge', 'microsoft edge', 'notepad', 'notepad.exe', 'explorer', 'file explorer']


class FolderArguments(Arguments):
    path: str = Field(min_length=1, max_length=2048)


class SearchArguments(Arguments):
    engine: Literal['google', 'youtube', 'github']
    query: str = Field(min_length=1, max_length=1000)
    browser: Literal['chrome', 'edge'] | None = None


class ToolResult(BaseModel):
    model_config = ConfigDict(extra='allow', strict=True)
    __pydantic_extra__: dict[str, JsonValue] = Field(init=False)
    ok: bool
    effect: Literal['accepted', 'no_effect', 'unknown'] | None = None


def legacy_arguments_model(name, schema):
    """Support old simple string schemas only; richer tools must provide a Pydantic model."""
    fields = {}
    for key, prop in schema.get('properties', {}).items():
        if prop.get('type') != 'string':
            raise ValueError('Register a typed input_model for non-string tool arguments.')
        annotation = Literal[tuple(prop['enum'])] if 'enum' in prop else str
        fields[key] = (annotation, ... if key in schema.get('required', []) else None)
    return create_model(name + 'Arguments', __base__=Arguments, **fields)


@dataclass(frozen=True)
class Capability:
    name: str
    guidance: str
    available: bool = True


CAPABILITIES = (
    Capability('windows', 'Only registered application tools are available. No typing, clicking, focus or screen inspection yet.'),
    Capability('browser', 'Opening a URL already launches the requested browser in a tab. Carry explicit browser selection into every navigation/search. Known public homes: https://github.com and https://www.youtube.com. No page reading or clicking yet.'),
    Capability('files', 'Open existing local directories only. Known aliases: downloads, desktop, documents, pictures, music, videos, home. For other folders require an exact user-supplied path. Never invent a path.'),
    Capability('youtube', 'Search with search_web engine youtube. Pass only search keywords as query, not trailing instructions. Do not navigate to the homepage before a search. Playback is not available yet.'),
    Capability('excel', 'Workbook inspection and editing are not installed yet.', False),
    Capability('research', 'Page extraction and source-backed research are not installed yet.', False),
)
