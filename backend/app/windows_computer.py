"""Windows desktop primitives. No application names or workflow scripts."""

import base64
import ctypes
import json
import os
import subprocess
import time
from ctypes import wintypes

from app.window_observer import foreground_window_id, list_visible_windows


class InputNotDispatched(ValueError):
    """Known pre-input rejection: safe to re-observe, not an unknown click."""


def user32():
    if os.name != 'nt':
        raise RuntimeError('Computer control requires Windows.')
    api = ctypes.WinDLL('user32', use_last_error=True)
    api.GetForegroundWindow.restype = wintypes.HWND
    api.SetForegroundWindow.argtypes = [wintypes.HWND]
    api.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    api.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    return api


def focus(window_id):
    if foreground_window_id() == window_id:
        return
    api = user32()
    api.ShowWindow(window_id, 9)
    api.SetForegroundWindow(window_id)
    # Frozen sidecars have a worker process separate from the launcher granted
    # foreground permission by Tauri. Briefly attach input queues for this
    # checked focus operation; never leave threads attached during model work.
    if foreground_window_id() != window_id:
        api.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        api.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        current_thread = kernel.GetCurrentThreadId()
        foreground_thread = api.GetWindowThreadProcessId(api.GetForegroundWindow(), None)
        attached = bool(foreground_thread and foreground_thread != current_thread and
                        api.AttachThreadInput(current_thread, foreground_thread, True))
        try:
            if attached:
                api.SetForegroundWindow(window_id)
        finally:
            if attached:
                api.AttachThreadInput(current_thread, foreground_thread, False)
    for _ in range(10):
        if foreground_window_id() == window_id:
            return
        time.sleep(.05)
    raise ValueError('Windows did not grant focus to the selected window.')


def rectangle(window_id):
    api = user32()
    api.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    api.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    old = api.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    try:
        rect = wintypes.RECT()
        if not api.GetWindowRect(window_id, ctypes.byref(rect)):
            raise ValueError('Window rectangle is unavailable.')
        # Exclude DWM's invisible resize margins, which otherwise capture pixels
        # from unrelated windows around the approved target.
        dwm = ctypes.WinDLL('dwmapi')
        dwm.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        visible = wintypes.RECT()
        if dwm.DwmGetWindowAttribute(window_id, 9, ctypes.byref(visible), ctypes.sizeof(visible)) == 0:
            rect = visible
        # Intersect with the virtual desktop, including negative monitor origins.
        left, top = api.GetSystemMetrics(76), api.GetSystemMetrics(77)
        right, bottom = left + api.GetSystemMetrics(78), top + api.GetSystemMetrics(79)
        bounds = [max(left, rect.left), max(top, rect.top), min(right, rect.right), min(bottom, rect.bottom)]
        width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
        if width <= 0 or height <= 0 or width * height > 20_000_000:
            raise ValueError('Window has no bounded visible capture area.')
        return [bounds[0], bounds[1], width, height]
    finally:
        api.SetThreadDpiAwarenessContext(old)


def powershell(script, payload, timeout=12):
    script = "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); " + script
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                            input=json.dumps(payload), capture_output=True, text=True,
                            encoding='utf-8', timeout=timeout, creationflags=0x08000000 if os.name == 'nt' else 0)
    if result.returncode or not result.stdout.strip():
        raise RuntimeError('Windows observation/action worker failed: ' + result.stderr.strip()[:250])
    return json.loads(result.stdout)


CAPTURE = r"""
$ErrorActionPreference='Stop'; $r=[Console]::In.ReadToEnd() | ConvertFrom-Json
Add-Type -AssemblyName System.Drawing
$b=[System.Drawing.Bitmap]::new([int]$r[2],[int]$r[3]); $g=[System.Drawing.Graphics]::FromImage($b)
$s=$null; $sg=$null; $m=[System.IO.MemoryStream]::new()
try {
 $g.CopyFromScreen([int]$r[0],[int]$r[1],0,0,$b.Size)
 $scale=[Math]::Min(1.0,768.0/[Math]::Max($b.Width,$b.Height))
 $s=[System.Drawing.Bitmap]::new([int]($b.Width*$scale),[int]($b.Height*$scale))
 $sg=[System.Drawing.Graphics]::FromImage($s); $sg.DrawImage($b,0,0,$s.Width,$s.Height)
 $s.Save($m,[System.Drawing.Imaging.ImageFormat]::Png)
 $signature=@(); for($y=0;$y -lt 24;$y++){for($x=0;$x -lt 32;$x++){
  $c=$s.GetPixel([int](($x+.5)*$s.Width/32),[int](($y+.5)*$s.Height/24))
  $signature += [int]([Math]::Floor(($c.R+$c.G+$c.B)/96))
 }}
 @{png=[Convert]::ToBase64String($m.ToArray()); width=$s.Width; height=$s.Height; signature=$signature} | ConvertTo-Json -Compress -Depth 4
} finally {if($sg){$sg.Dispose()};if($s){$s.Dispose()};$g.Dispose();$b.Dispose();$m.Dispose()}
"""


UIA = r"""
$ErrorActionPreference='Stop'; $p=[Console]::In.ReadToEnd() | ConvertFrom-Json
Add-Type -AssemblyName UIAutomationClient; Add-Type -AssemblyName UIAutomationTypes
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr][long]$p.window_id)
if(!$root){throw 'Window has no accessibility root'}
$all=$root.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
$items=@(); $password=$false; $acted=$false
for($i=0;$i -lt [Math]::Min($all.Count,500);$i++){
 try {
  $e=$all.Item($i); $c=$e.Current
  if($c.IsOffscreen){continue}; if($c.IsPassword){$password=$true;continue}
  $id=($e.GetRuntimeId() -join '.')
  if($p.target -and $id -eq $p.target){
   if(!$c.IsEnabled){throw 'Control is disabled'}
   $pattern=$null
   if($e.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$pattern)){$pattern.Invoke();$acted=$true}
   elseif($e.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern,[ref]$pattern)){$pattern.Select();$acted=$true}
   elseif($e.TryGetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern,[ref]$pattern)){$pattern.Toggle();$acted=$true}
   break
  }
  if($items.Count -ge 80){continue}
  $r=$c.BoundingRectangle
  if($r.Width -gt 0 -and $r.Height -gt 0){
   $name=$c.Name; if($name.Length -gt 180){$name=$name.Substring(0,180)}
   $value=''; $pattern=$null
   if($e.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$pattern)){$value=$pattern.Current.Value}
   elseif($e.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern,[ref]$pattern)){$value=$pattern.DocumentRange.GetText(500)}
   if($value.Length -gt 500){$value=$value.Substring(0,500)}
   $actions=@(); foreach($patternName in @('Invoke','SelectionItem','Toggle')){
    $patternType=('System.Windows.Automation.'+$patternName+'Pattern') -as [type]
    $supported=$null
    if($e.TryGetCurrentPattern($patternType::Pattern,[ref]$supported)){$actions+=$patternName}
   }
   $items+=@{id=$id;name=$name;value=$value;role=$c.ControlType.ProgrammaticName;enabled=$c.IsEnabled;focused=$c.HasKeyboardFocus;actions=$actions;rect=@($r.X,$r.Y,$r.Width,$r.Height)}
  }
 } catch {if($p.target){throw}}
}
@{controls=$items;password_controls_present=$password;truncated=($all.Count -gt 80);acted=$acted} | ConvertTo-Json -Compress -Depth 6
"""


def capture(rect):
    result = powershell(CAPTURE, rect)
    image = base64.b64decode(result['png'], validate=True)
    if not image.startswith(b'\x89PNG') or len(image) > 6_000_000:
        raise ValueError('Capture is not a bounded PNG.')
    return {**result, 'image': image}


def accessibility(window_id, target=None):
    return powershell(UIA, {'window_id': window_id, 'target': target})


def pointer_position(rect):
    api = user32()
    api.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    api.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    old = api.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    try:
        point = wintypes.POINT()
        api.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        if not api.GetCursorPos(ctypes.byref(point)):
            return {'available': False}
        left, top, width, height = rect
        inside = left <= point.x < left + width and top <= point.y < top + height
        return {'available': True, 'inside_window': inside,
                'x': round((point.x-left)*1000/max(1, width-1)),
                'y': round((point.y-top)*1000/max(1, height-1))}
    finally:
        api.SetThreadDpiAwarenessContext(old)


class Mouse(ctypes.Structure):
    _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG), ('mouseData', wintypes.DWORD),
                ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD), ('extra', ctypes.c_size_t)]


class Keyboard(ctypes.Structure):
    _fields_ = [('vk', wintypes.WORD), ('scan', wintypes.WORD), ('flags', wintypes.DWORD),
                ('time', wintypes.DWORD), ('extra', ctypes.c_size_t)]


class InputData(ctypes.Union):
    _fields_ = [('mouse', Mouse), ('keyboard', Keyboard)]


class Input(ctypes.Structure):
    _anonymous_ = ('data',)
    _fields_ = [('kind', wintypes.DWORD), ('data', InputData)]


KEYS = {'ctrl': 0x11, 'alt': 0x12, 'shift': 0x10, 'win': 0x5B, 'enter': 13, 'tab': 9,
        'escape': 27, 'space': 32, 'backspace': 8, 'delete': 46, 'home': 36, 'end': 35,
        'left': 37, 'up': 38, 'right': 39, 'down': 40, 'page_up': 33, 'page_down': 34,
        'multiply': 106, 'add': 107, 'subtract': 109, 'decimal': 110, 'divide': 111,
        **{str(i): ord(str(i)) for i in range(10)}, **{chr(i): i - 32 for i in range(97, 123)},
        **{f'f{i}': 111+i for i in range(1, 13)}}


def send(events):
    api = user32()
    api.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
    api.SendInput.restype = wintypes.UINT
    batch = (Input * len(events))(*events)
    if api.SendInput(len(events), batch, ctypes.sizeof(Input)) != len(events):
        raise RuntimeError('Windows accepted only part of the input; effect is unknown.')


def key_event(key, up=False, unicode=False):
    extended = 1 if not unicode and key in {33, 34, 35, 36, 37, 38, 39, 40, 45, 46, 91, 92, 111} else 0
    return Input(1, InputData(keyboard=Keyboard(0 if unicode else key, key if unicode else 0,
                                               (4 if unicode else 0) | (2 if up else 0) | extended, 0, 0)))


def open_search(cancelled=lambda: False):
    """Open OS search, never type or execute a guessed result."""
    if cancelled():
        raise ValueError('Windows Search opening was cancelled.')
    try:
        send([key_event(KEYS['win']), key_event(KEYS['s'])])
    finally:
        send([key_event(KEYS['s'], True), key_event(KEYS['win'], True)])
    deadline = time.monotonic() + 5
    foreground_description = 'no observed foreground window'
    while time.monotonic() < deadline:
        if cancelled():
            raise ValueError('Windows Search opening was cancelled.')
        current = foreground_window_id()
        for window in list_visible_windows():
            if window['hwnd'] == current:
                foreground_description = window['process'] + ': ' + window['title'][:120]
                if window['process'].casefold() in {'searchhost.exe', 'searchapp.exe', 'searchui.exe'}:
                    return current
        time.sleep(.1)
    raise ValueError('Windows Search did not become the observed foreground window. No text was sent. Foreground: ' + foreground_description)


def move_pointer(api, x, y, duration_ms, check):
    """Smooth, cancellable native pointer motion; no extra decorative circles."""
    point = wintypes.POINT()
    api.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    if not api.GetCursorPos(ctypes.byref(point)):
        raise RuntimeError('Could not read the pointer position.')
    start_x, start_y = point.x, point.y
    steps = max(1, duration_ms // 16)
    for step in range(1, steps + 1):
        check()
        t = step / steps
        eased = t * t * (3 - 2 * t)
        if not api.SetCursorPos(round(start_x + (x-start_x)*eased), round(start_y + (y-start_y)*eased)):
            raise RuntimeError('Windows refused pointer movement.')
        time.sleep(duration_ms / steps / 1000)
    check()


def dispatch(window_id, rect, action, cancelled=lambda: False):
    # Capture rectangles and normalized coordinates are physical pixels. Without
    # this, DPI-unaware Python shifts clicks on scaled Windows desktops.
    api = user32()
    api.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    api.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    old = api.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    try:
        return _dispatch(window_id, rect, action, cancelled)
    finally:
        api.SetThreadDpiAwarenessContext(old)


def _dispatch(window_id, rect, action, cancelled):
    def check():
        if cancelled() or user32().GetAsyncKeyState(0x1B) & 0x8000:
            raise RuntimeError('Computer input stopped by cancellation or Escape.')
        if foreground_window_id() != window_id:
            raise RuntimeError('Foreground changed; no further input sent.')
    check()
    kind = action['kind']
    if kind == 'invoke':
        if not accessibility(window_id, action['target_id'])['acted']:
            raise ValueError('Observed control has no supported accessibility action.')
    elif kind == 'wait':
        deadline = time.monotonic() + action.get('duration_ms', 300) / 1000
        while time.monotonic() < deadline:
            if cancelled() or user32().GetAsyncKeyState(0x1B) & 0x8000:
                raise RuntimeError('Computer observation wait cancelled.')
            time.sleep(.02)
        # Foreground may legitimately change while an app/dialog loads. The
        # session observes it afterwards; wait never sends input to either app.
    elif kind in {'click', 'scroll', 'move', 'hover', 'drag'}:
        x = rect[0] + round((action.get('x') if action.get('x') is not None else 500) * (rect[2]-1) / 1000)
        y = rect[1] + round((action.get('y') if action.get('y') is not None else 500) * (rect[3]-1) / 1000)
        api = user32()
        api.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        api.WindowFromPoint.argtypes = [wintypes.POINT]
        api.WindowFromPoint.restype = wintypes.HWND
        api.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        api.GetAncestor.restype = wintypes.HWND
        if api.GetAncestor(api.WindowFromPoint(wintypes.POINT(x, y)), 2) != window_id:
            raise InputNotDispatched('Pointer target is covered by a different window. No click or scroll was sent; inspect the new observation or use a grounded keyboard action.')
        if kind == 'drag':
            api.SetCursorPos(x, y)
        else:
            move_pointer(api, x, y, action.get('duration_ms', 300) if kind == 'move' else 160, check)
        check()
        if api.GetAncestor(api.WindowFromPoint(wintypes.POINT(x, y)), 2) != window_id:
            raise InputNotDispatched('Pointer target became covered during movement; pointer may have moved but no click or scroll was sent.')
        if kind == 'scroll':
            flag = 0x1000 if action.get('axis') == 'horizontal' else 0x0800
            send([Input(0, InputData(mouse=Mouse(0, 0, action['amount'] * 120 & 0xffffffff, flag, 0, 0)))])
        elif kind == 'move':
            return
        elif kind == 'hover':
            deadline = time.monotonic() + action.get('duration_ms', 300) / 1000
            while time.monotonic() < deadline:
                check()
                time.sleep(.02)
        elif kind == 'drag':
            end_x = rect[0] + round(action['end_x'] * (rect[2]-1) / 1000)
            end_y = rect[1] + round(action['end_y'] * (rect[3]-1) / 1000)
            steps = max(5, action.get('duration_ms', 300) // 20)
            points = [(round(x+(end_x-x)*i/steps), round(y+(end_y-y)*i/steps)) for i in range(steps+1)]
            def owns_point(point):
                return api.GetAncestor(api.WindowFromPoint(wintypes.POINT(*point)), 2) == window_id
            if not all(owns_point(point) for point in points):
                raise ValueError('Drag path leaves the approved visible window.')
            down, up = {'right': (8, 16), 'middle': (32, 64)}.get(action.get('button'), (2, 4))
            try:
                send([Input(0, InputData(mouse=Mouse(0, 0, 0, down, 0, 0)))])
                for point in points[1:]:
                    check()
                    if not owns_point(point):
                        raise RuntimeError('Drag path became occluded; partial effect is unknown.')
                    api.SetCursorPos(*point)
                    time.sleep(.02)
            finally:
                send([Input(0, InputData(mouse=Mouse(0, 0, 0, up, 0, 0)))])
        else:
            down, up = {'right': (8, 16), 'middle': (32, 64)}.get(action.get('button'), (2, 4))
            held = []
            try:
                for modifier in action.get('modifiers', []):
                    check()
                    held.append(KEYS[modifier])
                    send([key_event(KEYS[modifier])])
                for _ in range(action.get('clicks', 1)):
                    check()
                    try:
                        send([Input(0, InputData(mouse=Mouse(0, 0, 0, down, 0, 0)))])
                    finally:
                        send([Input(0, InputData(mouse=Mouse(0, 0, 0, up, 0, 0)))])
                    time.sleep(.06)
            finally:
                if held:
                    send([key_event(key, True) for key in reversed(held)])
    elif kind == 'press':
        for _ in range(action.get('presses', 1)):
            for name in action['keys']:
                check()
                key = KEYS[name]
                try:
                    send([key_event(key)])
                    time.sleep(.025)
                finally:
                    send([key_event(key, True)])
                time.sleep(.025)
    elif kind == 'hotkey':
        keys = [KEYS[key] for key in action['keys']]
        try:
            for key in keys:
                check()
                send([key_event(key)])
                time.sleep(.025)
            for key in reversed(keys):
                send([key_event(key, True)])
                time.sleep(.01)
        finally:
            send([key_event(k, True) for k in reversed(keys)])
    elif kind == 'type':
        encoded = action['text'].encode('utf-16-le')
        for offset in range(0, len(encoded), 2):
            check()
            code = int.from_bytes(encoded[offset:offset+2], 'little')
            send([key_event(code, up, True) for up in (False, True)])
            # Some native edit controls sample VK_PACKET state while draining
            # their queue; batching different characters can repeat the last one.
            time.sleep(.04)
