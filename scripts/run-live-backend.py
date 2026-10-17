"""Launch Bonan's unmodified backend with isolated persistent data and a verified Crusoe connection."""
from pathlib import Path
import argparse
import json
import os
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify configured models with real provider calls, then exit')
    parser.add_argument('--skip-preflight', action='store_true', help='Start directly after a separate successful provider check; does not bypass backend credentials or errors')
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data' / 'workspace')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'backend'))
    # Local application defaults. Benchmark and backend defaults remain unchanged.
    os.environ.setdefault('BRAINBOB_AGENT_MODEL', 'nvidia/NVIDIA-Nemotron-3-Super-120B-A12B')
    os.environ.setdefault('BRAINBOB_CURATOR_MODEL', 'nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B')
    from brainbob import llm
    from openai import OpenAI
    checked = set()
    for role in ([] if args.skip_preflight and not args.check else ['curator', 'agent', 'judge']):
        config = llm.configuration()[role]
        key = os.environ.get(f'BRAINBOB_{role.upper()}_API_KEY') or os.environ.get('BRAINBOB_API_KEY')
        if not key:
            path = Path.home() / '.config' / 'crusoe' / 'api.key'
            if not path.is_file() or not path.read_text().strip():
                raise SystemExit('Crusoe key missing. Save it to ~/.config/crusoe/api.key or set BRAINBOB_API_KEY. Browser login alone does not authorize API requests.')
            key = path.read_text().strip()
        identity = (config['base_url'], config['model'])
        if identity in checked:
            continue
        try:
            client = OpenAI(api_key=key, base_url=config['base_url'], timeout=45, max_retries=2)
            request = dict(model=config['model'], messages=[{'role':'user','content':'Reply with the single word ready.'}], max_tokens=256, temperature=0)
            if config.get('extra_body'):
                request['extra_body'] = config['extra_body']
            result = client.chat.completions.create(**request)
            if not result.choices[0].message.content:
                raise RuntimeError('empty provider response')
        except Exception as error:
            # Provider exception strings may include request headers or credentials.
            raise SystemExit(f'Inference preflight failed for {role}: {type(error).__name__} (HTTP {getattr(error, "status_code", "n/a")}). Check the key, expiry, credits, and model configuration.') from None
        checked.add(identity)
        print(json.dumps({'provider':config['base_url'], 'model':result.model, 'role':role, 'live':True, 'prompt_tokens':result.usage.prompt_tokens, 'completion_tokens':result.usage.completion_tokens}), flush=True)
    if args.check:
        return
    args.data_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(args.data_dir)
    sys.argv = [str(ROOT / 'backend' / 'server.py')]
    runpy.run_path(sys.argv[0], run_name='__main__')

if __name__ == '__main__':
    main()
