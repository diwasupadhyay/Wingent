"""Diagnose only an isolated, temporary Chrome CDP session; prints no page content."""

import sys
import time
import json
from pathlib import Path

from websockets.sync.client import connect

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'backend'))
from app.browser_tools import BrowserSession  # noqa: E402


session = BrowserSession(sys.argv[1] if len(sys.argv) > 1 else 'chrome')
try:
    session._start()
    print('Browser process alive:', session._process.poll() is None)
    print('Target IDs:', [(item.get('type'), item.get('id') == session._page_id)
                          for item in session._json('/json/list')])
    try:
        browser_socket = session._json('/json/version')['webSocketDebuggerUrl']
        with connect(browser_socket, origin='http://localhost', proxy=None,
                     compression=None, open_timeout=3) as channel:
            channel.send(json.dumps({'id': 1, 'method': 'Browser.getVersion'}))
            print('Browser-level CDP result:', channel.recv(timeout=5)[:300])
            channel.send(json.dumps({'id': 2, 'method': 'Target.attachToTarget',
                                     'params': {'targetId': session._page_id, 'flatten': True}}))
            while True:
                attached = json.loads(channel.recv(timeout=5))
                if attached.get('id') == 2:
                    break
            print('Attached via browser:', attached)
            session_id = attached.get('result', {}).get('sessionId')
            channel.send(json.dumps({'id': 3, 'sessionId': session_id,
                                     'method': 'Page.enable'}))
            while True:
                result = json.loads(channel.recv(timeout=5))
                if result.get('id') == 3:
                    break
            print('Page enable through browser:', result)
            channel.send(json.dumps({'id': 4, 'sessionId': session_id,
                                     'method': 'Runtime.evaluate',
                                     'params': {'expression': '1+1', 'returnByValue': True}}))
            while True:
                result = json.loads(channel.recv(timeout=5))
                if result.get('id') == 4:
                    break
        print('CDP result:', result)
    except Exception as error:
        print('CDP error:', type(error).__name__, str(error))
        print('Browser process alive afterward:', session._process.poll() is None)
        time.sleep(1)
        print('Browser exit code one second later:', session._process.poll())
        try:
            print('Target still listed:', any(item.get('id') == session._page_id
                                              for item in session._json('/json/list')))
        except Exception as probe_error:
            print('CDP HTTP endpoint error:', type(probe_error).__name__)
finally:
    session.close()
