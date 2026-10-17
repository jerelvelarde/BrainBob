#!/usr/bin/env python3
"""Build a 60s silent cut from timestamped, unmodified live browser frames."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parent
capture = json.loads((ROOT / 'capture.json').read_text())
# label, source offset, duration: real-time excerpts, with cuts between operations.
edits = [
    ('office-and-new-session', 0, 4),
    ('fresh-session-final', 0, 11),
    ('approved-date-final', 0, 12),
    ('source-evidence-final', 0, 9),
    ('open-personal-preference', 0, 2),
    ('save-correction-final', 0, 10),
    ('correction-history-final', 0, 4),
    ('new-session-reuses-correction', 2, 6),
    ('office-outro', 0, 2),
]
assert sum(duration for _, _, duration in edits) == 60
lines = ['ffconcat version 1.0']
timeline = []
position = 0
for label, offset, duration in edits:
    clip = next(c for c in capture['clips'] if c['label'] == label)
    start = clip['start'] + offset * 1000
    end = start + duration * 1000
    assert end <= clip['end']
    frames = [f for f in capture['frames'] if f['label'] == label]
    prior = [f for f in frames if f['at'] <= start]
    selected = ([prior[-1]] if prior else [frames[0]]) + [f for f in frames if start < f['at'] < end and f != frames[0]]
    for i, frame in enumerate(selected):
        next_time = selected[i+1]['at'] if i+1 < len(selected) else end
        current_time = start if i == 0 else frame['at']
        seconds = (next_time - current_time) / 1000
        if seconds <= 0:
            continue
        file = (ROOT / 'raw' / frame['name']).as_posix().replace("'", "'\\''")
        lines += [f"file '{file}'", f'duration {seconds:.6f}']
    timeline.append({'label': label, 'sourceOffset': offset, 'start': position, 'end': position + duration})
    position += duration
lines.append(f"file '{(ROOT / 'raw' / selected[-1]['name']).as_posix()}'")
(ROOT / 'edit.json').write_text(json.dumps({'duration':60,'speed':1,'cuts':timeline,'unusedTake':'ask-atlas-live: initial drafting prompt, replaced with factual question'}, indent=2)+'\n')
(ROOT / 'frames.ffconcat').write_text('\n'.join(lines)+'\n')
(ROOT / 'output').mkdir(exist_ok=True)
subprocess.run(['ffmpeg','-hide_banner','-loglevel','warning','-y','-safe','0','-i',str(ROOT/'frames.ffconcat'),'-t','60','-vf','scale=1920:1080:flags=lanczos,fps=30,format=yuv420p','-an','-c:v','libx264','-preset','fast','-crf','18','-movflags','+faststart',str(ROOT/'output/brainbob-live-60s.mp4')],check=True)
print('Rendered output/brainbob-live-60s.mp4')
