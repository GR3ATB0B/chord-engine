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
        gain = self.config.get("gain", 1.0)

        if not os.path.exists(soundfont):
            print(f"❌ SoundFont not found: {soundfont}")
            print("   Install: sudo apt install fluid-soundfont-gm")
            print("   Or download a .sf2 and update config.json")
            return False

        try:
            # Create FluidSynth instance with low-latency settings
            self.fs = fluidsynth.Synth(gain=gain)

            # Audio buffer settings (larger = stable, less choppy)
            buffer_size = self.config.get("buffer_size", 2048)
            self.fs.setting("audio.period-size", buffer_size)
            self.fs.setting("audio.periods", 8)
            self.fs.setting("synth.sample-rate", 44100.0)
            self.fs.setting("synth.polyphony", 64)
            self.fs.setting("audio.realtime-prio", 0)
            self.fs.setting("synth.overflow.percussion", 5000.0)
            self.fs.setting("synth.overflow.sustained", 5000.0)

            # Start audio driver
            # Set audio device if configured
            device = self.config.get("audio_device", "")
            if device:
                self.fs.setting("audio.alsa.device", device)
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
        Uses legato: new notes start before old ones release for smooth transitions.
        """
        if not self._initialized:
            return

        new_notes = [n for n, v in note_velocity_pairs]
        old_notes = self.current_notes[:]

        # Notes that continue (in both old and new) — don't touch them
        keep = set(new_notes) & set(old_notes)
        # Notes to add
        add = [(n, v) for n, v in note_velocity_pairs if n not in keep]
        # Notes to remove
        remove = [n for n in old_notes if n not in keep]

        # Play new notes FIRST (before killing old ones) for overlap
        for note, velocity in add:
            self.fs.noteon(0, note, velocity)

        # Then release old notes that aren't in the new chord
        for note in remove:
            self.fs.noteoff(0, note)

        self.current_notes = list(new_notes)

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

    def set_sustain(self, value):
        """Set sustain level from CC value (0-127)."""
        if not self._initialized:
            return
        self.fs.cc(0, 64, min(127, value))

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

    def set_sustain(self, value):
        pass

    def shutdown(self):
        print("🔇 Dummy synth stopped")
