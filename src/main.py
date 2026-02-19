"""
main.py — Entry point for Chord Engine.

Initializes all subsystems, wires them together, and runs the main loop.
MIDI input triggers chord generation → synth plays audio → display updates.
Now with multi-instrument switching, loop recorder, and drum pads.

Usage:
    python3 -m src.main              # Normal mode
    python3 -m src.main --midi-debug # Print all MIDI messages
    python3 -m src.main --headless   # No display (terminal only) — uses TUI
    python3 -m src.main --simple     # Headless with old print-style output
    python3 -m src.main --dummy      # No audio (print notes to terminal)
"""

import sys
import signal
import time
import threading

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.midi_handler import MidiHandler
from src.chord_engine import ChordEngine
from src.synth_engine import SynthEngine, DummySynth
from src.display import Display
from src.instruments import INSTRUMENT_LIST, cc_to_instrument_index, get_instrument
from src.looper import Looper
from src.tui import TUI, SimpleTUI

# Looper control pads (channel 9)
PAD_RECORD = 40
PAD_PLAY_PAUSE = 41
PAD_UNDO = 42
PAD_CLEAR = 43

# Drum pads (channel 9) — notes 36-39 and 44-51
DRUM_PAD_START = 36
DRUM_PAD_END = 51


class ChordEngineApp:
    """Main application — ties everything together."""

    def __init__(self, midi_debug=False, headless=False, dummy_synth=False, simple=False):
        self.running = False
        self.midi_debug = midi_debug
        self.headless = headless
        self.use_tui = headless and not simple

        if not self.use_tui:
            print("🎹 Chord Engine + Loopstation — Starting up...")
        self.config = Config()

        self.midi = MidiHandler(self.config, debug=midi_debug)
        self.engine = ChordEngine(self.config)

        if dummy_synth:
            self.synth = DummySynth()
        else:
            self.synth = SynthEngine(self.config)

        self.display = Display(self.config) if not headless else None

        self._lock = threading.Lock()
        self._display_state = {}
        self._state_dirty = True

        # Instrument state
        self._current_instrument_idx = 0
        self._current_program = 0
        self._current_instrument_name = "Acoustic Grand Piano"

        # Looper (initialized after synth)
        self.looper = None

        # TUI
        if self.use_tui:
            self.tui = TUI()
        elif self.headless:
            self.tui = SimpleTUI()
        else:
            self.tui = SimpleTUI()

    def start(self):
        """Initialize all subsystems and start the main loop."""
        if not self.use_tui:
            print()

        if not self.synth.initialize():
            if not self.use_tui:
                print("⚠️  Running without audio")
            self.synth = DummySynth()
            self.synth.initialize()

        # Initialize drum channel (channel 9) — select GM drum kit
        if hasattr(self.synth, 'fs') and self.synth.fs and self.synth.sfid is not None:
            self.synth.fs.program_select(9, self.synth.sfid, 128, 0)
            # Set up looper playback channels (1-8) with default piano
            for ch in range(1, 9):
                self.synth.fs.program_select(ch, self.synth.sfid, 0, 0)

        # Create looper
        self.looper = Looper(self.synth)

        if not self.midi.connect():
            if self.midi_debug and not self.use_tui:
                print("\n🔍 Running in MIDI debug mode — waiting for device...")
            elif not self.use_tui:
                print("⚠️  No MIDI device — use --midi-debug to monitor")

        self._volume = 100
        self._reverb = 0
        self.synth.set_volume(100)

        # Wire MIDI callbacks — now channel-aware
        self.midi.on_note_on = self._on_note_on
        self.midi.on_note_off = self._on_note_off
        self.midi.on_cc = self._on_cc
        self.midi.on_pitch_bend = self._on_pitch_bend

        if self.display:
            if not self.display.start():
                if not self.use_tui:
                    print("⚠️  Display failed — running headless")
                self.display = None

        self.running = True

        # Start TUI
        if self.use_tui:
            if self.tui.start() is False:
                # Terminal not available, fall back
                self.tui = SimpleTUI()
                self.use_tui = False
                print("⚠️  TUI unavailable, using simple output")
            self.tui.log("Chord Engine + Loopstation is LIVE")
            self.tui.log("Keys: chords | Knob B1: instruments")
            self.tui.log("Pads: 1=rec 2=play 3=undo 4=clear")
            self.tui.refresh()
        else:
            print()
            print("=" * 50)
            print("  🎹 Chord Engine + Loopstation is LIVE")
            print("  Keys: play chords  |  Knob B1: instruments")
            print("  Pad 1: record/overdub  |  Pad 2: play/pause")
            print("  Pad 3: undo layer  |  Pad 4: clear all")
            print("  Pads 5-16: drums (recordable)")
            if self.midi_debug:
                print("  📡 MIDI debug mode ON")
            print("  Press Ctrl+C to quit")
            print("=" * 50)
            print()

        try:
            self._main_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def _main_loop(self):
        while self.running:
            if self.display:
                with self._lock:
                    state = self._display_state.copy()
                if not self.display.update(state):
                    self.running = False
                    break
            else:
                time.sleep(0.05)

    def _on_note_on(self, channel, note, velocity):
        """Handle note on — route by channel."""
        if channel == 9:
            self._on_pad_note_on(note, velocity)
        else:
            self._on_key_note_on(note, velocity)

    def _on_note_off(self, channel, note):
        """Handle note off — route by channel."""
        if channel == 9:
            self._on_pad_note_off(note)
        else:
            self._on_key_note_off(note)

    def _on_key_note_on(self, note, velocity):
        """Piano key pressed — generate and play chord."""
        with self._lock:
            chord_notes = self.engine.generate_chord(note, velocity)
            self.synth.play_chord(chord_notes)

            # Record into looper if active
            if self.looper and self.looper.is_recording():
                for n, v in chord_notes:
                    self.looper.record_event('note_on', 0, n, v, self._current_program)

            state = self.engine.get_state()
            state["volume"] = getattr(self, "_volume", 100)
            state["reverb"] = getattr(self, "_reverb", 0)
            self._display_state = state

            name = self.engine.get_chord_name()
            names = self.engine.get_note_names()
            voicing = getattr(self.engine, "voicing", "close")

            # Update TUI
            root = state.get("root_name", name.split()[0] if name else "--")
            chord_type = state.get("chord_type", "Major")
            self.tui.set_chord(root, chord_type, voicing, names)
            self.tui.log(f"{name} ({voicing})  ->  {', '.join(names)}")
            self.tui.refresh()

    def _on_key_note_off(self, note):
        """Piano key released."""
        with self._lock:
            # Record note-offs for looper
            if self.looper and self.looper.is_recording() and self.engine.current_notes:
                for n, v in self.engine.current_notes:
                    self.looper.record_event('note_off', 0, n, 0, self._current_program)

            self.engine.stop_chord()
            self.synth.stop_chord()

            state = self.engine.get_state()
            state["volume"] = getattr(self, "_volume", 100)
            state["reverb"] = getattr(self, "_reverb", 0)
            self._display_state = state

    def _on_pad_note_on(self, note, velocity):
        """Drum pad pressed — looper control or drum trigger."""
        if note == PAD_RECORD:
            if self.looper:
                new_state = self.looper.toggle_record(self._current_program)
                self._update_looper_tui(new_state)
        elif note == PAD_PLAY_PAUSE:
            if self.looper:
                new_state = self.looper.toggle_play_pause()
                self._update_looper_tui(new_state)
        elif note == PAD_UNDO:
            if self.looper:
                new_state = self.looper.undo_layer()
                self._update_looper_tui(new_state)
                self.tui.log(f"Undo layer ({len(self.looper.layers)} remaining)")
                self.tui.refresh()
        elif note == PAD_CLEAR:
            if self.looper:
                new_state = self.looper.clear_all()
                self._update_looper_tui(new_state)
                self.tui.log("Cleared all loops")
                self.tui.refresh()
        elif DRUM_PAD_START <= note <= DRUM_PAD_END:
            # Drum sound — play on channel 9
            if hasattr(self.synth, 'fs') and self.synth.fs:
                self.synth.fs.noteon(9, note, velocity)
            # Record drum into looper
            if self.looper and self.looper.is_recording():
                self.looper.record_event('note_on', 9, note, velocity, 0)
            self.tui.set_pad_active(note, True)
            self.tui.log(f"Drum pad {note}")
            self.tui.refresh()

    def _on_pad_note_off(self, note):
        """Drum pad released."""
        if DRUM_PAD_START <= note <= DRUM_PAD_END:
            if hasattr(self.synth, 'fs') and self.synth.fs:
                self.synth.fs.noteoff(9, note)
            if self.looper and self.looper.is_recording():
                self.looper.record_event('note_off', 9, note, 0, 0)
            self.tui.set_pad_active(note, False)
            self.tui.refresh()

    def _update_looper_tui(self, state):
        """Update TUI looper section from looper state."""
        if not self.looper:
            return
        layers = len(self.looper.layers)
        length = self.looper.loop_length if self.looper.loop_length > 0 else 0.0
        state_str = state if state else "idle"
        self.tui.set_looper_state(state_str, layers=layers, length=length)

        # Log looper state changes
        log_map = {
            "recording": "Recording...",
            "playing": "Playing",
            "paused": "Paused",
            "overdubbing": "Overdubbing...",
            "idle": "Stopped",
        }
        msg = log_map.get(state_str, state_str)
        self.tui.log(f"Looper: {msg}")
        self.tui.refresh()

    def _on_cc(self, cc_number, value):
        """CC message — knobs and controls."""
        action, param = self.config.get_cc_action(cc_number)

        if action is None:
            if self.midi_debug:
                self.tui.log(f"Unmapped CC {cc_number} = {value}")
                self.tui.refresh()
            return

        with self._lock:
            if action == "instrument_select":
                idx = cc_to_instrument_index(value)
                if idx != self._current_instrument_idx:
                    self._current_instrument_idx = idx
                    program, emoji, name = get_instrument(idx)
                    self._current_program = program
                    self._current_instrument_name = name
                    # Change program on channel 0 (live play)
                    if hasattr(self.synth, 'fs') and self.synth.fs and self.synth.sfid is not None:
                        self.synth.fs.program_select(0, self.synth.sfid, 0, program)
                    self.tui.set_instrument(name)
                    self.tui.log(f"Switched to: {name}")
                    self.tui.refresh()

            elif action == "chord_type":
                chord_type = self.config.cc_to_chord_type(value)
                self.engine.set_chord_type(chord_type)
                self.tui.log(f"Chord type: {chord_type}")
                self.tui.refresh()

            elif action == "voicing":
                voicing = self.config.cc_to_voicing(value)
                self.engine.set_voicing(voicing)
                self.tui.log(f"Voicing: {voicing}")
                self.tui.refresh()

            elif action == "volume":
                self._volume = value
                self.synth.set_volume(value)
                self.tui.set_volume(value)
                self.tui.refresh()

            elif action == "reverb":
                self._reverb = value
                self.synth.set_reverb(value)
                self.tui.set_reverb(value)
                self.tui.refresh()

            elif action == "expression":
                self.synth.set_modulation(value)

            elif action == "modulation":
                self.synth.set_modulation(value)

            elif action == "octave_shift":
                shift = self.config.cc_to_octave_shift(value)
                self.engine.octave_shift = shift
                self.tui.set_octave(shift)
                self.tui.log(f"Octave shift: {shift:+d}")
                self.tui.refresh()

            elif action == "sustain_level":
                self.synth.set_sustain(value)

            elif action == "preset_select":
                preset = self.config.cc_to_preset(value)
                self.synth.set_instrument(preset)

            # Regenerate chord if playing
            if self.engine.root_note is not None and self.engine.current_notes:
                chord_notes = self.engine.generate_chord(
                    self.engine.root_note, self.engine.velocity
                )
                self.synth.play_chord(chord_notes)

            state = self.engine.get_state()
            state["volume"] = getattr(self, "_volume", 100)
            state["reverb"] = getattr(self, "_reverb", 0)
            self._display_state = state

    def _on_pitch_bend(self, value):
        self.synth.pitch_bend(value)

    def shutdown(self):
        if self.use_tui:
            self.tui.stop()
        print("\n🛑 Shutting down...")
        self.running = False
        if self.looper:
            self.looper.clear_all()
        self.synth.shutdown()
        self.midi.disconnect()
        if self.display:
            self.display.stop()
        print("👋 Chord Engine stopped\n")


def main():
    midi_debug = "--midi-debug" in sys.argv
    headless = "--headless" in sys.argv
    dummy = "--dummy" in sys.argv
    simple = "--simple" in sys.argv

    if "--monitor" in sys.argv:
        from src.midi_handler import run_midi_monitor
        run_midi_monitor()
        return

    app = ChordEngineApp(
        midi_debug=midi_debug,
        headless=headless,
        dummy_synth=dummy,
        simple=simple,
    )

    def handle_signal(sig, frame):
        app.running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    app.start()


if __name__ == "__main__":
    main()
