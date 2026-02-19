# MIDI Mapping Guide

## Finding Your CC Numbers

Every MIDI controller has different CC assignments. You need to discover yours.

### Step 1: Run MIDI Debug Mode

```bash
python3 src/main.py --midi-debug
```

### Step 2: Map Everything

Press/turn each control and write down what you see:

| Control | CC Number | Notes |
|---------|-----------|-------|
| Button 1 | ? | |
| Button 2 | ? | |
| Button 3 | ? | |
| Button 4 | ? | |
| Button 5 | ? | |
| Button 6 | ? | |
| Button 7 | ? | |
| Button 8 | ? | |
| Knob 1 | ? | |
| Knob 2 | ? | |
| Knob 3 | ? | |
| Knob 4 | ? | |
| Joystick X | ? | |
| Joystick Y | ? | |

### Step 3: Update config.json

Edit the `cc_map`, `knob_map`, and `joystick` sections with your actual CC numbers.

**Buttons** — each one triggers a chord type:
```json
"button_1": {"cc": YOUR_NUMBER, "action": "chord_type", "value": "major"}
```

**Knobs** — continuous control:
```json
"knob_1a": {"cc": YOUR_NUMBER, "action": "inversion"}
```

**Joystick:**
```json
"x": {"cc": YOUR_NUMBER, "action": "pitch_bend"}
```

## MPK Mini Play Defaults

The MPK Mini Play typically uses these CC numbers (but verify with debug mode!):

- **Knobs (Bank A):** CC 70, 71, 72, 73
- **Knobs (Bank B):** CC 74, 75, 76, 77
- **Buttons:** Varies by preset — often CC 20-27 or note messages
- **Joystick X:** CC 1 (Mod Wheel) or Pitch Bend
- **Joystick Y:** CC 2 (Breath)

⚠️ The MPK Mini Play buttons can be set to send CC messages or Note On/Off messages depending on the Akai preset editor. For Chord Engine, **CC mode works best for buttons**.

## Available Actions

| Action | Description | Used With |
|--------|-------------|-----------|
| `chord_type` | Set chord type (needs `value`) | Buttons |
| `inversion` | Set inversion (0-127 → 0-3) | Knobs |
| `spread` | Set voicing spread (0-127) | Knobs |
| `volume` | Set volume (0-127) | Knobs |
| `reverb` | Set reverb amount (0-127) | Knobs |
| `pitch_bend` | Pitch bend | Joystick |
| `modulation` | Modulation | Joystick |

## Chord Type Values

Use these in button `value` fields:

`major`, `minor`, `sus2`, `sus4`, `dim`, `aug`, `dom7`, `maj7`, `min7`, `dim7`, `aug7`, `add9`, `min9`, `maj9`, `power`, `6`, `min6`, `9`, `11`, `13`
