# 🎹 Chord Engine

**A DIY chord synthesizer inspired by the [Telepathic Instruments Orchid](https://www.telepathicinstruments.com/).**

Play a single note → get a full chord voicing. Smooth voice leading, real-time visualization, and total control via knobs and buttons. Built for Raspberry Pi + any USB MIDI controller.

> Why pay $650 when you can build it yourself? 🚀

![Demo Screenshot](docs/screenshot-placeholder.png)

## What It Does

1. **Press one key** on your MIDI controller → Chord Engine generates a full chord
2. **Turn knobs** to change chord type, inversion, voicing spread, reverb
3. **Press buttons** to switch between Major, Minor, Sus2, Dom7, Maj7, etc.
4. **Voice leading** makes transitions between chords buttery smooth
5. **Visual display** shows the chord name, piano visualization, and all settings
6. **Key mode** locks to a musical key — every note gives you the right diatonic chord

## Hardware

| Component | Details |
|-----------|---------|
| **Computer** | Raspberry Pi 4 or 5 (2GB+ RAM) |
| **MIDI Controller** | Akai MPK Mini Play (or any USB MIDI controller) |
| **Display** | Any HDMI monitor/TV |
| **Audio** | Pi headphone jack, USB audio, or HDMI audio |

## Quick Start

```bash
# Clone
git clone https://github.com/GR3ATB0B/chord-engine.git
cd chord-engine

# Setup (Raspberry Pi)
chmod +x setup.sh
./setup.sh

# Plug in your MIDI controller, then:
python3 src/main.py
```

### First Time? Find Your MIDI Mappings

```bash
# Run MIDI debug mode — press every button, turn every knob
python3 src/main.py --midi-debug

# Note the CC numbers, then update config.json
```

See [docs/MIDI_MAPPING.md](docs/MIDI_MAPPING.md) for the full guide.

## Command Line Options

```bash
python3 src/main.py                # Normal mode (display + audio)
python3 src/main.py --midi-debug   # Print all MIDI messages
python3 src/main.py --headless     # No display (terminal only)
python3 src/main.py --dummy        # No audio (prints notes to terminal)
python3 src/main.py --monitor      # Standalone MIDI monitor
```

## Configuration

Edit `config.json` to customize:

- **MIDI CC mappings** — match your controller's actual CC numbers
- **Chord types** on each button
- **SoundFont** path
- **Audio driver** (alsa, pulseaudio, jack)
- **Display settings** (resolution, fullscreen)

## Default MIDI Mapping

| Control | Assignment |
|---------|-----------|
| Keys | Root note input |
| Button 1-8 | Maj, Min, Sus2, Sus4, Dim, Aug, Dom7, Maj7 |
| Knob 1A | Inversion (root/1st/2nd/3rd) |
| Knob 2A | Voicing spread (tight → wide) |
| Knob 3A | Volume |
| Knob 4A | Reverb |
| Joystick X | Pitch bend |
| Joystick Y | Modulation |

## Chord Types

Major, Minor, Sus2, Sus4, Diminished, Augmented, Dom7, Maj7, Min7, Dim7, Aug7, Add9, Min9, Maj9, Power, 6, Min6, 9, 11, 13

## Architecture

```
MIDI Controller → midi_handler → chord_engine → synth_engine → 🔊 Audio
                                      ↓
                                   display → 🖥️ HDMI
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full breakdown.

## Inspiration & Credits

- **[Telepathic Instruments Orchid](https://www.telepathicinstruments.com/)** — the $650 chord synth that inspired this project
- **[Minichord](https://github.com/benwis/minichord)** — another DIY chord instrument project
- **[FluidSynth](https://www.fluidsynth.org/)** — the open-source software synthesizer powering the audio

## Tech Stack

- **Python 3.9+** — main language
- **mido + python-rtmidi** — MIDI input
- **pyfluidsynth** — audio synthesis via SoundFonts
- **PyGame** — visual display
- **Raspberry Pi OS** — platform

## License

MIT — build your own, remix it, make it yours.

---

*Built by Nash 🎹*
