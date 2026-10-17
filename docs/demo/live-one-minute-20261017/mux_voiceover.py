#!/usr/bin/env python3
"""Attach the final ElevenLabs narration without truncating speech."""
import argparse
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('audio',type=Path)
args=parser.parse_args()
audio=args.audio.resolve()
if not audio.is_file():
    parser.error('Voiceover file does not exist')
duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(audio)]))
if duration > 60:
    parser.error(f'Voiceover is {duration:.2f}s; fit it within 60s before muxing')
subprocess.run(['ffmpeg','-hide_banner','-y','-i',str(root/'output/brainbob-live-60s.mp4'),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-af','apad','-c:a','aac','-b:a','192k','-t','60','-movflags','+faststart',str(root/'output/brainbob-live-60s-vo.mp4')],check=True)
