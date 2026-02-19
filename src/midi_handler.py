"""
midi_handler.py — MIDI input handling for Chord Engine.

Auto-detects the MPK Mini Play (or any USB MIDI controller),
parses incoming messages, and dispatches callbacks.
Uses mido with python-rtmidi backend for low-latency input.
"""

import mido
import threading
import time


class MidiHandler:
    """Handles MIDI input from USB controller."""

    def __init__(self, config, debug=False):
        self.config = config.midi
        self.debug = debug
        self.port = None
        self.running = False
        self._thread = None

        # Callbacks — set these from main.py
        self.on_note_on = None      # (note, velocity) → called on key press
        self.on_note_off = None     # (note) → called on key release
        self.on_cc = None           # (cc_number, value) → called on CC change
        self.on_pitch_bend = None   # (value) → called on pitch bend

    def find_device(self):
        """Find and return the MIDI input port name for the controller."""
        available = mido.get_input_names()
        if self.debug:
            print(f"🔍 Available MIDI inputs: {available}")

        if not available:
            return None

        # Try to find by configured name
        device_name = self.config.get("device_name", "MPK Mini Play")
        for port_name in available:
            if device_name.lower() in port_name.lower():
                return port_name

        # Fallback: use first available port
        print(f"⚠️  '{device_name}' not found, using: {available[0]}")
        return available[0]

    def connect(self):
        """Connect to the MIDI device."""
        port_name = self.find_device()
        if port_name is None:
            print("❌ No MIDI devices found!")
            print("   Connect your MIDI controller and try again.")
            print("   Available ports:", mido.get_input_names())
            return False

        try:
            self.port = mido.open_input(port_name, callback=self._on_message)
            print(f"🎹 Connected to: {port_name}")
            self.running = True
            return True
        except Exception as e:
            print(f"❌ Failed to open MIDI port: {e}")
            return False

    def _on_message(self, msg):
        """
        Callback for incoming MIDI messages. Runs on mido's listener thread.
        Dispatches to registered callbacks.
        """
        if self.debug:
            self._print_debug(msg)

        if msg.type == "note_on" and msg.velocity > 0:
            if self.on_note_on:
                self.on_note_on(msg.note, msg.velocity)

        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            if self.on_note_off:
                self.on_note_off(msg.note)

        elif msg.type == "control_change":
            if self.on_cc:
                self.on_cc(msg.control, msg.value)

        elif msg.type == "pitchwheel":
            if self.on_pitch_bend:
                self.on_pitch_bend(msg.pitch)

    def _print_debug(self, msg):
        """Pretty-print MIDI messages for debug mode."""
        if msg.type == "note_on":
            note_name = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][msg.note % 12]
            octave = msg.note // 12 - 1
            print(f"  🎵 NOTE ON:  {note_name}{octave} (note={msg.note}, vel={msg.velocity})")
        elif msg.type == "note_off":
            note_name = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][msg.note % 12]
            octave = msg.note // 12 - 1
            print(f"  🔇 NOTE OFF: {note_name}{octave} (note={msg.note})")
        elif msg.type == "control_change":
            print(f"  🎛️  CC {msg.control:3d} = {msg.value:3d}")
        elif msg.type == "pitchwheel":
            print(f"  🕹️  PITCH BEND: {msg.pitch}")
        else:
            print(f"  📨 {msg}")

    def disconnect(self):
        """Disconnect from MIDI device."""
        self.running = False
        if self.port:
            self.port.close()
            self.port = None
            print("🔌 MIDI disconnected")

    def is_connected(self):
        """Check if MIDI device is connected."""
        return self.port is not None and self.running


def run_midi_monitor():
    """
    Standalone MIDI monitor — prints all incoming MIDI messages.
    Run with: python3 -m src.midi_handler
    """
    print("=" * 50)
    print("🎹 MIDI Monitor — Chord Engine")
    print("=" * 50)
    print("Press keys, turn knobs, push buttons...")
    print("Press Ctrl+C to quit\n")

    available = mido.get_input_names()
    if not available:
        print("❌ No MIDI devices found!")
        return

    print(f"Available ports: {available}")
    port_name = available[0]
    print(f"Using: {port_name}\n")

    handler = MidiHandler.__new__(MidiHandler)
    handler.debug = True
    handler.on_note_on = None
    handler.on_note_off = None
    handler.on_cc = None
    handler.on_pitch_bend = None
    handler.config = {"device_name": ""}

    try:
        with mido.open_input(port_name) as port:
            print("Listening...\n")
            for msg in port:
                handler._print_debug(msg)
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped")


if __name__ == "__main__":
    run_midi_monitor()
