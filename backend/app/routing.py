"""Conservative routing for commands that can be completed without a model."""

import re
from urllib.parse import quote_plus

ToolAction = tuple[str, dict[str, str]]

_APP_NAMES = {
    'chrome': 'chrome',
    'google chrome': 'chrome',
    'edge': 'edge',
    'microsoft edge': 'edge',
    'msedge': 'edge',
    'notepad': 'notepad',
    'explorer': 'explorer',
    'file explorer': 'explorer',
}
_BROWSER_APPS = {'chrome', 'edge'}
_DOMAIN = r'(?:https?://)?(?:www\.)?[a-z0-9][a-z0-9.-]+\.(?:com|org|net|io|dev)(?:/[^\s]*)?'
_ACTION_PREFIX = re.compile(
    r'^(?:(?:please|can you|could you|would you)\s+)?'
    r'(?:open|launch|start|visit|go to|search|seach|serach|look up|check|read|send|delete|'
    r'move|rename|type|click|take a screenshot|find a file)\b',
    re.IGNORECASE,
)


def requests_unsupported_browser_automation(prompt: str) -> bool:
    return bool(
        re.search(
            r'\b(?:select|choose|pick)\b.{0,32}\b(?:profile|account)\b',
            prompt,
            flags=re.IGNORECASE,
        )
    )


def looks_like_action_request(prompt: str) -> bool:
    return bool(_ACTION_PREFIX.match(prompt.strip()))


def _parse_segment(segment: str) -> ToolAction | None:
    segment = segment.strip()
    app_match = re.fullmatch(r'(?:open|launch|start)\s+(.+)', segment, re.IGNORECASE)
    if app_match:
        application = _APP_NAMES.get(app_match.group(1).lower())
        if application:
            return 'open_application', {'application': application}

    site_match = re.fullmatch(
        r'(?:open|visit|go to)\s+(?:(?:the\s+)?(?:website|site)\s+)?(.+)',
        segment,
        re.IGNORECASE,
    )
    if site_match:
        site = site_match.group(1).strip()
        known_sites = {
            'youtube': 'https://www.youtube.com',
            'gmail': 'https://mail.google.com',
            'github': 'https://github.com',
            'google': 'https://www.google.com',
        }
        if site.lower() in known_sites:
            return 'open_url', {'url': known_sites[site.lower()]}
        if re.fullmatch(_DOMAIN, site, re.IGNORECASE):
            return 'open_url', {'url': site if site.lower().startswith(('http://', 'https://')) else f'https://{site}'}

    web_search = re.fullmatch(
        r'(?:search|seach|serach|look up)\s+(?:(?:google|the web)\s+for\s+|for\s+)?(.+)',
        segment,
        re.IGNORECASE,
    )
    if web_search:
        query = web_search.group(1).strip()
        if query:
            return 'open_url', {'url': f'https://www.google.com/search?q={quote_plus(query)}'}

    return None


def detect_deterministic_tools(prompt: str) -> list[ToolAction]:
    cleaned = prompt.strip().rstrip(' .!?')
    cleaned = re.sub(
        r'^(?:please|can you|could you|would you)\s+',
        '',
        cleaned,
        flags=re.IGNORECASE,
    )

    # Split at action boundaries, not conjunctions inside search text.
    segments = re.split(
        r'(?:\s*,\s*(?:and\s+)?|\s+(?:and then|and|then|also)\s+)'
        r'(?=(?:open|launch|start|visit|go to|search|seach|serach|look up|'
        r'check|read|send|delete|move|rename|click|type|select|choose)\b)',
        cleaned, flags=re.IGNORECASE,
    )
    if not segments or any(not segment.strip() for segment in segments):
        return []

    actions = [_parse_segment(segment) for segment in segments]
    if any(action is None for action in actions):
        return []

    result: list[ToolAction] = []
    browser: str | None = None
    for segment, action in zip(segments, actions):
        assert action is not None
        name, params = action
        if name == 'open_application' and params['application'] in _BROWSER_APPS:
            browser = params['application']
        elif name == 'open_url':
            if browser:
                params = {**params, 'browser': browser}
                # A navigation launches the browser itself; avoid a blank window.
                if result and result[-1] == ('open_application', {'application': browser}):
                    result.pop()
            search = re.fullmatch(
                r'(?:search|seach|serach|look up)\s+(?:for\s+)?(.+)',
                segment, re.IGNORECASE,
            )
            if search and result and result[-1][0] == 'open_url':
                site = result[-1][1]['url']
                search_base = {
                    'https://www.youtube.com': 'https://www.youtube.com/results?search_query=',
                    'https://github.com': 'https://github.com/search?q=',
                }.get(site)
                if search_base:
                    result.pop()
                    params = {**params, 'url': search_base + quote_plus(search.group(1).strip())}
        result.append((name, params))
    return result
