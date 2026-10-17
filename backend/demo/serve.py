"""Start server.py --legacy inside the demo state directory, on any port.

    .venv/Scripts/python demo/serve.py                  # port 3001, isolated cache (state/cache)
    .venv/Scripts/python demo/serve.py --port 3002
    .venv/Scripts/python demo/serve.py --shared-cache   # reuse backend/cache (see DEMO.md)

Equivalent to `cd demo/state && ../../.venv/Scripts/python ../../server.py --legacy`, except that
server.py hard-codes port 3001 and the shared disk cache; this wrapper only overrides those two
(it does not change server.py)."""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=3001)
    p.add_argument("--state", default=os.path.join(HERE, "state"))
    p.add_argument("--shared-cache", action="store_true",
                   help="use backend/cache: identical prompts return the stored completion of an earlier real call")
    a = p.parse_args()
    state = os.path.abspath(a.state)
    os.makedirs(state, exist_ok=True)
    os.chdir(state)  # server.py writes memory.jsonl / events.jsonl / episodes.jsonl in the cwd
    sys.path.insert(0, BACKEND)
    from brainbob import llm
    if not a.shared_cache:
        llm.CACHE = os.path.join(state, "cache")  # wiped by reset.py, so every model call is live
        os.makedirs(llm.CACHE, exist_ok=True)
    import uvicorn
    run = uvicorn.run
    uvicorn.run = lambda app, **kw: run(app, **{**kw, "port": a.port})
    import server
    sys.argv = [server.__file__, "--legacy"]
    print(f"demo state: {state}\ncache: {llm.CACHE}\nport: {a.port}", flush=True)
    server.main()


if __name__ == "__main__":
    main()
