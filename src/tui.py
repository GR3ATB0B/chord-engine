"""
tui.py — Curses-based terminal UI for Chord Engine.

Provides a single-screen, in-place updating display with sections for
chord info, looper state, drum pads, and a scrolling log.
"""

import curses
import threading
import time


class TUI:
    """Curses TUI that replaces print statements."""

    # Box drawing (ASCII for max compat)
    WIDTH = 52

    def __init__(self):
        self._lock = threading.Lock()
        self._scr = None
        self._running = False

        # State
        self._note = "--"
        self._chord = "--"
        self._voice = "--"
        self._notes_list = ""
        self._instrument = "Acoustic Grand Piano"
        self._volume = 100
        self._reverb = 0
        self._octave = 0

        self._looper_state = "Stopped"
        self._looper_layers = 0
        self._looper_length = "--"

        self._drum_pads = {}  # note -> active bool
        self._looper_pads = {"REC": False, "PLAY": False, "UNDO": False, "CLR": False}

        self._log_lines = ["Ready — play a key!"]
        self._max_log = 5

        # Color pairs
        self.COLOR_NORMAL = 0
        self.COLOR_RED = 1
        self.COLOR_GREEN = 2
        self.COLOR_YELLOW = 3
        self.COLOR_CYAN = 4
        self.COLOR_HEADER = 5

    def start(self):
        """Initialize curses. Returns False if terminal not available."""
        try:
            self._scr = curses.initscr()
            curses.noecho()
            curses.cbreak()
            curses.curs_set(0)
            self._scr.keypad(True)
            self._scr.nodelay(True)
            self._scr.timeout(100)

            if curses.has_colors():
                curses.start_color()
                curses.use_default_colors()
                curses.init_pair(1, curses.COLOR_RED, -1)
                curses.init_pair(2, curses.COLOR_GREEN, -1)
                curses.init_pair(3, curses.COLOR_YELLOW, -1)
                curses.init_pair(4, curses.COLOR_CYAN, -1)
                curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)
        except Exception:
            # Clean up partial init
            try:
                curses.endwin()
            except Exception:
                pass
            self._scr = None
            return False

        self._running = True
        self.refresh()
        return True

    def stop(self):
        """Clean up curses."""
        self._running = False
        if self._scr:
            try:
                curses.nocbreak()
                self._scr.keypad(False)
                curses.echo()
                curses.endwin()
            except Exception:
                pass
            self._scr = None

    def set_chord(self, note, chord_type, voicing, note_names=None):
        with self._lock:
            self._note = note or "--"
            self._chord = chord_type or "--"
            self._voice = voicing or "--"
            self._notes_list = ", ".join(note_names) if note_names else ""

    def clear_chord(self):
        with self._lock:
            self._note = "--"
            self._chord = "--"
            self._notes_list = ""

    def set_instrument(self, name):
        with self._lock:
            self._instrument = name or "--"

    def set_volume(self, vol):
        with self._lock:
            self._volume = vol

    def set_reverb(self, rev):
        with self._lock:
            self._reverb = rev

    def set_octave(self, oct_shift):
        with self._lock:
            self._octave = oct_shift

    def set_looper_state(self, state, layers=None, length=None):
        with self._lock:
            self._looper_state = state or "Stopped"
            if layers is not None:
                self._looper_layers = layers
            if length is not None:
                self._looper_length = f"{length:.1f}s" if isinstance(length, float) and length > 0 else "--"

    def set_pad_active(self, note, active):
        with self._lock:
            self._drum_pads[note] = active

    def log(self, msg):
        with self._lock:
            self._log_lines.append(msg)
            if len(self._log_lines) > self._max_log:
                self._log_lines = self._log_lines[-self._max_log:]

    def refresh(self):
        """Redraw the entire screen."""
        if not self._scr or not self._running:
            return
        with self._lock:
            try:
                self._draw()
            except curses.error:
                pass

    def _safe_addstr(self, y, x, text, attr=0):
        h, w = self._scr.getmaxyx()
        if y >= h or x >= w:
            return
        # Truncate to fit
        max_len = w - x
        if max_len <= 0:
            return
        text = text[:max_len]
        try:
            self._scr.addstr(y, x, text, attr)
        except curses.error:
            pass

    def _draw(self):
        self._scr.erase()
        h, w = self._scr.getmaxyx()
        W = min(self.WIDTH, w - 1)
        y = 0

        has_color = curses.has_colors()

        def hline(char="="):
            return "+" + char * (W - 2) + "+"

        def padline(content):
            # Pad content to fit box width
            inner = W - 4  # "| " ... " |"
            return "| " + content.ljust(inner) + " |"

        # Header
        self._safe_addstr(y, 0, hline("="),
                          curses.color_pair(self.COLOR_HEADER) | curses.A_BOLD if has_color else curses.A_BOLD)
        y += 1
        title = "CHORDZ"
        self._safe_addstr(y, 0, padline(f"  {title}"),
                          curses.color_pair(self.COLOR_HEADER) | curses.A_BOLD if has_color else curses.A_BOLD)
        y += 1
        self._safe_addstr(y, 0, hline("-"))
        y += 1

        # Chord info
        chord_attr = curses.color_pair(self.COLOR_YELLOW) | curses.A_BOLD if has_color else curses.A_BOLD
        self._safe_addstr(y, 0, "| ", curses.A_BOLD)
        self._safe_addstr(y, 2, f" Note: {self._note:4s}  Chord: ", 0)
        cx = 2 + len(f" Note: {self._note:4s}  Chord: ")
        self._safe_addstr(y, cx, f"{self._chord:8s}", chord_attr)
        cx += 8
        self._safe_addstr(y, cx, f"  Voice: {self._voice}", 0)
        # Close the box
        if W - 1 < w:
            self._safe_addstr(y, W - 1, "|")
        y += 1

        # Notes list
        if self._notes_list:
            self._safe_addstr(y, 0, padline(f" -> {self._notes_list}"), chord_attr)
        else:
            self._safe_addstr(y, 0, padline(""))
        y += 1

        # Instrument
        inst_attr = curses.color_pair(self.COLOR_CYAN) if has_color else 0
        self._safe_addstr(y, 0, padline(f" Instrument: {self._instrument}"), inst_attr)
        y += 1

        # Vol / Rev / Oct
        self._safe_addstr(y, 0, padline(f" Vol: {self._volume:<4d}  Rev: {self._reverb:<4}  Oct: {self._octave:+d}"))
        y += 1

        # Looper section
        self._safe_addstr(y, 0, hline("-"))
        y += 1
        self._safe_addstr(y, 0, padline("  LOOPER"), curses.A_BOLD)
        y += 1
        self._safe_addstr(y, 0, hline("-"))
        y += 1

        ls = self._looper_state.upper()
        if has_color:
            if ls in ("RECORDING", "OVERDUBBING"):
                lattr = curses.color_pair(self.COLOR_RED) | curses.A_BOLD
            elif ls == "PLAYING":
                lattr = curses.color_pair(self.COLOR_GREEN) | curses.A_BOLD
            else:
                lattr = 0
        else:
            lattr = 0

        state_icon = {"STOPPED": "[]", "RECORDING": "@@", "PLAYING": ">>",
                       "PAUSED": "||", "OVERDUBBING": "@@", "IDLE": "[]"}.get(ls, "  ")
        self._safe_addstr(y, 0,
                          padline(f" {state_icon} {ls:12s}  Layers: {self._looper_layers}  Length: {self._looper_length}"),
                          lattr)
        y += 1

        self._safe_addstr(y, 0,
                          padline(" [1]REC  [2]PLAY  [3]UNDO  [4]CLR"))
        y += 1

        # Pads section
        self._safe_addstr(y, 0, hline("-"))
        y += 1
        self._safe_addstr(y, 0, padline("  DRUM PADS"), curses.A_BOLD)
        y += 1
        self._safe_addstr(y, 0, hline("-"))
        y += 1

        # Show drum pads 36-39, 44-51
        pad_str = ""
        for note in [36, 37, 38, 39, 44, 45, 46, 47]:
            active = self._drum_pads.get(note, False)
            dot = "#" if active else "o"
            pad_str += f" {note}:{dot} "
        self._safe_addstr(y, 0, padline(pad_str.strip()))
        y += 1

        # Log section
        self._safe_addstr(y, 0, hline("-"))
        y += 1
        self._safe_addstr(y, 0, padline("  LOG"), curses.A_BOLD)
        y += 1
        self._safe_addstr(y, 0, hline("-"))
        y += 1

        for i in range(self._max_log):
            if i < len(self._log_lines):
                msg = self._log_lines[-(self._max_log - i)] if (self._max_log - i) <= len(self._log_lines) else ""
            else:
                msg = ""
            if y < h - 1:
                self._safe_addstr(y, 0, padline(f" > {msg}"))
                y += 1

        # Bottom border
        if y < h:
            self._safe_addstr(y, 0, hline("="))

        self._scr.noutrefresh()
        curses.doupdate()


class SimpleTUI:
    """Fallback: just prints like before."""

    def start(self):
        pass

    def stop(self):
        pass

    def set_chord(self, note, chord_type, voicing, note_names=None):
        names = ", ".join(note_names) if note_names else ""
        print(f"  {note} {chord_type} ({voicing})  ->  {names}")

    def clear_chord(self):
        pass

    def set_instrument(self, name):
        print(f"  Instrument: {name}")

    def set_volume(self, vol):
        print(f"  Volume: {vol}")

    def set_reverb(self, rev):
        print(f"  Reverb: {rev}")

    def set_octave(self, oct_shift):
        print(f"  Octave: {oct_shift:+d}")

    def set_looper_state(self, state, layers=None, length=None):
        print(f"  Looper: {state} (layers={layers}, length={length})")

    def set_pad_active(self, note, active):
        pass

    def log(self, msg):
        print(f"  > {msg}")

    def refresh(self):
        pass
