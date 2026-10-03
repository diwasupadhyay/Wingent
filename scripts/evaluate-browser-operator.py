"""Live local-model reasoning fixture with a fake browser; never launches a website."""

import asyncio
import argparse
import time
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
    def __init__(self, any_song=False):
        self.actions = []
        self.url = ''
        self.any_song = any_song

    def search(self, query, site='youtube'):
        self.actions.append(('search', query, site))
        self.url = 'https://www.youtube.com/results?search_query=joji'
        return {'ok': True, 'url': self.url, 'title': 'YouTube results for Joji',
                'links': [{'index': 0, 'text': 'Joji - Glimpse of Us (Official Video)',
                           'url': 'https://www.youtube.com/watch?v=fixture-other'},
                          {'index': 1, 'text': 'Joji - 777 (Official Video)',
                           'url': 'https://www.youtube.com/watch?v=fixture-observed-777'}],
                'media': [], 'page_observed': True}

    def navigate(self, url):
        self.actions.append(('open', url))
        self.url = url
        if 'watch?v=fixture-observed-777' in url or (self.any_song and 'watch?v=fixture-other' in url):
            return self.follow(1 if 'fixture-observed-777' in url else 0)
        return {'ok': True, 'url': url, 'title': 'YouTube', 'links': [],
                'media': [], 'page_observed': True}

    def inspect(self):
        return {'ok': True, 'url': self.url, 'title': 'YouTube',
                'links': [], 'media': [], 'page_observed': True}

    def follow(self, index):
        self.actions.append(('follow', index))
        if index != 1 and not (self.any_song and index == 0):
            return {'ok': False, 'effect': 'no_effect', 'reason': 'Selected a different song.'}
        self.url = ('https://www.youtube.com/watch?v=fixture-observed-777' if index == 1
                    else 'https://www.youtube.com/watch?v=fixture-other')
        return {'ok': True, 'url': self.url,
                'title': 'Joji - 777 (Official Video)' if index == 1 else 'Joji - Glimpse of Us (Official Video)',
                'links': [], 'media': [{'paused': True, 'current_time': 0, 'ready_state': 4}],
                'page_observed': True}

    def play_media(self):
        self.actions.append(('play',))
        return {'ok': True, 'effect': 'accepted', 'url': self.url,
                'title': ('Joji - 777 (Official Video)' if 'fixture-observed-777' in self.url
                          else 'Joji - Glimpse of Us (Official Video)'),
                'media': {'paused': False, 'current_time': 2.1, 'ready_state': 4},
                'playback_progressed': True,
                'page_observed': True}


async def connected():
    return False


async def main(variant='777'):
    started = time.monotonic()
    browser = FixtureBrowser(any_song=variant == 'any')
    registry = ToolRegistry()
    register_files(registry)
    register_browser(registry, browser)
    for name in ('open_url', 'open_application', 'search_web', 'open_folder'):
        tool = registry.tools[name]
        registry.tools[name] = replace(tool, executor=lambda _: {
            'ok': False, 'effect': 'no_effect', 'reason': 'Fixture permits only browser control.'})
    goal = ('Open Chrome and play any Joji song on YouTube' if variant == 'any'
            else 'Open Chrome and then play 777 song by Joji on YouTube')
    state = TaskState(goal=goal, criteria=[goal], limits=Limits(model_calls=12, seconds=180))
    provider = BudgetedProvider(OllamaClient(), state)
    events = [event async for event in run_operator(registry, state, provider, connected)]
    print('Tools:', [record.action.tool for record in state.records])
    print('Browser actions:', browser.actions)
    print('Terminal:', events[-1][0], events[-1][1].get('outcome'),
          str(events[-1][1].get('text') or events[-1][1].get('message') or '')[:600])
    print('Seconds:', round(time.monotonic() - started, 2), 'Model calls:', state.model_calls)
    assert any(action[0] == 'search' for action in browser.actions)
    assert any(action[0] == 'follow' and (variant == 'any' or action[1] == 1) for action in browser.actions)
    assert any(action[0] == 'play' for action in browser.actions)
    assert any(record.action.tool == 'browser_play_media' and
               record.outcome.data.get('playback_progressed') is True for record in state.records)
    assert events[-1][0] == 'final' and 'Host observation: HTML media time advanced' in events[-1][1]['text']
    assert 'Stopped because' not in events[-1][1]['text']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=('777', 'any'), default='777')
    asyncio.run(main(parser.parse_args().variant))
