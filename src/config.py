"""
config.py — Configuration manager for Chord Engine.
Loads settings from config.json, creates defaults if missing.
"""

import json
import os
from pathlib import Path

# Project root (one level up from src/)
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"

# Default configuration — matches MPK Mini Play mk3 real MIDI mappings
DEFAULT_CONFIG = {
    "midi": {
        "device_name": "MPK Mini Play",
        "channel": 0,
        "keys": {
            "channel": 0,
            "note_range": [49, 72],
        },
        "pads": {
            "channel": 9,
            "note_range": [36, 51],
        },
        "cc_map": {},
        "knob_map": {
            "knob_1a": {"cc": 70, "action": "chord_type"},
            "knob_2a": {"cc": 71, "action": "voicing"},
            "knob_3a": {"cc": 72, "action": "reverb"},
            "knob_4a": {"cc": 73, "action": "volume"},
            "knob_1b": {"cc": 74, "action": "instrument_select"},
            "knob_2b": {"cc": 75, "action": "expression"},
            "knob_3b": {"cc": 76, "action": "sustain_level"},
            "knob_4b": {"cc": 77, "action": "preset_select"},
            "mod_wheel": {"cc": 1, "action": "modulation"},
        },
        "joystick": {},
    },
    "synth": {
        "soundfont": "/usr/share/sounds/sf2/FluidR3_GM.sf2",
        "audio_driver": "alsa",
        "audio_device": "hw:2,0",
        "instrument": 0,
        "gain": 0.8,
        "reverb": 0.4,
        "chorus": 0.0,
        "buffer_size": 64,
    },
    "display": {
        "width": 1280,
        "height": 720,
        "fullscreen": True,
        "fps": 60,
    },
    "chord": {
        "default_type": "major",
        "default_octave": 4,
        "voice_leading": True,
        "key_mode": None,
        "key_root": None,
    },
}

# Chord types that knob_1 cycles through
CHORD_TYPES = ["major", "minor", "sus2", "sus4", "dim", "aug", "dom7", "maj7", "min7"]

# Voicing modes that knob_2 cycles through
VOICING_MODES = ["close", "spread", "drop2", "drop3", "open"]


# GM presets useful for chord engine
PRESETS = [0, 4, 5, 6, 11, 16, 19, 24, 26, 33, 48, 52, 56, 80, 88, 95]


class Config:
    """Manages application configuration with file persistence."""

    def __init__(self, path=None):
        self.path = Path(path) if path else CONFIG_PATH
        self.data = {}
        self.load()

    def load(self):
        """Load config from JSON file, creating defaults if needed."""
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    self.data = json.load(f)
                # Merge with defaults to fill any missing keys
                self.data = self._deep_merge(DEFAULT_CONFIG, self.data)
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️  Config error, using defaults: {e}")
                self.data = DEFAULT_CONFIG.copy()
                self.save()
        else:
            print(f"📝 Creating default config at {self.path}")
            self.data = DEFAULT_CONFIG.copy()
            self.save()

    def save(self):
        """Save current config to JSON file."""
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=4)

    def _deep_merge(self, default, override):
        """Recursively merge override into default."""
        result = default.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    # --- Accessors ---

    @property
    def midi(self):
        return self.data["midi"]

    @property
    def synth(self):
        return self.data["synth"]

    @property
    def display(self):
        return self.data["display"]

    @property
    def chord(self):
        return self.data["chord"]

    def get_cc_action(self, cc_number):
        """Look up what a CC number does. Returns (action, value) or (None, None)."""
        # Check cc_map (button-style, may have value)
        for entry in self.midi.get("cc_map", {}).values():
            if entry["cc"] == cc_number:
                return entry["action"], entry.get("value")
        # Check knob_map
        for entry in self.midi.get("knob_map", {}).values():
            if entry["cc"] == cc_number:
                return entry["action"], None
        # Check joystick
        for entry in self.midi.get("joystick", {}).values():
            if isinstance(entry, dict) and entry.get("cc") == cc_number:
                return entry["action"], None
        return None, None

    def get_button_cc_list(self):
        """Get list of CC numbers assigned to chord type buttons."""
        return [btn["cc"] for btn in self.midi.get("cc_map", {}).values()]

    def cc_to_chord_type(self, cc_value):
        """Map a CC value (0-127) to a chord type name."""
        idx = int(cc_value / 128 * len(CHORD_TYPES))
        idx = min(idx, len(CHORD_TYPES) - 1)
        return CHORD_TYPES[idx]

    def cc_to_voicing(self, cc_value):
        """Map a CC value (0-127) to a voicing mode name."""
        idx = int(cc_value / 128 * len(VOICING_MODES))
        idx = min(idx, len(VOICING_MODES) - 1)
        return VOICING_MODES[idx]

    def cc_to_octave_shift(self, cc_value):
        """Map CC 0-127 to octave shift -2..+2."""
        return int(cc_value / 127 * 4) - 2

    def cc_to_preset(self, cc_value):
        """Map CC 0-127 to a GM preset number."""
        idx = int(cc_value / 128 * len(PRESETS))
        idx = min(idx, len(PRESETS) - 1)
        return PRESETS[idx]
