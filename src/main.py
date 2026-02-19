"""
main.py — Entry point for Chord Engine.

Initializes all subsystems, wires them together, and runs the main loop.
MIDI input triggers chord generation → synth plays audio → display updates.

Usage:
    python3 src/main.py              # Normal mode
    python3 src/main.py --midi-debug # Print all MIDI messages
    python3 src/main.py --headless   # No display (terminal only)
    python3 src/main.py --dummy      # No audio (print notes to terminal)
"""

import sys
import signal
import time
import threading

# Add parent directory to path for imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.midi_handler import MidiHandler
from src.chord_engine import ChordEngine
from src.synth_engine import SynthEngine, DummySynth
from src.display import Display


class ChordEngineApp:
    """Main application — ties everything together."""

    def __init__(self, midi_debug=False, headless=False, dummy_synth=False):
        self.running = False
        self.midi_debug = midi_debug
        self.headless = headless

        # Load config
        print("🎹 Chord Engine — Starting up...")
        self.config = Config()

        # Initialize subsystems
        self.midi = MidiHandler(self.config, debug=midi_debug)
        self.engine = ChordEngine(self.config)

        if dummy_synth:
            self.synth = DummySynth()
        else:
            self.synth = SynthEngine(self.config)

        self.display = Display(self.config) if not headless else None

        # Thread lock for shared state
        self._lock = threading.Lock()

        # Display state (updated from MIDI callbacks, read by display)
        self._display_state = {}
        self._state_dirty = True

    def start(self):
        """Initialize all subsystems and start the main loop."""
        print()

        # Initialize synth
        if not self.synth.initialize():
            print("⚠️  Running without audio")
            self.synth = DummySynth()
            self.synth.initialize()

        # Connect MIDI
        if not self.midi.connect():
            if self.midi_debug:
                print("\n🔍 Running in MIDI debug mode — waiting for device...")
                print("   Connect your controller and restart.\n")
            else:
                print("⚠️  No MIDI device — use --midi-debug to monitor")

        # Wire up MIDI callbacks
        self.midi.on_note_on = self._on_note_on
        self.midi.on_note_off = self._on_note_off
        self.midi.on_cc = self._on_cc
        self.midi.on_pitch_bend = self._on_pitch_bend

        # Start display
        if self.display:
            if not self.display.start():
                print("⚠️  Display failed — running headless")
                self.display = None

        self.running = True
        print()
        print("=" * 50)
        print("  🎹 Chord Engine is LIVE")
        print("  Play a key to hear chords!")
        if self.midi_debug:
            print("  📡 MIDI debug mode ON")
        print("  Press Ctrl+C to quit")
        print("=" * 50)
        print()

        # Main loop
        try:
            self._main_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def _main_loop(self):
        """Main application loop — updates display, handles events."""
        while self.running:
            if self.display:
                with self._lock:
                    state = self._display_state.copy()
                if not self.display.update(state):
                    self.running = False
                    break
            else:
                # Headless mode — just sleep to keep the app alive
                time.sleep(0.01)

    def _on_note_on(self, note, velocity):
        """Called when a key is pressed on the MIDI controller."""
        with self._lock:
            # Generate chord from the single note
            chord_notes = self.engine.generate_chord(note, velocity)

            # Play the chord
            self.synth.play_chord(chord_notes)

            # Update display state
            state = self.engine.get_state()
            state["volume"] = getattr(self, "_volume", 100)
            state["reverb"] = getattr(self, "_reverb", 50)
            self._display_state = state

            if not self.display:
                name = self.engine.get_chord_name()
                names = self.engine.get_note_names()
                print(f"  🎵 {name}  →  {', '.join(names)}")

    def _on_note_off(self, note):
        """Called when a key is released."""
        with self._lock:
            # Stop the chord
            self.engine.stop_chord()
            self.synth.stop_chord()

            # Update display
            state = self.engine.get_state()
            state["volume"] = getattr(self, "_volume", 100)
            state["reverb"] = getattr(self, "_reverb", 50)
            self._display_state = state

    def _on_cc(self, cc_number, value):
        """Called when a knob/button sends a CC message."""
        action, param = self.config.get_cc_action(cc_number)

        if action is None:
            if self.midi_debug:
                print(f"  ⚠️  Unmapped CC {cc_number} = {value}")
            return

        with self._lock:
            if action == "chord_type" and param:
                # Button press — only trigger on value > 0 (press, not release)
                if value > 0:
                    self.engine.set_chord_type(param)
                    print(f"  🎛️  Chord type: {param}")

            elif action == "inversion":
                self.engine.set_inversion(value)

            elif action == "spread":
                self.engine.set_spread(value)

            elif action == "volume":
                self._volume = value
                self.synth.set_volume(value)

            elif action == "reverb":
                self._reverb = value
                self.synth.set_reverb(value)

            elif action == "modulation":
                self.synth.set_modulation(value)

            # If a chord is currently playing, regenerate with new settings
            if self.engine.root_note is not None and self.engine.current_notes:
                chord_notes = self.engine.generate_chord(
                    self.engine.root_note, self.engine.velocity
                )
                self.synth.play_chord(chord_notes)

            # Update display state
            state = self.engine.get_state()
            state["volume"] = getattr(self, "_volume", 100)
            state["reverb"] = getattr(self, "_reverb", 50)
            self._display_state = state

    def _on_pitch_bend(self, value):
        """Called on pitch bend (joystick X)."""
        self.synth.pitch_bend(value)

    def shutdown(self):
        """Clean shutdown of all subsystems."""
        print("\n🛑 Shutting down...")
        self.running = False
        self.synth.shutdown()
        self.midi.disconnect()
        if self.display:
            self.display.stop()
        print("👋 Chord Engine stopped\n")


def main():
    # Parse args
    midi_debug = "--midi-debug" in sys.argv
    headless = "--headless" in sys.argv
    dummy = "--dummy" in sys.argv

    # MIDI monitor mode (standalone)
    if "--monitor" in sys.argv:
        from src.midi_handler import run_midi_monitor
        run_midi_monitor()
        return

    app = ChordEngineApp(
        midi_debug=midi_debug,
        headless=headless,
        dummy_synth=dummy,
    )

    # Handle signals
    signal.signal(signal.SIGINT, lambda s, f: setattr(app, "running", False))
    signal.signal(signal.SIGTERM, lambda s, f: setattr(app, "running", False))

    app.start()


if __name__ == "__main__":
    main()
