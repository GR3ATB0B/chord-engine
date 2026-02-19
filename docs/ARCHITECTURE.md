# Architecture

## Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  MPK Mini   │────▶│ midi_handler  │────▶│ chord_engine │────▶│ synth_engine │──▶ 🔊 Audio
│  Play (USB) │     │  (callbacks)  │     │  (the brain) │     │ (FluidSynth) │
└─────────────┘     └──────────────┘     └──────┬───────┘     └──────────────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │   display     │──▶ 🖥️ HDMI
                                          │  (PyGame)     │
                                          └──────────────┘
```

## Module Responsibilities

| Module | Role | Thread |
|--------|------|--------|
| `main.py` | App lifecycle, wiring | Main |
| `midi_handler.py` | MIDI input, event dispatch | mido callback (background) |
| `chord_engine.py` | Chord generation, state | Called from MIDI callback |
| `voice_leading.py` | Smooth voice transitions | Called from chord_engine |
| `synth_engine.py` | Audio output via FluidSynth | Called from MIDI callback |
| `display.py` | Visual UI via PyGame | Main thread (render loop) |
| `config.py` | Settings management | Startup |

## Threading Model

- **MIDI callback thread** (managed by mido/rtmidi): receives MIDI messages, calls into chord_engine and synth_engine under a lock
- **Main thread**: runs the PyGame display loop at 60fps, reads shared state under the same lock
- Thread safety via `threading.Lock` — MIDI callbacks write state, display reads it

## Voice Leading

The voice leading algorithm (`voice_leading.py`) is the secret sauce. When you change from one chord to another:

1. Generate pitch classes for the new chord
2. For each pitch class, consider candidates in multiple octaves near the previous voicing
3. Find the assignment of new notes to old voice positions that minimizes total semitone movement
4. For ≤4 voices, tries all permutations (exact optimal solution)
5. For larger voicings, uses greedy placement

This means transitions sound smooth and musical — voices move by small intervals rather than jumping around.

## Key Mode

When key mode is active (e.g., "C Major"):
- Any note you play gets mapped to the nearest scale degree
- The chord type is automatically set to the diatonic chord for that degree
- I=Major, ii=minor, iii=minor, IV=Major, V=Major, vi=minor, vii°=dim
