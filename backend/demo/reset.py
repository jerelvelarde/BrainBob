"""Wipe the demo state directory (default backend/demo/state/) and print the start commands.

    .venv/Scripts/python demo/reset.py                                   # empty state
    .venv/Scripts/python demo/reset.py --restore results/<ts>-demo        # recorded replay state

Stop the demo server first: it keeps memories, tasks and evaluator evidence in memory, so wiping
files under a running server leaves it inconsistent."""
import argparse
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
STATE_FILES = ("memory.jsonl", "events.jsonl", "episodes.jsonl")


def reset(state, restore=None):
    state = os.path.abspath(state)
    if os.path.basename(state) != "state" and not os.path.exists(os.path.join(state, ".demo-state")):
        raise SystemExit(f"refusing to wipe {state}: not a demo state directory")
    if os.path.isdir(state):
        shutil.rmtree(state)
    os.makedirs(state)
    open(os.path.join(state, ".demo-state"), "w").close()
    if restore:
        src = os.path.join(os.path.abspath(restore), "state")
        for f in STATE_FILES:
            if os.path.exists(os.path.join(src, f)):
                shutil.copy(os.path.join(src, f), os.path.join(state, f))
    return state


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--state", default=os.path.join(HERE, "state"))
    p.add_argument("--restore", help="a results/<ts>-demo directory: copy its recorded state/ in (replay)")
    a = p.parse_args()
    state = reset(a.state, a.restore)
    print(f"{'restored' if a.restore else 'reset'}: {state}")
    print("start the backend (from backend/):")
    print("  .venv/Scripts/python demo/serve.py --port 3001")
    print("  # same as: cd demo/state && ../../.venv/Scripts/python ../../server.py --legacy  (port 3001, shared cache)")
    if not a.restore:
        print("then seed it:   .venv/Scripts/python demo/seed.py --base http://127.0.0.1:3001")


if __name__ == "__main__":
    main()
