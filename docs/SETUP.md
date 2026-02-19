# Chord Engine — Setup Guide

## Hardware Requirements

- **Raspberry Pi 4 or 5** (2GB+ RAM)
- **USB MIDI Controller** — Akai MPK Mini Play recommended, but any USB MIDI controller works
- **HDMI Display** — monitor or TV for the visual display
- **Audio Output** — headphone jack, USB audio, or HDMI audio
- **USB Cable** — to connect MIDI controller to Pi

## Software Setup

### 1. Flash Raspberry Pi OS

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to flash **Raspberry Pi OS (64-bit)** with Desktop.

### 2. Run the Setup Script

```bash
git clone https://github.com/GR3ATB0B/chord-engine.git
cd chord-engine
chmod +x setup.sh
./setup.sh
```

### 3. Connect Your MIDI Controller

Plug in the MPK Mini Play (or any USB MIDI controller) via USB. Verify it's detected:

```bash
aconnect -l
# Should show your controller
```

### 4. Run Chord Engine

```bash
python3 src/main.py
```

### Command Line Options

| Flag | Description |
|------|-------------|
| `--midi-debug` | Print all incoming MIDI messages (use this first!) |
| `--headless` | Run without display (terminal only) |
| `--dummy` | No audio output (prints notes to terminal) |
| `--monitor` | Standalone MIDI monitor mode |

## First Run — Find Your MIDI Mappings

Every MIDI controller sends different CC numbers for its knobs and buttons. Run MIDI debug mode first:

```bash
python3 src/main.py --midi-debug
```

Then:
1. Press each button — note the CC numbers
2. Turn each knob — note the CC numbers
3. Move the joystick — note the CC numbers
4. Update `config.json` with your actual CC numbers

See [MIDI_MAPPING.md](MIDI_MAPPING.md) for details.

## Audio Troubleshooting

### No sound?

```bash
# Check audio output
aplay -l

# Test FluidSynth directly
fluidsynth -a alsa /usr/share/sounds/sf2/FluidR3_GM.sf2

# Try different audio drivers in config.json:
# "audio_driver": "alsa"    ← default
# "audio_driver": "pulseaudio"
# "audio_driver": "jack"
```

### High latency?

Reduce buffer size in `config.json`:
```json
"buffer_size": 32
```

If you get audio crackling, increase it back to 64 or 128.

### HDMI audio instead of headphone jack?

```bash
# Force headphone jack output
raspi-config  # Advanced → Audio → Force 3.5mm jack
```

## Auto-Start on Boot (Optional)

Create a systemd service:

```bash
sudo tee /etc/systemd/system/chord-engine.service << 'EOF'
[Unit]
Description=Chord Engine
After=multi-user.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/chord-engine
ExecStart=/usr/bin/python3 src/main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable chord-engine
sudo systemctl start chord-engine
```
