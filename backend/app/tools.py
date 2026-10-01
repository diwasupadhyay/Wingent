import subprocess
import webbrowser
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable
from urllib.parse import urlparse
from app.applications import resolve_browser


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
        tool = self.get_tool(name)
        if tool is None:
            raise KeyError(f'Unknown tool: {name}')

        if tool.permission is ToolPermission.RESTRICTED:
            raise PermissionError(f'Tool is restricted: {name}')
        if tool.permission is ToolPermission.CONFIRMATION_REQUIRED and not confirmed:
            raise PermissionError(f'Confirmation is required before running: {name}')

        payload = params or {}
        if not isinstance(payload, dict):
            raise TypeError('Tool arguments must be a dictionary.')

        return tool.executor(payload)

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
