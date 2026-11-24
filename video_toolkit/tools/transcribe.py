"""Transcribe speech offline with Whisper (to check what a voiceover actually says).

Usage: python transcribe.py <audio or video> [start_s] [end_s] [model, default openai/whisper-small]
Whisper reads at most 30 s at a time, so longer audio is transcribed in 30 s chunks.
"""
import subprocess
import sys
import tempfile

import librosa
from transformers import WhisperForConditionalGeneration, WhisperProcessor

path = sys.argv[1]
start = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
end = float(sys.argv[3]) if len(sys.argv) > 3 else None
model_id = sys.argv[4] if len(sys.argv) > 4 else "openai/whisper-small"

with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", tmp.name],
                   check=True)
    audio, sr = librosa.load(tmp.name, sr=16000)
audio = audio[int(start * sr):int(end * sr) if end else None]

proc = WhisperProcessor.from_pretrained(model_id)
model = WhisperForConditionalGeneration.from_pretrained(model_id)
for i in range(0, len(audio), 30 * sr):
    chunk = audio[i:i + 30 * sr]
    feats = proc(chunk, sampling_rate=sr, return_tensors="pt").input_features
    ids = model.generate(feats, language="en", task="transcribe")
    t0 = start + i / sr
    print(f"[{t0:6.1f}s] {proc.batch_decode(ids, skip_special_tokens=True)[0].strip()}")
