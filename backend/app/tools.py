import subprocess
import os
import webbrowser
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable
from urllib.parse import urlparse
from app.applications import resolve_browser
from app.folders import resolve_folder


class ToolPermission(str, Enum):
    SAFE = 'safe'
    CONFIRMATION_REQUIRED = 'confirmation_required'
    RESTRICTED = 'restricted'


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    permission: ToolPermission
    input_schema: dict[str, Any]
    executor: Callable[[dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    def __init__(self) -> None:
        self.tools: dict[str, ToolDefinition] = {}
        self.register('open_folder', 'Open an existing local folder in Explorer.', ToolPermission.SAFE,
                      {'type': 'object', 'properties': {'path': {'type': 'string'}}, 'required': ['path']},
                      self._open_folder)
        self.register(
            'open_url',
            'Open a public website in the system default browser.',
            ToolPermission.SAFE,
            {
                'type': 'object',
                'properties': {
                    'url': {'type': 'string'},
                    'browser': {'type': 'string', 'enum': ['chrome', 'edge']},
                },
                'required': ['url'],
            },
            self._open_url,
        )
        self.register(
            'open_application',
            'Open a known Windows application such as Chrome, Edge, Notepad, or Explorer.',
            ToolPermission.SAFE,
            {
                'type': 'object',
                'properties': {'application': {'type': 'string'}},
                'required': ['application'],
            },
            self._open_application,
        )

    def register(
        self,
        name: str,
        description: str,
        permission: ToolPermission,
        input_schema: dict[str, Any],
        executor: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.tools[name] = ToolDefinition(
            name=name,
            description=description,
            permission=permission,
            input_schema=input_schema,
            executor=executor,
        )

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self.tools.get(name)

    def execute(
        self,
        name: str,
        params: dict[str, Any] | None = None,
        *,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        payload = self.validate(name, params, confirmed=confirmed)
        return self.tools[name].executor(payload)

    def validate(self, name: str, params: dict[str, Any] | None = None, *, confirmed: bool = False) -> dict[str, Any]:
        """Preflight without side effects, used on EVERY step before a plan starts."""
        tool = self.get_tool(name)
        if tool is None:
            raise KeyError(f'Unknown tool: {name}')

        if tool.permission is ToolPermission.RESTRICTED:
            raise PermissionError(f'Tool is restricted: {name}')
        if tool.permission is ToolPermission.CONFIRMATION_REQUIRED and not confirmed:
            raise PermissionError(f'Confirmation is required before running: {name}')

        payload = {} if params is None else params.copy() if isinstance(params, dict) else params
        if not isinstance(payload, dict):
            raise TypeError('Tool arguments must be a dictionary.')

        properties = tool.input_schema.get('properties', {})
        if any(key not in properties for key in payload):
            raise ValueError(f'Unexpected arguments for {name}.')
        if any(key not in payload for key in tool.input_schema.get('required', [])):
            raise ValueError(f'Missing arguments for {name}.')
        for key, value in payload.items():
            schema = properties[key]
            if schema.get('type') == 'string' and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f'{key} must be a non-empty string.')
            if 'enum' in schema and value not in schema['enum']:
                raise ValueError(f'Unsupported {key}: {value}')
        if name == 'open_url':
            parsed = urlparse(payload['url'])
            if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
                raise ValueError('Only HTTP and HTTPS URLs are allowed.')
            if parsed.username or parsed.password or any(ord(c) < 32 for c in payload['url']):
                raise ValueError('URLs cannot include credentials or control characters.')
            if payload.get('browser'):
                resolve_browser(payload['browser'])
        elif name == 'open_folder':
            payload['path'] = resolve_folder(payload['path'])
        elif name == 'open_application':
            allowed = {'chrome', 'google chrome', 'edge', 'msedge', 'microsoft edge',
                       'notepad', 'notepad.exe', 'explorer', 'file explorer'}
            if payload['application'].lower() not in allowed:
                raise ValueError(f'Unsupported application: {payload["application"]}')
            if payload['application'].lower() in {'chrome', 'google chrome', 'edge', 'msedge', 'microsoft edge'}:
                resolve_browser('chrome' if 'chrome' in payload['application'].lower() else 'edge')
        return payload

    @staticmethod
    def _open_folder(params: dict[str, Any]) -> dict[str, Any]:
        path = resolve_folder(params['path'])
        os.startfile(path, 'explore')
        return {'ok': True, 'action': 'open_folder', 'path': path}

    @staticmethod
    def _open_url(params: dict[str, Any]) -> dict[str, Any]:
        url = str(params.get('url', '')).strip()
        parsed = urlparse(url)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            raise ValueError('Only HTTP and HTTPS URLs are allowed.')

        browser = params.get('browser')
        if browser:
            executable = resolve_browser(browser)
            subprocess.Popen([executable, url], shell=False)
            return {'ok': True, 'action': 'open_url', 'url': url, 'browser': browser}
        if not webbrowser.open(url, new=2, autoraise=True):
            raise RuntimeError('The default browser did not accept the URL.')
        return {'ok': True, 'action': 'open_url', 'url': url}

    @staticmethod
    def _open_application(params: dict[str, Any]) -> dict[str, Any]:
        application = str(params.get('application', '')).strip().lower()
        if not application:
            raise ValueError('Application name is required.')

        target = application
        if application in {'chrome', 'google chrome'}:
            target = 'chrome'
        elif application in {'edge', 'msedge', 'microsoft edge'}:
            target = 'msedge'
        elif application in {'notepad', 'notepad.exe'}:
            target = 'notepad'
        elif application in {'explorer', 'file explorer'}:
            target = 'explorer'

        if target in {'chrome', 'msedge'}:
            subprocess.Popen([resolve_browser('chrome' if target == 'chrome' else 'edge')], shell=False)
        elif target in {'notepad', 'explorer'}:
            subprocess.Popen(['cmd', '/c', 'start', '', target], shell=False)
        else:
            raise ValueError(f'Unsupported application: {application}')

        return {'ok': True, 'action': 'open_application', 'application': application}
