"""
chord_engine.py — The brain of Chord Engine.

Takes a root note + chord type → generates the right MIDI notes,
applies voice leading, inversions, and spread. Handles key mode
for diatonic chord generation.
"""

from .voice_leading import smooth_voice_lead, apply_inversion, apply_spread

# Note names for display
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_NAMES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# Chord intervals as semitones from root
CHORD_INTERVALS = {
    "major":    [0, 4, 7],
    "minor":    [0, 3, 7],
    "sus2":     [0, 2, 7],
    "sus4":     [0, 5, 7],
    "dim":      [0, 3, 6],
    "aug":      [0, 4, 8],
    "dom7":     [0, 4, 7, 10],
    "maj7":     [0, 4, 7, 11],
    "min7":     [0, 3, 7, 10],
    "dim7":     [0, 3, 6, 9],
    "aug7":     [0, 4, 8, 10],
    "add9":     [0, 4, 7, 14],
    "min9":     [0, 3, 7, 10, 14],
    "maj9":     [0, 4, 7, 11, 14],
    "power":    [0, 7],
    "6":        [0, 4, 7, 9],
    "min6":     [0, 3, 7, 9],
    "9":        [0, 4, 7, 10, 14],
    "11":       [0, 4, 7, 10, 14, 17],
    "13":       [0, 4, 7, 10, 14, 21],
}

# Chord display names (for pretty printing)
CHORD_DISPLAY = {
    "major": "", "minor": "m", "sus2": "sus2", "sus4": "sus4",
    "dim": "dim", "aug": "aug", "dom7": "7", "maj7": "maj7",
    "min7": "m7", "dim7": "dim7", "aug7": "aug7", "add9": "add9",
    "min9": "m9", "maj9": "maj9", "power": "5", "6": "6",
    "min6": "m6", "9": "9", "11": "11", "13": "13",
}

# Scale patterns (semitone intervals) for key mode
SCALES = {
    "major":     [0, 2, 4, 5, 7, 9, 11],
    "minor":     [0, 2, 3, 5, 7, 8, 10],
    "dorian":    [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "phrygian":  [0, 1, 3, 5, 7, 8, 10],
}

# Diatonic chord qualities for major scale degrees (I-VII)
MAJOR_DIATONIC = ["major", "minor", "minor", "major", "major", "minor", "dim"]
MINOR_DIATONIC = ["minor", "dim", "major", "minor", "minor", "major", "major"]


class ChordEngine:
    """Core chord generation and state management."""

    def __init__(self, config):
        self.config = config.chord

        # Current state
        self.root_note = None          # MIDI note number of root
        self.chord_type = self.config.get("default_type", "major")
        self.inversion = 0             # 0-3
        self.spread = 0.0
        self.octave_shift = 0              # 0.0 - 1.0
        self.voice_leading_enabled = self.config.get("voice_leading", True)
        self.default_octave = self.config.get("default_octave", 4)

        # Key mode
        self.key_mode = self.config.get("key_mode")    # "major", "minor", etc.
        self.key_root = self.config.get("key_root")    # Pitch class 0-11

        # Voice leading state
        self.last_chord_notes = []     # Previous chord's MIDI notes
        self.current_notes = []        # Currently sounding MIDI notes
        self.velocity = 100

    def set_chord_type(self, chord_type):
        """Set the active chord type."""
        if chord_type in CHORD_INTERVALS:
            self.chord_type = chord_type
            return True
        return False

    def set_inversion(self, cc_value):
        """Set inversion from CC value (0-127)."""
        # Map 0-127 to 0-3 inversions
        self.inversion = min(cc_value // 32, 3)

    def set_voicing(self, voicing_name):
        """Set the voicing mode (close, spread, drop2, drop3, open)."""
        self.voicing = voicing_name

    def set_spread(self, cc_value):
        """Set spread from CC value (0-127)."""
        self.spread = cc_value / 127.0

    def set_key_mode(self, key_root, scale_name):
        """Enable key mode. key_root is pitch class (0-11), scale is 'major'/'minor'/etc."""
        if scale_name in SCALES:
            self.key_root = key_root
            self.key_mode = scale_name

    def clear_key_mode(self):
        """Disable key mode (free chromatic mode)."""
        self.key_mode = None
        self.key_root = None

    def generate_chord(self, midi_note, velocity=100):
        """
        Generate a chord from a single MIDI note input.

        Args:
            midi_note: MIDI note number (0-127) from the keyboard.
            velocity: Note velocity (0-127).

        Returns:
            List of (midi_note, velocity) tuples for the chord,
            or empty list if no valid chord.
        """
        self.root_note = midi_note
        self.velocity = velocity
        root_pc = midi_note % 12  # Pitch class

        # Determine chord type (key mode may override)
        chord_type = self.chord_type
        if self.key_mode and self.key_root is not None:
            chord_type = self._get_diatonic_chord_type(root_pc)

        # Get intervals for this chord type
        intervals = CHORD_INTERVALS.get(chord_type, CHORD_INTERVALS["major"])

        # Build pitch classes
        pitch_classes = [(root_pc + interval) % 12 for interval in intervals]

        # Voice leading: find smooth voicing relative to previous chord
        if self.voice_leading_enabled and self.last_chord_notes:
            notes = smooth_voice_lead(self.last_chord_notes, pitch_classes,
                                      anchor_octave=self.default_octave)
        else:
            # No previous chord — place in default octave
            base_octave = midi_note // 12
            notes = []
            for pc in pitch_classes:
                note = base_octave * 12 + pc
                # Keep notes near the played note
                while note < midi_note - 6:
                    note += 12
                while note > midi_note + 18:
                    note -= 12
                notes.append(note)
            notes.sort()

        # Apply inversion
        if self.inversion > 0:
            notes = apply_inversion(notes, self.inversion)

        # Apply spread
        if self.spread > 0.05:
            notes = apply_spread(notes, self.spread)

        # Clamp to valid MIDI range
        notes = [max(0, min(127, n)) for n in notes]

        # Update state
        self.last_chord_notes = notes
        self.current_notes = notes

        return [(n, velocity) for n in notes]

    def stop_chord(self):
        """Stop the current chord. Returns the notes to stop."""
        notes = self.current_notes[:]
        self.current_notes = []
        return notes

    def get_chord_name(self):
        """Get the display name of the current chord (e.g., 'Cmaj7')."""
        if self.root_note is None:
            return ""
        root_pc = self.root_note % 12

        # Use the potentially overridden chord type in key mode
        chord_type = self.chord_type
        if self.key_mode and self.key_root is not None:
            chord_type = self._get_diatonic_chord_type(root_pc)

        note_name = NOTE_NAMES[root_pc]
        suffix = CHORD_DISPLAY.get(chord_type, chord_type)

        inv_suffix = ""
        if self.inversion == 1:
            inv_suffix = "/1st"
        elif self.inversion == 2:
            inv_suffix = "/2nd"
        elif self.inversion == 3:
            inv_suffix = "/3rd"

        return f"{note_name}{suffix}{inv_suffix}"

    def get_note_names(self, notes=None):
        """Get note names for the current chord."""
        if notes is None:
            notes = self.current_notes
        return [f"{NOTE_NAMES[n % 12]}{n // 12 - 1}" for n in notes]

    def get_state(self):
        """Get current engine state for display."""
        return {
            "chord_name": self.get_chord_name(),
            "chord_type": self.chord_type,
            "inversion": self.inversion,
            "spread": self.spread,
            "notes": self.current_notes,
            "note_names": self.get_note_names(),
            "key_mode": self.key_mode,
            "key_root": NOTE_NAMES[self.key_root] if self.key_root is not None else None,
            "voice_leading": self.voice_leading_enabled,
        }

    def _get_diatonic_chord_type(self, root_pc):
        """In key mode, determine the diatonic chord type for a given root pitch class."""
        if self.key_root is None or self.key_mode is None:
            return self.chord_type

        scale = SCALES.get(self.key_mode, SCALES["major"])

        # Find which scale degree this root is closest to
        interval = (root_pc - self.key_root) % 12

        if interval in scale:
            degree = scale.index(interval)
        else:
            # Not a diatonic note — find nearest scale degree
            closest = min(scale, key=lambda s: min(abs(s - interval), 12 - abs(s - interval)))
            degree = scale.index(closest)

        # Get diatonic chord quality
        if self.key_mode == "minor":
            diatonic = MINOR_DIATONIC
        else:
            diatonic = MAJOR_DIATONIC

        return diatonic[degree % len(diatonic)]
