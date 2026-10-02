"""Diagnose only an isolated, temporary Chrome CDP session; prints no page content."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'backend'))
from app.browser_tools import BrowserSession  # noqa: E402


session = BrowserSession(sys.argv[1] if len(sys.argv) > 1 else 'chrome')
try:
    session._start()
    print('Browser process alive:', session._process.poll() is None)
    print('Target IDs:', [(item.get('type'), item.get('id') == session._page_id)
                          for item in session._json('/json/list')])
    try:
        result = session._run([('Runtime.evaluate', {'expression': '1+1', 'returnByValue': True})])
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
