import subprocess
import os
import re
import time
import webbrowser
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from urllib.parse import urlparse, quote_plus
from uuid import uuid4
from pydantic import BaseModel
from app.applications import resolve_browser
from app.folders import resolve_folder
from app.approvals import ApprovalStore
from app.capabilities import (CAPABILITIES, UrlArguments, ApplicationArguments, FolderArguments,
                              SearchArguments, ToolResult, legacy_arguments_model)


class ToolPermission(str, Enum):
    SAFE = 'safe'
    CONFIRMATION_REQUIRED = 'confirmation_required'
    RESTRICTED = 'restricted'


# asyncio.to_thread copies this context into the worker executing a tool.
execution_task_id: ContextVar[str] = ContextVar('wingent_execution_task_id', default='')


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    permission: ToolPermission
    input_schema: dict[str, Any]
    executor: Callable[[dict[str, Any]], dict[str, Any]]
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    capability: str = 'windows'
    timeout_seconds: float = 15.0
    cancellation: str = 'cannot_undo_dispatch'
    retry_safe: bool = False
    precondition: Callable | None = None
    observe: Callable | None = None
    verify: Callable | None = None
    cancel_task: Callable[[str], None] | None = None
    revision: str = field(default_factory=lambda: uuid4().hex)


class ToolRegistry:
    def __init__(self) -> None:
        self.tools: dict[str, ToolDefinition] = {}
        self.approvals = ApprovalStore()
        self.capabilities = {item.name: item for item in CAPABILITIES}
        self.register('open_folder', 'Open an existing local folder in Explorer.', ToolPermission.SAFE,
                      {'type': 'object', 'properties': {'path': {'type': 'string'}}, 'required': ['path']},
                      self._open_folder, input_model=FolderArguments, capability='files')
        self.register('search_web', 'Search a named website in a new browser tab. Query contains only search keywords.',
                      ToolPermission.SAFE, {}, self._search_web, input_model=SearchArguments, capability='browser')
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
            input_model=UrlArguments, capability='browser',
        )
        self.register(
            'open_application',
            'Compatibility launcher for Chrome, Edge, Notepad or Explorer only. For any other installed app, use application_search then application_open.',
            ToolPermission.SAFE,
            {
                'type': 'object',
                'properties': {'application': {'type': 'string'}},
                'required': ['application'],
            },
            self._open_application,
            input_model=ApplicationArguments,
        )

    def register(
        self,
        name: str,
        description: str,
        permission: ToolPermission,
        input_schema: dict[str, Any],
        executor: Callable[[dict[str, Any]], dict[str, Any]],
        *, input_model: type[BaseModel] | None = None, output_model: type[BaseModel] = ToolResult,
        capability: str = 'windows', timeout_seconds: float = 15.0,
        cancellation: str = 'cannot_undo_dispatch', retry_safe: bool = False,
        precondition: Callable | None = None, observe: Callable | None = None, verify: Callable | None = None,
        cancel_task: Callable[[str], None] | None = None,
    ) -> None:
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,79}', name) or name in {'ask', 'finish', 'answer'}:
            raise ValueError('Tool names must be lowercase identifiers and cannot use reserved decisions.')
        if not 0 < timeout_seconds <= 120:
            raise ValueError('Tool timeout must be between 0 and 120 seconds.')
        model = input_model or legacy_arguments_model(name, input_schema)
        self.tools[name] = ToolDefinition(
            name=name,
            description=description,
            permission=permission,
            input_schema=model.model_json_schema(), input_model=model, output_model=output_model,
            executor=executor,
            capability=capability, timeout_seconds=timeout_seconds, cancellation=cancellation,
            retry_safe=retry_safe, precondition=precondition, observe=observe, verify=verify,
            cancel_task=cancel_task,
        )

    def manifest(self):
        return [{'name': tool.name, 'description': tool.description, 'permission': tool.permission.value,
                 'input_schema': tool.input_schema, 'output_schema': tool.output_model.model_json_schema(),
                 'capability': tool.capability, 'timeout_seconds': tool.timeout_seconds,
                 'cancellation': tool.cancellation, 'retry_safe': tool.retry_safe,
                 'has_observer': tool.observe is not None, 'has_verifier': tool.verify is not None}
                for tool in self.tools.values() if tool.permission != ToolPermission.RESTRICTED]

    def prepare(self, name, params):
        """Validate prerequisites without granting execution authority."""
        return self.validate(name, params, for_planning=True)

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self.tools.get(name)

    def execute(
        self,
        name: str,
        params: dict[str, Any] | None = None,
        *,
        approval_id: str | None = None, task_id: str = '', review_required: bool = False,
    ) -> dict[str, Any]:
        payload = self.prepare(name, params)
        tool = self.tools[name]
        if approval_id or tool.permission == ToolPermission.CONFIRMATION_REQUIRED or review_required:
            if not approval_id:
                raise PermissionError(f'Confirmation is required before running: {name}')
            self.approvals.consume(approval_id, task_id, name, tool.revision, payload)
        result = tool.executor(payload)
        return tool.output_model.model_validate(result).model_dump(exclude_none=True)

    def validate(self, name: str, params: dict[str, Any] | None = None, *, for_planning: bool = False) -> dict[str, Any]:
        """Preflight without side effects, used on EVERY step before a plan starts."""
        tool = self.get_tool(name)
        if tool is None:
            raise KeyError(f'Unknown tool: {name}')

        if tool.permission is ToolPermission.RESTRICTED:
            raise PermissionError(f'Tool is restricted: {name}')
        if tool.permission is ToolPermission.CONFIRMATION_REQUIRED and not for_planning:
            raise PermissionError(f'Confirmation is required before running: {name}')

        payload = {} if params is None else params.copy() if isinstance(params, dict) else params
        if not isinstance(payload, dict):
            raise TypeError('Tool arguments must be a dictionary.')

        properties = tool.input_schema.get('properties', {})
        if any(key not in properties for key in payload):
            raise ValueError(f'Unexpected arguments for {name}.')
        payload = tool.input_model.model_validate(payload).model_dump(exclude_none=True)
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
        elif name == 'search_web':
            if not payload['query'].strip():
                raise ValueError('Search keywords cannot be blank.')
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
        if tool.precondition:
            payload = tool.precondition(payload)
            payload = tool.input_model.model_validate(payload).model_dump(exclude_none=True)
        return payload

    @staticmethod
    def _search_web(params):
        bases = {'google': 'https://www.google.com/search?q=',
                 'youtube': 'https://www.youtube.com/results?search_query=',
                 'github': 'https://github.com/search?q='}
        payload = {'url': bases[params['engine']] + quote_plus(params['query'])}
        if params.get('browser'):
            payload['browser'] = params['browser']
        return ToolRegistry._open_url(payload)

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
            executable = resolve_browser('chrome' if target == 'chrome' else 'edge')
        elif target in {'notepad', 'explorer'}:
            executable = target + '.exe'
        else:
            raise ValueError(f'Unsupported application: {application}')
        process = subprocess.Popen([executable], shell=False, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # An OS process handle is not a visible application. Give a newly started
        # GUI a short chance to expose a window, then report exactly what was seen.
        from app.window_observer import list_visible_windows
        observed = []
        for _ in range(12):
            observed = [window for window in list_visible_windows()
                        if window['pid'] == process.pid]
            if observed or process.poll() is not None:
                break
            time.sleep(0.15)
        return {'ok': True, 'effect': 'accepted', 'action': 'open_application',
                'application': application, 'pid': process.pid,
                'visible_windows': [{'window_id': window['hwnd'], 'title': window['title'],
                                     'process': window['process']} for window in observed],
                'observation': ('A matching visible window was observed.' if observed else
                                'Process launch accepted; no matching visible window was observed yet.')}
