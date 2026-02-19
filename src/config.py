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

# Default configuration (used if config.json doesn't exist)
DEFAULT_CONFIG = {
    "midi": {
        "device_name": "MPK Mini Play",
        "channel": 0,
        "cc_map": {
            "button_1": {"cc": 20, "action": "chord_type", "value": "major"},
            "button_2": {"cc": 21, "action": "chord_type", "value": "minor"},
            "button_3": {"cc": 22, "action": "chord_type", "value": "sus2"},
            "button_4": {"cc": 23, "action": "chord_type", "value": "sus4"},
            "button_5": {"cc": 24, "action": "chord_type", "value": "dim"},
            "button_6": {"cc": 25, "action": "chord_type", "value": "aug"},
            "button_7": {"cc": 26, "action": "chord_type", "value": "dom7"},
            "button_8": {"cc": 27, "action": "chord_type", "value": "maj7"},
        },
        "knob_map": {
            "knob_1a": {"cc": 70, "action": "inversion"},
            "knob_2a": {"cc": 71, "action": "spread"},
            "knob_3a": {"cc": 72, "action": "volume"},
            "knob_4a": {"cc": 73, "action": "reverb"},
        },
        "joystick": {
            "x": {"cc": 1, "action": "pitch_bend"},
            "y": {"cc": 2, "action": "modulation"},
        },
    },
    "synth": {
        "soundfont": "/usr/share/sounds/sf2/FluidR3_GM.sf2",
        "audio_driver": "alsa",
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
        """Look up what a CC number does. Returns (action, value) or None."""
        # Check buttons
        for btn in self.midi["cc_map"].values():
            if btn["cc"] == cc_number:
                return btn["action"], btn.get("value")
        # Check knobs
        for knob in self.midi["knob_map"].values():
            if knob["cc"] == cc_number:
                return knob["action"], None
        # Check joystick
        for axis in self.midi["joystick"].values():
            if axis["cc"] == cc_number:
                return axis["action"], None
        return None, None

    def get_button_cc_list(self):
        """Get list of CC numbers assigned to chord type buttons."""
        return [btn["cc"] for btn in self.midi["cc_map"].values()]
