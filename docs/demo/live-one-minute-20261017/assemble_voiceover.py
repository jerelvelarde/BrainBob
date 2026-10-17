#!/usr/bin/env python3
"""Fit the seven downloaded ElevenLabs clips to the live edit without cutting speech."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import wave

ROOT = Path(__file__).resolve().parent
RATE = 48000
SAMPLE_BYTES = 2
blocks = json.loads((ROOT / 'voiceover-timing.json').read_text())
clips = sorted((ROOT / 'elevenlabs').glob('[0-9][0-9]-*.mp3'))
if len(clips) != len(blocks):
    raise SystemExit('Expected exactly one downloaded clip for each script block')

track = bytearray()
manifest = []
for block, clip in zip(blocks, clips):
    pcm = subprocess.check_output([
        'ffmpeg', '-v', 'error', '-i', str(clip),
        '-ar', str(RATE), '-ac', '1', '-f', 's16le', '-',
    ])
    original_duration = len(pcm) / SAMPLE_BYTES / RATE
    window = block['end'] - block['start']
    available = window - 0.25  # 100ms lead-in and at least 150ms after the clip
    tempo = max(1.0, original_duration / available)
    if tempo > 1.15:
        raise SystemExit(f'{clip.name} requires a new take; tempo would be {tempo:.3f}')
    if tempo > 1:
        pcm = subprocess.check_output([
            'ffmpeg', '-v', 'error', '-i', str(clip),
            '-af', f'atempo={tempo:.9f}', '-ar', str(RATE), '-ac', '1',
            '-f', 's16le', '-',
        ])
    before = bytes(round(0.1 * RATE) * SAMPLE_BYTES)
    padding = round(window * RATE) * SAMPLE_BYTES - len(before) - len(pcm)
    if padding < 0:
        raise SystemExit(f'{clip.name} still exceeds its scene; speech was not truncated')
    track.extend(before + pcm + bytes(padding))
    manifest.append({
        **block,
        'file': str(clip.relative_to(ROOT)),
        'sha256': hashlib.sha256(clip.read_bytes()).hexdigest(),
        'source_duration_seconds': original_duration,
        'tempo_multiplier': tempo,
        'audio_start_seconds': block['start'] + 0.1,
        'audio_end_seconds': block['start'] + 0.1 + len(pcm) / SAMPLE_BYTES / RATE,
    })

with tempfile.TemporaryDirectory() as temp:
    raw = Path(temp) / 'aligned.wav'
    with wave.open(str(raw), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(SAMPLE_BYTES)
        wav.setframerate(RATE)
        wav.writeframes(track)
    subprocess.run([
        'ffmpeg', '-v', 'error', '-y', '-i', str(raw),
        '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
        '-ar', str(RATE), '-c:a', 'pcm_s16le', str(ROOT / 'output/voiceover.wav'),
    ], check=True)

(ROOT / 'elevenlabs/alignment.json').write_text(json.dumps({
    'assembled_at': datetime.now(timezone.utc).isoformat(),
    'voice': 'Roger - Laid-Back, Casual, Resonant',
    'model': 'Eleven v4',
    'settings': {'stability': 0.5, 'similarity': 0.75},
    'selection': 'Generation 1 for each of seven text blocks',
    'method': 'Generated and downloaded through signed-in ElevenLabs Chrome UI',
    'processing': 'Silence padding; pitch-preserving tempo only where needed; -16 LUFS normalization',
    'timing_note': 'Clip placement, not word-level forced alignment',
    'blocks': manifest,
}, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
