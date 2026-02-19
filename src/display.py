"""
display.py — Visual display for Chord Engine using PyGame.

Dark theme with vibrant accents. Shows chord name, piano keyboard
visualization, active notes, and control state. Runs at 60fps
without blocking MIDI processing.
"""

import math
import time

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

# Colors — Nash's signature dark theme
BG_COLOR = (14, 14, 18)           # #0e0e12
PANEL_BG = (22, 22, 30)           # Slightly lighter panels
ACCENT_BLUE = (78, 154, 241)      # #4e9af1
ACCENT_PURPLE = (168, 85, 247)    # #a855f7
ROOT_COLOR = (78, 154, 241)       # Bright blue for root
TONE_COLOR = (138, 85, 247)       # Purple for chord tones
TONE_COLOR_2 = (108, 65, 217)     # Darker purple
WHITE_KEY = (40, 40, 50)          # Dark white keys
BLACK_KEY = (20, 20, 28)          # Darker black keys
WHITE_KEY_ACTIVE = (78, 154, 241) # Active white key
TEXT_COLOR = (220, 220, 230)
TEXT_DIM = (100, 100, 120)
DIVIDER = (35, 35, 45)


class Display:
    """PyGame-based visual display."""

    def __init__(self, config):
        self.config = config.display
        self.width = self.config.get("width", 1280)
        self.height = self.config.get("height", 720)
        self.fullscreen = self.config.get("fullscreen", False)
        self.fps = self.config.get("fps", 60)

        self.screen = None
        self.clock = None
        self.running = False

        # Fonts (initialized in start())
        self.font_huge = None    # Chord name
        self.font_large = None   # Section headers
        self.font_medium = None  # Info text
        self.font_small = None   # Note labels

        # Animation state
        self._note_brightness = {}  # note -> brightness (0.0-1.0) for fade
        self._last_chord_name = ""
        self._chord_name_alpha = 255

        # Current state (updated from main loop)
        self.state = {
            "chord_name": "",
            "chord_type": "major",
            "inversion": 0,
            "spread": 0.0,
            "notes": [],
            "note_names": [],
            "key_mode": None,
            "key_root": None,
            "voice_leading": True,
            "volume": 100,
            "reverb": 50,
            "instrument": 0,
        }

    def start(self):
        """Initialize PyGame display."""
        if not PYGAME_AVAILABLE:
            print("⚠️  PyGame not available — running headless")
            return False

        pygame.init()

        flags = 0
        if self.fullscreen:
            flags = pygame.FULLSCREEN

        try:
            self.screen = pygame.display.set_mode((self.width, self.height), flags)
            pygame.display.set_caption("Chord Engine 🎹")
            self.clock = pygame.time.Clock()

            # Load fonts
            self.font_huge = pygame.font.SysFont("helvetica", 96, bold=True)
            self.font_large = pygame.font.SysFont("helvetica", 32, bold=True)
            self.font_medium = pygame.font.SysFont("helvetica", 22)
            self.font_small = pygame.font.SysFont("helvetica", 14)

            self.running = True
            print(f"🖥️  Display: {self.width}x{self.height} @ {self.fps}fps")
            return True
        except Exception as e:
            print(f"⚠️  Display init failed: {e}")
            return False

    def update(self, state=None):
        """Update display with current state. Call once per frame."""
        if not self.running:
            return True  # Return True to keep app running headless

        if state:
            self.state = state

        # Handle PyGame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()

        # Draw
        self.screen.fill(BG_COLOR)
        self._draw_chord_name()
        self._draw_piano()
        self._draw_info_panel()
        self._draw_knob_indicators()
        self._update_animations()

        pygame.display.flip()
        self.clock.tick(self.fps)
        return True

    def _draw_chord_name(self):
        """Draw the big chord name at the top center."""
        name = self.state.get("chord_name", "")
        if not name:
            name = "♪"

        # Render chord name
        text = self.font_huge.render(name, True, TEXT_COLOR)
        rect = text.get_rect(centerx=self.width // 2, top=40)
        self.screen.blit(text, rect)

        # Note names below
        note_names = self.state.get("note_names", [])
        if note_names:
            notes_str = "  ".join(note_names)
            subtext = self.font_medium.render(notes_str, True, ACCENT_PURPLE)
            subrect = subtext.get_rect(centerx=self.width // 2, top=rect.bottom + 10)
            self.screen.blit(subtext, subrect)

    def _draw_piano(self):
        """Draw a piano keyboard at the bottom with active notes highlighted."""
        active_notes = set(self.state.get("notes", []))
        root = None
        if active_notes:
            root = min(active_notes)

        # Piano dimensions
        num_octaves = 5
        start_note = 36  # C2
        piano_y = self.height - 200
        piano_h = 160
        total_white = num_octaves * 7
        key_w = (self.width - 80) / total_white
        piano_x = 40

        # Draw white keys first
        white_notes = []
        x = piano_x
        for octave in range(num_octaves):
            for i, offset in enumerate([0, 2, 4, 5, 7, 9, 11]):
                note = start_note + octave * 12 + offset
                is_active = note in active_notes
                is_root = note == root

                if is_active:
                    color = ROOT_COLOR if is_root else TONE_COLOR
                    brightness = self._note_brightness.get(note, 1.0)
                    color = self._lerp_color(WHITE_KEY, color, brightness)
                else:
                    color = WHITE_KEY

                rect = pygame.Rect(x, piano_y, key_w - 2, piano_h)
                pygame.draw.rect(self.screen, color, rect, border_radius=4)

                # Note name on active keys
                if is_active:
                    note_name = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][note % 12]
                    label = self.font_small.render(note_name, True, (255, 255, 255))
                    label_rect = label.get_rect(centerx=x + key_w // 2, bottom=piano_y + piano_h - 8)
                    self.screen.blit(label, label_rect)

                white_notes.append((x, note))
                x += key_w

        # Draw black keys on top
        x = piano_x
        for octave in range(num_octaves):
            for i, offset in enumerate([0, 2, 4, 5, 7, 9, 11]):
                if i in [0, 1, 3, 4, 5]:  # C, D, F, G, A have black keys after them
                    if offset + 1 in [1, 3, 6, 8, 10]:
                        note = start_note + octave * 12 + offset + 1
                        is_active = note in active_notes
                        is_root = note == root

                        bx = x + key_w * 0.6
                        bw = key_w * 0.7
                        bh = piano_h * 0.6

                        if is_active:
                            color = ROOT_COLOR if is_root else TONE_COLOR_2
                        else:
                            color = BLACK_KEY

                        rect = pygame.Rect(bx, piano_y, bw, bh)
                        pygame.draw.rect(self.screen, color, rect, border_radius=3)

                        if is_active:
                            note_name = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][note % 12]
                            label = self.font_small.render(note_name, True, (255, 255, 255))
                            label_rect = label.get_rect(centerx=bx + bw // 2, bottom=piano_y + bh - 4)
                            self.screen.blit(label, label_rect)

                x += key_w
            x = piano_x + (octave + 1) * 7 * key_w  # Reset x for next octave... actually handled above

    def _draw_info_panel(self):
        """Draw the settings info panel."""
        panel_y = 200
        panel_x = 50

        items = [
            ("Type", self.state.get("chord_type", "major").upper()),
            ("Inversion", str(self.state.get("inversion", 0))),
            ("Spread", f"{self.state.get('spread', 0):.0%}"),
            ("Voice Lead", "ON" if self.state.get("voice_leading") else "OFF"),
        ]

        key_mode = self.state.get("key_mode")
        key_root = self.state.get("key_root")
        if key_mode and key_root:
            items.append(("Key", f"{key_root} {key_mode}"))

        for i, (label, value) in enumerate(items):
            # Label
            lbl = self.font_medium.render(label, True, TEXT_DIM)
            self.screen.blit(lbl, (panel_x, panel_y + i * 40))
            # Value
            val = self.font_medium.render(value, True, ACCENT_BLUE)
            self.screen.blit(val, (panel_x + 140, panel_y + i * 40))

    def _draw_knob_indicators(self):
        """Draw circular knob indicators on the right side."""
        knobs = [
            ("INV", self.state.get("inversion", 0) / 3.0),
            ("SPREAD", self.state.get("spread", 0)),
            ("VOL", self.state.get("volume", 100) / 127.0),
            ("REVERB", self.state.get("reverb", 50) / 127.0),
        ]

        knob_x = self.width - 100
        knob_y = 220
        knob_r = 25

        for i, (label, value) in enumerate(knobs):
            cy = knob_y + i * 80
            # Background circle
            pygame.draw.circle(self.screen, PANEL_BG, (knob_x, cy), knob_r)
            pygame.draw.circle(self.screen, DIVIDER, (knob_x, cy), knob_r, 2)

            # Arc showing value (from -135° to +135°)
            if value > 0:
                start_angle = math.radians(135)
                end_angle = math.radians(135 - value * 270)
                # Draw arc as segments
                steps = max(2, int(value * 20))
                points = []
                for s in range(steps + 1):
                    t = s / steps
                    angle = start_angle + t * (end_angle - start_angle)
                    px = knob_x + math.cos(angle) * (knob_r - 3)
                    py = cy - math.sin(angle) * (knob_r - 3)
                    points.append((px, py))
                if len(points) >= 2:
                    pygame.draw.lines(self.screen, ACCENT_PURPLE, False, points, 3)

            # Label
            lbl = self.font_small.render(label, True, TEXT_DIM)
            lbl_rect = lbl.get_rect(centerx=knob_x, top=cy + knob_r + 5)
            self.screen.blit(lbl, lbl_rect)

    def _update_animations(self):
        """Update animation state (note fade, etc.)."""
        active = set(self.state.get("notes", []))
        # Brighten active notes
        for note in active:
            self._note_brightness[note] = 1.0
        # Fade inactive notes
        fade_keys = list(self._note_brightness.keys())
        for note in fade_keys:
            if note not in active:
                self._note_brightness[note] -= 0.05
                if self._note_brightness[note] <= 0:
                    del self._note_brightness[note]

    def _lerp_color(self, c1, c2, t):
        """Linear interpolate between two colors."""
        t = max(0, min(1, t))
        return (
            int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t),
        )

    def stop(self):
        """Shut down PyGame display."""
        if self.running:
            self.running = False
            if PYGAME_AVAILABLE:
                pygame.quit()
            print("🖥️  Display stopped")
