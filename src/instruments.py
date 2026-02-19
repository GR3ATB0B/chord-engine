"""
instruments.py — Multi-instrument switching via CC knob.

Maps CC 74 (Bank B Knob 1) to a curated list of 16 General MIDI instruments.
"""

# Curated instrument list: (GM program number, emoji, display name)
INSTRUMENT_LIST = [
    (0,   "🎹", "Acoustic Grand Piano"),
    (4,   "🎹", "Electric Piano"),
    (19,  "🎹", "Organ"),
    (48,  "🎻", "Strings Ensemble"),
    (89,  "🎛️", "Synth Pad"),
    (80,  "🎛️", "Synth Lead"),
    (25,  "🎸", "Acoustic Guitar"),
    (27,  "🎸", "Electric Guitar Clean"),
    (30,  "🎸", "Electric Guitar Distorted"),
    (32,  "🎸", "Acoustic Bass"),
    (36,  "🎸", "Slap Bass"),
    (56,  "🎺", "Trumpet"),
    (65,  "🎷", "Saxophone"),
    (73,  "🎵", "Flute"),
    (52,  "🎤", "Choir Aahs"),
    (61,  "🎺", "Brass Section"),
]

NUM_INSTRUMENTS = len(INSTRUMENT_LIST)


def cc_to_instrument_index(cc_value):
    """Map CC value 0-127 to instrument index 0-15."""
    idx = int(cc_value / 128 * NUM_INSTRUMENTS)
    return min(idx, NUM_INSTRUMENTS - 1)


def get_instrument(index):
    """Return (program, emoji, name) for an instrument index."""
    index = max(0, min(index, NUM_INSTRUMENTS - 1))
    return INSTRUMENT_LIST[index]


def get_program(index):
    """Return GM program number for an instrument index."""
    return INSTRUMENT_LIST[max(0, min(index, NUM_INSTRUMENTS - 1))][0]
