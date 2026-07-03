"""Color + Spinner utilities for lk CLI.

No external dependencies. ANSI escape codes (auto-disabled when not a TTY).
"""

from __future__ import annotations

import itertools
import sys
import threading
import time


def ansi(code: str) -> str:
    """Return ANSI escape sequence; empty if stdout is not a TTY."""
    if not sys.stdout.isatty():
        return ''
    return f'\033[{code}m'


# Color codes
RESET = ansi('0')
BOLD = ansi('1')
DIM = ansi('2')
RED = ansi('31')
GREEN = ansi('32')
YELLOW = ansi('33')
BLUE = ansi('34')
MAGENTA = ansi('35')
CYAN = ansi('36')


def colorize(code: str, text: str) -> str:
    """Wrap text in a color, with auto-reset."""
    if not sys.stdout.isatty():
        return text
    return f'{code}{text}{RESET}'


def red(s: str) -> str: return colorize(RED, s)
def green(s: str) -> str: return colorize(GREEN, s)
def yellow(s: str) -> str: return colorize(YELLOW, s)
def blue(s: str) -> str: return colorize(BLUE, s)
def cyan(s: str) -> str: return colorize(CYAN, s)
def bold(s: str) -> str: return colorize(BOLD, s)
def dim(s: str) -> str: return colorize(DIM, s)


# Status icons
def ok(s: str = 'OK') -> str:
    return colorize(GREEN, f'✓ {s}')

def fail(s: str = 'FAIL') -> str:
    return colorize(RED, f'✗ {s}')

def warn(s: str = 'WARN') -> str:
    return colorize(YELLOW, f'⚠ {s}')

def info(s: str = 'INFO') -> str:
    return colorize(CYAN, f'ℹ {s}')


class Spinner:
    """Context manager showing a spinner while work is done.

    Usage:
        with Spinner('查询 opencode models'):
            result = subprocess.run(...)

    Auto-disabled when stdout is not a TTY (no visual noise in pipes).
    """

    FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    def __init__(self, text: str, enabled: bool = True):
        self.text = text
        self.enabled = enabled and sys.stdout.isatty()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self):
        if self.enabled:
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, *args):
        if self._thread:
            self._stop.set()
            self._thread.join()
            sys.stdout.write('\r' + ' ' * (len(self.text) + 6) + '\r')
            sys.stdout.flush()

    def _spin(self):
        for frame in itertools.cycle(self.FRAMES):
            if self._stop.is_set():
                break
            sys.stdout.write(f'\r  {cyan(frame)} {self.text}')
            sys.stdout.flush()
            time.sleep(0.08)
