# Video toolkit: lipsync presenter, voice, overlays and multi-format export

Everything used to make the Nigerian healthcare campaign video, packaged so a new Mac can do the
same work: a lipsynced presenter, voice separation and replacement, photo cards, text fixes baked
into slides, and widescreen / iPhone / TV / end-slate exports.

## Set up a new iMac (Apple silicon, M1 or newer)

1. Copy this whole `video_toolkit` folder to the new Mac (AirDrop, USB drive or iCloud Drive).
2. Optional, saves a 4 GB download: copy `~/MuseTalk/models` from the old Mac onto a USB drive.
3. On the new Mac, open Terminal and run:

```bash
bash ~/Downloads/video_toolkit/setup_new_mac.sh
```

If you copied the models to a drive, run this instead:

```bash
MODELS_FROM=/Volumes/YOUR_DRIVE/models bash ~/Downloads/video_toolkit/setup_new_mac.sh
```

The first run takes 30–60 minutes and needs about 15 GB of free space. If it stops after
installing the Xcode command line tools, run it again. It's safe to re-run at any time.

What it installs: Xcode command line tools, Homebrew, Python 3.10, ffmpeg, MuseTalk (pinned to the
tested version, with the Apple-GPU patch), the exact Python packages from the original Mac, the
model weights, Demucs (voice separation), Whisper (transcription), and Claude's saved house rules.

## Things the script can't install

- **Claude desktop app**: install from claude.ai/download and sign in with the same account.
- **ElevenLabs connector** (voices, voice changer, image generation): it belongs to your Claude
  account, so it carries over when you sign in. Check it's connected under Settings → Connectors.
- **Fonts**: the tools use Avenir Next and Arial, which come with macOS.

## Using it

Open a Claude session in `~/MuseTalk/video_toolkit` and ask for what you want, as before. Claude
reads the tools below. To rebuild the Nigerian healthcare deliverables yourself:

```bash
bash ~/MuseTalk/video_toolkit/projects/nigerian_healthcare/build.sh
```

Add `--relipsync` to re-run the presenter lipsync instead of using the saved one (about 12 minutes).
Videos land in `projects/nigerian_healthcare/output/`.

## What's in here

| Path | What it does |
|---|---|
| `setup_new_mac.sh` | One-time setup described above |
| `tools/run_lipsync.sh` | MuseTalk lipsync: `run_lipsync.sh <face video or still clip> <voice.wav> <out.mp4>` (Apple GPU, falls back to CPU) |
| `tools/separate_voice.sh` | Splits any video/audio into `vocals.wav` and `no_vocals.wav` (music) with Demucs |
| `tools/make_alpha.py` | Cuts a presenter out of a plain background (for the corner/no-circle look) |
| `tools/make_cards.py` | Framed photo cards with name and role captions, any size |
| `tools/loudnorm.sh` | Two-pass loudness: −23 LUFS for TV, −14 for social |
| `tools/transcribe.py` | Offline Whisper transcription, e.g. to check how a voiceover pronounces "PBAT" |
| `tools/overlay.sh` | Simple round-badge corner overlay (the first version of the presenter) |
| `assets/avatar/` | The presenter image and her cut-out mask |
| `projects/nigerian_healthcare/` | This campaign: inputs, photos, layout scripts and `build.sh` |
| `claude/` | Claude's saved rules (PBAT is said "P-Bat"), installed by the setup script |
| `patches/` | The small MuseTalk change that lets it use the Apple GPU |

### Project scripts (`projects/nigerian_healthcare/`)

| Script | Output |
|---|---|
| `patch_source.py` | Repaints end-card lines: "This message is approved by the…" and the new disclosure wording |
| `composite.py` | Widescreen: presenter glides to an empty spot per slide; Tinubu/Shettima and Tompolo/Asuku cards animate in |
| `composite_vertical.py` | iPhone 9:16: slides enlarged (split text/photo on wide slides), presenter as a corner inset, large cards |
| `composite_tv.py` | TV 1920×1080 25 fps, overlays inside the safe area |
| `make_endslate.py` | 10 s end slate with photos and names typing out |

Positions and timings are at the top of each script, in plain lists, so they're easy to adjust.
