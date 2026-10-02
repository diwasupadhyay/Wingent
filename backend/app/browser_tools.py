"""Isolated Chrome observation and navigation through the local DevTools protocol.

Only pages in the browser process started here are reachable. This never attaches to a
personal Chrome profile or an arbitrary debugging endpoint.
"""

import atexit
import json
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from websockets.sync.client import connect
from pydantic import Field

from app.applications import resolve_browser
from app.capabilities import Arguments
from app.tools import ToolPermission
from app.window_observer import list_visible_windows


class BrowserUrl(Arguments):
    url: str = Field(min_length=1, max_length=2048)


class BrowserQuery(Arguments):
    query: str = Field(min_length=1, max_length=300)
    site: str = Field(default='youtube', pattern=r'^(youtube|google)$')


class BrowserLink(Arguments):
    index: int = Field(ge=0, le=29)


def _public_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Browser navigation requires an HTTP(S) URL without credentials.')
    if any(ord(char) < 32 for char in value):
        raise ValueError('Browser URL contains control characters.')
    return value


class BrowserSession:
    def __init__(self, browser='chrome'):
        self.browser = browser
        self._lock = threading.RLock()
        self._profile = None
        self._process = None
        self._port = None
        self._page_id = None
        self._observed_links = []
        self._fallback_url = None
        self._startup_error = None
        atexit.register(self.close)

    def close(self):
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                # Only terminate the process tree whose PID this session started.
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(self._process.pid), '/T', '/F'],
                                   capture_output=True, timeout=5, check=False)
                else:
                    self._process.terminate()
                try:
                    self._process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._process.kill()
            self._process = None
            self._port = None
            self._page_id = None
            self._observed_links = []
            if self._profile is not None:
                try:
                    self._profile.cleanup()
                except PermissionError:
                    # Chrome subprocesses can release Windows file locks slightly later.
                    time.sleep(0.2)
                    self._profile.cleanup()
                self._profile = None

    def _json(self, path):
        with urlopen(f'http://127.0.0.1:{self._port}{path}', timeout=3) as response:
            return json.load(response)

    def _start(self):
        if self._process is not None and self._process.poll() is None:
            return
        self.close()
        self._profile = tempfile.TemporaryDirectory(prefix='wingent-browser-', ignore_cleanup_errors=True)
        self._startup_error = None
        self._process = subprocess.Popen([
            resolve_browser(self.browser), f'--user-data-dir={self._profile.name}',
            '--remote-debugging-port=0', '--remote-debugging-address=127.0.0.1',
            '--remote-allow-origins=http://localhost',
            '--no-first-run', '--no-default-browser-check', 'about:blank',
        ], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file = Path(self._profile.name) / 'DevToolsActivePort'
        for _ in range(80):
            if self._process.poll() is not None:
                break
            if port_file.exists():
                self._port = int(port_file.read_text(encoding='ascii').splitlines()[0])
                # Chrome already starts with an about:blank target. Creating a second
                # target here is unnecessary and can fail before the first page is used.
                for _ in range(20):
                    if self._process.poll() is not None:
                        break
                    try:
                        pages = [item for item in self._json('/json/list')
                                 if item.get('type') == 'page' and item.get('webSocketDebuggerUrl')]
                    except (OSError, ValueError):
                        pages = []
                    if pages:
                        self._page_id = pages[0]['id']
                        return
                    time.sleep(0.1)
                break
            time.sleep(0.1)
        self.close()
        raise RuntimeError('Agent-owned browser did not expose a usable page. No page was opened.')

    def _socket_url(self):
        pages = [item for item in self._json('/json/list') if item.get('id') == self._page_id]
        if not pages:
            raise RuntimeError('The agent-owned browser page closed.')
        return pages[0]['webSocketDebuggerUrl']

    def _commands(self, commands):
        with connect(self._socket_url(), origin='http://localhost', proxy=None,
                     compression=None, open_timeout=3) as channel:
            results = []
            for index, (method, params) in enumerate(commands, 1):
                channel.send(json.dumps({'id': index, 'method': method, 'params': params}))
                while True:
                    reply = json.loads(channel.recv(timeout=8))
                    if reply.get('id') == index:
                        if 'error' in reply:
                            raise RuntimeError(str(reply['error'].get('message', 'Browser command failed.')))
                        results.append(reply.get('result', {}))
                        break
            return results

    def _run(self, commands):
        return self._commands(commands)

    def navigate(self, url):
        with self._lock:
            url = _public_url(url)
            try:
                self._start()
                self._observed_links = []
                self._run([('Page.navigate', {'url': url})])
                self._fallback_url = None
                deadline = time.monotonic() + 18
                while time.monotonic() < deadline:
                    time.sleep(0.4)
                    page = self.inspect()
                    if page['url'].startswith('chrome-error://'):
                        return {'ok': False, 'effect': 'no_effect', 'url': url,
                                'reason': 'Chrome displayed a navigation error page.'}
                    if page['url'] not in {'', 'about:blank'} and (page['links'] or page['media'] or page['title']):
                        return page
                return {'ok': False, 'effect': 'no_effect', 'url': url,
                        'reason': 'Browser page did not become observable before the timeout.'}
            except Exception as control_error:
                self.close()
                return self._fallback_open(url, control_error)

    def _fallback_open(self, url, control_error):
        self._fallback_url = url
        executable = resolve_browser(self.browser)
        prior_windows = {item['hwnd'] for item in list_visible_windows()
                         if os.path.normcase(item['executable']) == os.path.normcase(executable)}
        subprocess.Popen([executable, '--new-window', url], shell=False)
        for _ in range(25):
            new_windows = [item for item in list_visible_windows()
                           if os.path.normcase(item['executable']) == os.path.normcase(executable)
                           and item['hwnd'] not in prior_windows]
            if new_windows:
                return {'ok': True, 'effect': 'accepted', 'url': url, 'browser': self.browser,
                        'new_window_visible': True, 'page_observed': False, 'browser_control': False,
                        'limitation': 'Chrome control failed; only a new browser window was verified. '
                                      'The page and playback were not observed.'}
            time.sleep(0.2)
        return {'ok': False, 'effect': 'unknown', 'url': url, 'browser': self.browser,
                'new_window_visible': False, 'page_observed': False, 'browser_control': False,
                'reason': 'Browser control failed and no new visible browser window was detected. '
                          'A late launch cannot be ruled out.',
                'diagnostic': type(control_error).__name__}

    def search(self, query, site='youtube'):
        from urllib.parse import quote_plus
        bases = {'youtube': 'https://www.youtube.com/results?search_query=',
                 'google': 'https://www.google.com/search?q='}
        return self.navigate(bases[site] + quote_plus(query))

    def _evaluate(self, expression):
        result = self._run([('Runtime.evaluate', {
            'expression': expression, 'returnByValue': True, 'awaitPromise': True,
        })])[0]
        if result.get('exceptionDetails'):
            raise RuntimeError('Browser page evaluation failed.')
        return result.get('result', {}).get('value')

    def inspect(self):
        with self._lock:
            if self._fallback_url is not None:
                return {'ok': False, 'effect': 'no_effect', 'url': self._fallback_url,
                        'reason': 'The visible Chrome fallback cannot inspect pages. '
                                  'Playback cannot be verified in that browser window.'}
            self._start()
            expression = """(() => ({
              url: location.href, title: document.title,
              links: [...document.querySelectorAll('a[href]')]
                .filter(a => a.innerText.trim() && a.getBoundingClientRect().width > 0)
                .map(a => ({text: a.innerText.trim().slice(0, 140),
                            url: new URL(a.getAttribute('href'), location.href).href,
                            content: !!a.closest('main,article,ytd-video-renderer')}))
                .sort((a,b) => Number(b.content) - Number(a.content)).slice(0, 100),
              media: [...document.querySelectorAll('video,audio')].map(v => ({
                paused: v.paused, current_time: v.currentTime, ready_state: v.readyState,
                duration: Number.isFinite(v.duration) ? v.duration : null
              }))
            }))()"""
            page = self._evaluate(expression)
            if not isinstance(page, dict):
                raise RuntimeError('Browser page did not return an observation.')
            links = []
            seen = set()
            for item in page.get('links', []):
                try:
                    url = _public_url(item['url'])
                except (KeyError, ValueError):
                    continue
                if url not in seen:
                    seen.add(url)
                    links.append({'index': len(links), 'text': item['text'], 'url': url})
                if len(links) >= 30:
                    break
            self._observed_links = links
            return {'ok': True, 'url': page.get('url', ''), 'title': page.get('title', ''),
                    'links': links, 'media': page.get('media', []), 'page_observed': True,
                    'observation': 'Live agent-owned Chrome page; links and media may change.'}

    def follow(self, index):
        with self._lock:
            if not 0 <= index < len(self._observed_links):
                return {'ok': False, 'effect': 'no_effect',
                        'reason': 'Link index is not in the latest live browser observation.'}
            return self.navigate(self._observed_links[index]['url'])

    def play_media(self):
        with self._lock:
            if self._fallback_url is not None:
                return {'ok': False, 'effect': 'no_effect', 'url': self._fallback_url,
                        'reason': 'Chrome opened without page control; Wingent cannot start or verify playback.'}
            before = self.inspect()
            if not before['media']:
                return {'ok': False, 'effect': 'no_effect', 'reason': 'No HTML audio or video element is present.'}
            # A trusted, narrowly scoped DOM interaction. A rejected play() is reported,
            # never converted into a success claim.
            attempt = self._evaluate("""(async () => {
              const v = document.querySelector('video,audio');
              try { await v.play(); return {ok:true}; }
              catch (e) { return {ok:false, reason:String(e).slice(0,200)}; }
            })()""")
            if not (attempt or {}).get('ok'):
                target = self._evaluate("""(() => {
                  const v = document.querySelector('video,audio');
                  const r = v.getBoundingClientRect();
                  return r.width > 20 && r.height > 20 && r.left >= 0 && r.top >= 0
                    ? {x: r.left + r.width / 2, y: r.top + r.height / 2} : null;
                })()""")
                if target:
                    self._run([
                        ('Input.dispatchMouseEvent', {'type': 'mousePressed', **target,
                                                      'button': 'left', 'buttons': 1, 'clickCount': 1}),
                        ('Input.dispatchMouseEvent', {'type': 'mouseReleased', **target,
                                                      'button': 'left', 'buttons': 0, 'clickCount': 1}),
                    ])
            time.sleep(1.2)
            after = self.inspect()
            media = after['media'][0] if after['media'] else None
            progressed = bool(media and not media['paused'] and
                              media['current_time'] > before['media'][0]['current_time'])
            return {'ok': progressed, 'effect': 'accepted' if progressed else 'no_effect',
                    'url': after['url'], 'title': after['title'], 'media': media,
                    'reason': '' if progressed else (attempt or {}).get('reason', 'Playback did not advance.')}


def register(registry, session=None):
    session = session or BrowserSession()
    registry.register('browser_search', 'Search YouTube or Google in agent-owned Chrome and observe the page.',
                      ToolPermission.SAFE, {}, lambda p: session.search(**p),
                      input_model=BrowserQuery, capability='browser', timeout_seconds=45)
    registry.register('browser_open', 'Open an HTTP(S) URL in agent-owned Chrome and observe its title, links and media.',
                      ToolPermission.SAFE, {}, lambda p: session.navigate(p['url']),
                      input_model=BrowserUrl, capability='browser', timeout_seconds=45)
    registry.register('browser_inspect', 'Inspect the current agent-owned Chrome page; returns bounded links and media state.',
                      ToolPermission.SAFE, {}, lambda p: session.inspect(),
                      input_model=Arguments, capability='browser', timeout_seconds=15, retry_safe=True)
    registry.register('browser_follow_link', 'Navigate to an indexed link from the latest browser observation.',
                      ToolPermission.SAFE, {}, lambda p: session.follow(p['index']),
                      input_model=BrowserLink, capability='browser', timeout_seconds=45)
    registry.register('browser_play_media', 'Start HTML audio/video in agent-owned Chrome and verify playback time advances.',
                      ToolPermission.SAFE, {}, lambda p: session.play_media(),
                      input_model=Arguments, capability='browser', timeout_seconds=20)
    return session
