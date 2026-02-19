#!/bin/bash
# Chord Engine — Raspberry Pi Setup
set -e

echo "🎹 Chord Engine — Setting up your Pi..."

sudo apt update
sudo apt install -y fluidsynth fluid-soundfont-gm python3-pip python3-pygame \
    libasound2-dev libjack-dev

pip3 install --break-system-packages mido python-rtmidi pyfluidsynth pygame

# Set up low-latency audio
echo "Configuring audio for low latency..."
if ! grep -q "audio_pwm_mode=2" /boot/config.txt 2>/dev/null; then
    echo "# Better audio quality" | sudo tee -a /boot/config.txt
    echo "audio_pwm_mode=2" | sudo tee -a /boot/config.txt
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Default SoundFont installed at: /usr/share/sounds/sf2/FluidR3_GM.sf2"
echo "Run: python3 src/main.py"
echo "MIDI debug: python3 src/main.py --midi-debug"
