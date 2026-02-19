"""
synth_engine.py — Sound generation via FluidSynth.

Loads SoundFont (.sf2) files and handles real-time audio output.
Designed for low latency on Raspberry Pi.
"""

import os


class SynthEngine:
    """FluidSynth-based audio synthesis engine."""

    def __init__(self, config):
        self.config = config.synth
        self.fs = None
        self.sfid = None
        self.current_notes = []  # Currently sounding MIDI notes
        self._initialized = False

    def initialize(self):
        """Initialize FluidSynth with configured settings."""
        try:
            import fluidsynth
        except ImportError:
            print("❌ pyfluidsynth not installed!")
            print("   Run: pip3 install pyfluidsynth")
            print("   Also need: sudo apt install fluidsynth")
            return False

        soundfont = self.config.get("soundfont", "/usr/share/sounds/sf2/FluidR3_GM.sf2")
        driver = self.config.get("audio_driver", "alsa")
        gain = self.config.get("gain", 0.8)

        if not os.path.exists(soundfont):
            print(f"❌ SoundFont not found: {soundfont}")
            print("   Install: sudo apt install fluid-soundfont-gm")
            print("   Or download a .sf2 and update config.json")
            return False

        try:
            # Create FluidSynth instance with low-latency settings
            self.fs = fluidsynth.Synth(gain=gain)

            # Set small buffer for low latency
            buffer_size = self.config.get("buffer_size", 64)
            self.fs.setting("audio.period-size", buffer_size)
            self.fs.setting("audio.periods", 2)

            # Start audio driver
            self.fs.start(driver=driver)

            # Load SoundFont
            self.sfid = self.fs.sfload(soundfont)
            if self.sfid == -1:
                print(f"❌ Failed to load SoundFont: {soundfont}")
                return False

            # Select initial instrument
            instrument = self.config.get("instrument", 0)
            self.fs.program_select(0, self.sfid, 0, instrument)

            # Set reverb
            reverb = self.config.get("reverb", 0.4)
            self.fs.set_reverb(0.8, 0.3, reverb * 100, 0.5)

            self._initialized = True
            print(f"🔊 Synth ready — SoundFont: {os.path.basename(soundfont)}")
            return True

        except Exception as e:
            print(f"❌ Synth init failed: {e}")
            return False

    def play_chord(self, note_velocity_pairs):
        """
        Play a chord (list of (note, velocity) tuples).
        Stops any currently sounding notes first.
        """
        if not self._initialized:
            return

        # Stop current notes
        self.stop_chord()

        # Play new notes
        for note, velocity in note_velocity_pairs:
            self.fs.noteon(0, note, velocity)
            self.current_notes.append(note)

    def stop_chord(self):
        """Stop all currently sounding notes."""
        if not self._initialized:
            return

        for note in self.current_notes:
            self.fs.noteoff(0, note)
        self.current_notes.clear()

    def set_instrument(self, program):
        """Change instrument (General MIDI program number 0-127)."""
        if not self._initialized:
            return
        program = max(0, min(127, program))
        self.fs.program_select(0, self.sfid, 0, program)
        print(f"🎸 Instrument: {program}")

    def set_volume(self, value):
        """Set volume from CC value (0-127)."""
        if not self._initialized:
            return
        # CC 7 is standard volume
        self.fs.cc(0, 7, value)

    def set_reverb(self, cc_value):
        """Set reverb amount from CC value (0-127)."""
        if not self._initialized:
            return
        level = (cc_value / 127.0) * 100
        self.fs.set_reverb(0.8, 0.3, level, 0.5)

    def set_modulation(self, value):
        """Set modulation from CC value (0-127)."""
        if not self._initialized:
            return
        self.fs.cc(0, 1, value)

    def pitch_bend(self, value):
        """Set pitch bend. value: -8192 to 8191."""
        if not self._initialized:
            return
        self.fs.pitch_bend(0, value + 8192)

    def shutdown(self):
        """Clean shutdown of the synth engine."""
        if self._initialized:
            self.stop_chord()
            if self.fs:
                self.fs.delete()
            self._initialized = False
            print("🔇 Synth stopped")


class DummySynth:
    """Fallback synth that just prints — for testing without audio."""

    def __init__(self):
        self.current_notes = []
        self._initialized = True

    def initialize(self):
        print("🔊 Dummy synth (no audio output)")
        return True

    def play_chord(self, note_velocity_pairs):
        self.stop_chord()
        notes = [n for n, v in note_velocity_pairs]
        note_names = []
        for n in notes:
            name = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][n % 12]
            note_names.append(f"{name}{n // 12 - 1}")
        self.current_notes = notes
        print(f"  🎵 Playing: {', '.join(note_names)}")

    def stop_chord(self):
        self.current_notes.clear()

    def set_instrument(self, program):
        print(f"  🎸 Instrument: {program}")

    def set_volume(self, value):
        pass

    def set_reverb(self, cc_value):
        pass

    def set_modulation(self, value):
        pass

    def pitch_bend(self, value):
        pass

    def shutdown(self):
        print("🔇 Dummy synth stopped")
