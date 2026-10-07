"""Unicode SendInput for text PyAutoGUI's keyboard-layout mapping cannot type."""
import ctypes
from ctypes import wintypes


class Mouse(ctypes.Structure):
    _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG), ('data', wintypes.DWORD),
                ('flags', wintypes.DWORD), ('time', wintypes.DWORD), ('extra', ctypes.c_size_t)]


class Keyboard(ctypes.Structure):
    _fields_ = [('vk', wintypes.WORD), ('scan', wintypes.WORD), ('flags', wintypes.DWORD),
                ('time', wintypes.DWORD), ('extra', ctypes.c_size_t)]


class InputData(ctypes.Union):
    _fields_ = [('mouse', Mouse), ('keyboard', Keyboard)]


class Input(ctypes.Structure):
    _fields_ = [('kind', wintypes.DWORD), ('data', InputData)]


def type_code_unit(code):
    api = ctypes.WinDLL('user32', use_last_error=True)
    api.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
    api.SendInput.restype = wintypes.UINT
    events = (Input * 2)(Input(1, InputData(keyboard=Keyboard(0, code, 4, 0, 0))),
                         Input(1, InputData(keyboard=Keyboard(0, code, 6, 0, 0))))
    if api.SendInput(2, events, ctypes.sizeof(Input)) != 2:
        raise RuntimeError('Windows did not accept all input. Inspect the screen before retrying.')
