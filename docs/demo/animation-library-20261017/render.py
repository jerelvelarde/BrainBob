#!/usr/bin/env python3
"""Export native, timestamped gallery captures without fabricated UI or domain events."""
from pathlib import Path
import json, subprocess, shutil
from concurrent.futures import ThreadPoolExecutor
R=Path(__file__).resolve().parent
ORDER=['arrive','create','retrieve','session','update','retire','evaluator-enter','evaluator-check','evaluator-exit','promote','flag','lock','resolve','reject','answer']
GIFS={'create','retrieve','update','retire','session','evaluator-enter'}
def run(args):subprocess.run(['ffmpeg','-v','error','-y',*args],check=True)
def render(label):
 c=json.loads((R/f'{label}.capture.json').read_text());start=c['start'];duration=c['seconds']+.7;end=start+duration*1000
 assert end<=c['end']
 frames=[f for f in c['frames'] if f['at']<end];lines=['ffconcat version 1.0']
 for i,f in enumerate(frames):
  next_at=frames[i+1]['at'] if i+1<len(frames) else end
  at=start if i==0 else f['at'];seconds=(next_at-at)/1000
  lines.extend([f"file '{R/'raw'/f['name']}'",f'duration {seconds:.6f}'])
 lines.append(f"file '{R/'raw'/frames[-1]['name']}'")
 concat=R/f'{label}.ffconcat';concat.write_text('\n'.join(lines)+'\n')
 output=R/'clips'/f'{label}.mp4'
 run(['-safe','0','-i',str(concat),'-t',str(duration),'-vf','fps=15,format=yuv420p','-an','-c:v','libx264','-preset','fast','-crf','19','-threads','2','-movflags','+faststart',str(output)])
 poster=frames[round(len(frames)*(.48 if label in ['update','retire'] else .6))]
 shutil.copyfile(R/'raw'/poster['name'],R/'previews'/f'{label}.jpg')
 if label in GIFS:
  run(['-i',str(output),'-filter_complex','fps=8,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0',str(R/'previews'/f'{label}.gif')])
 return {'id':label,'label':c['button'],'scope':c['scope'],'duration':duration,'frames':len(frames),'captured_start_ms':start,'captured_end_ms':c['end'],'source':'native browser capture of isolated production scene components','domain_effects':'none','path':f'clips/{label}.mp4'}
with ThreadPoolExecutor(max_workers=3) as pool:manifest=list(pool.map(render,ORDER))
(R/'manifest.json').write_text(json.dumps({'implementation':'5196b05','resolution':[1600,900],'output_fps':15,'sampling_note':'Native screenshots sampled about 8–10 fps; timestamps preserved with repeated output frames. Silent animation previews, not live backend operations.','clips':manifest},indent=2)+'\n')
concat=R/'reel.ffconcat';concat.write_text('ffconcat version 1.0\n'+'\n'.join(f"file '{R/c['path']}'" for c in manifest)+'\n')
run(['-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(R/'brainbob-memory-animations.mp4')])
print(f"Exported {len(manifest)} clips, {len(GIFS)} GIFs, and the full reel")
