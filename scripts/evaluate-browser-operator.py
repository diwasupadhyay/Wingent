"""Live local-model reasoning fixture with a fake browser; never launches a website."""

import asyncio
from dataclasses import replace
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'backend'))

from app.browser_tools import register as register_browser  # noqa: E402
from app.file_tools import register as register_files  # noqa: E402
from app.launch_runtime import BudgetedProvider  # noqa: E402
from app.llm import OllamaClient  # noqa: E402
from app.operator import run_operator  # noqa: E402
from app.task_state import Limits, TaskState  # noqa: E402
from app.tools import ToolRegistry  # noqa: E402


class FixtureBrowser:
    def __init__(self):
        self.actions = []
        self.url = ''

    def search(self, query, site='youtube'):
        self.actions.append(('search', query, site))
        self.url = 'https://www.youtube.com/results?search_query=joji+777'
        return {'ok': True, 'url': self.url, 'title': 'YouTube results for Joji 777',
                'links': [{'index': 0, 'text': 'Joji - Glimpse of Us (Official Video)',
                           'url': 'https://www.youtube.com/watch?v=fixture-other'},
                          {'index': 1, 'text': 'Joji - 777 (Official Video)',
                           'url': 'https://www.youtube.com/watch?v=fixture-observed-777'}],
                'media': [], 'page_observed': True}

    def navigate(self, url):
        self.actions.append(('open', url))
        self.url = url
        if 'watch?v=fixture-observed-777' in url:
            return self.follow(1)
        return {'ok': True, 'url': url, 'title': 'YouTube', 'links': [],
                'media': [], 'page_observed': True}

    def inspect(self):
        return {'ok': True, 'url': self.url, 'title': 'YouTube',
                'links': [], 'media': [], 'page_observed': True}

    def follow(self, index):
        self.actions.append(('follow', index))
        if index != 1:
            return {'ok': False, 'effect': 'no_effect', 'reason': 'Selected a different song.'}
        self.url = 'https://www.youtube.com/watch?v=fixture-observed-777'
        return {'ok': True, 'url': self.url, 'title': 'Joji - 777 (Official Video)',
                'links': [], 'media': [{'paused': True, 'current_time': 0, 'ready_state': 4}],
                'page_observed': True}

    def play_media(self):
        self.actions.append(('play',))
        return {'ok': True, 'effect': 'accepted', 'url': self.url,
                'title': 'Joji - 777 (Official Video)',
                'media': {'paused': False, 'current_time': 2.1, 'ready_state': 4},
                'page_observed': True}


async def connected():
    return False


async def main():
    browser = FixtureBrowser()
    registry = ToolRegistry()
    register_files(registry)
    register_browser(registry, browser)
    for name in ('open_url', 'open_application', 'search_web', 'open_folder'):
        tool = registry.tools[name]
        registry.tools[name] = replace(tool, executor=lambda _: {
            'ok': False, 'effect': 'no_effect', 'reason': 'Fixture permits only browser control.'})
    state = TaskState(goal='Open Chrome and then play 777 song by Joji on YouTube',
                      criteria=['Joji 777 playing'], limits=Limits(model_calls=12, seconds=180))
    provider = BudgetedProvider(OllamaClient(), state)
    events = [event async for event in run_operator(registry, state, provider, connected)]
    print('Tools:', [record.action.tool for record in state.records])
    print('Browser actions:', browser.actions)
    print('Terminal:', events[-1][0], events[-1][1].get('outcome'))
    assert any(action[0] == 'search' for action in browser.actions)
    assert ('follow', 1) in browser.actions
    assert any(action[0] == 'play' for action in browser.actions)


if __name__ == '__main__':
    asyncio.run(main())
