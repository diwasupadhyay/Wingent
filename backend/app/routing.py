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
    r'(?:open|launch|start|visit|go to|search|check|read|send|delete|'
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
        }
        if site.lower() in known_sites:
            return 'open_url', {'url': known_sites[site.lower()]}
        if re.fullmatch(_DOMAIN, site, re.IGNORECASE):
            return 'open_url', {'url': site if site.lower().startswith(('http://', 'https://')) else f'https://{site}'}

    web_search = re.fullmatch(
        r'search\s+(?:google|the web)\s+for\s+(.+)',
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

    youtube_search = re.fullmatch(
        r'(?:(?:open|launch|start)\s+(?:google\s+)?chrome\s+(?:and|then)\s+)?'
        r'(?:open|visit|go to)\s+youtube\s+(?:and|then)\s+'
        r'(?:search|find|look up)\s+(?:for\s+)?(.+?)(?:\s+on\s+youtube)?',
        cleaned,
        re.IGNORECASE,
    )
    if youtube_search:
        query = youtube_search.group(1).strip()
        if query:
            return [('open_url', {'url': f'https://www.youtube.com/results?search_query={quote_plus(query)}'})]

    segments = re.split(r'\s*,\s*|\s+(?:and|then|also)\s+', cleaned, flags=re.IGNORECASE)
    if not segments or any(not segment.strip() for segment in segments):
        return []

    actions = [_parse_segment(segment) for segment in segments]
    if any(action is None for action in actions):
        return []

    parsed_actions = [action for action in actions if action is not None]
    if any(name == 'open_url' for name, _ in parsed_actions):
        parsed_actions = [
            action for action in parsed_actions
            if action[0] != 'open_application' or action[1]['application'] not in _BROWSER_APPS
        ]
    return parsed_actions
