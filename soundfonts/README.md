# SoundFonts

Place `.sf2` SoundFont files here and update `config.json` to point to them.

## Free SoundFonts

| Name | Size | Sounds | Link |
|------|------|--------|------|
| **FluidR3_GM** | 141 MB | Full General MIDI | `sudo apt install fluid-soundfont-gm` (installed at `/usr/share/sounds/sf2/FluidR3_GM.sf2`) |
| **MuseScore_General** | 208 MB | High quality GM | [Download](https://ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/) |
| **GeneralUser GS** | 30 MB | Lightweight GM | [Download](https://schristiancollins.com/generaluser.php) |
| **Timbres of Heaven** | 380 MB | Premium quality | [Download](http://midkar.com/soundfonts/) |
| **Nice Keys** | ~5 MB | Piano only (great!) | [Download](https://freepats.zenvoid.org/) |

## Quick Setup

```bash
# The easiest option — comes with Debian/Ubuntu/Pi OS:
sudo apt install fluid-soundfont-gm

# Then config.json already points to the right place:
# "soundfont": "/usr/share/sounds/sf2/FluidR3_GM.sf2"
```

## Custom SoundFonts

1. Download a `.sf2` file
2. Place it in this `soundfonts/` directory
3. Update `config.json`:
   ```json
   "soundfont": "soundfonts/YourFont.sf2"
   ```
4. Restart Chord Engine
