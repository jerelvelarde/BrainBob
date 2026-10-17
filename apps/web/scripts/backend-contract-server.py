"""Real HTTP/SSE + memory/ACL/maintenance stack with deterministic model doubles.

Run from the repo root with backend/.venv/bin/python. State is temporary, model
calls fail closed, and this verifies integration only, never model quality.
"""
import os
import pathlib
import sys
import tempfile
from types import SimpleNamespace

BACKEND = pathlib.Path(__file__).resolve().parents[3] / "backend"
sys.path.insert(0, str(BACKEND))

import uvicorn
from brainbob import curator, events, llm, maintain
from brainbob.acl import Org
from brainbob.evaluator import Evaluator
from brainbob.memory import MemoryStore
from brainbob.types import Answer, Episode, Task
from server import create_app


def no_inference(*args, **kwargs):
    raise RuntimeError("Inference is forbidden in the contract smoke server")


if __name__ == "__main__":
    llm.complete = no_inference
    curator.extract = lambda episode, role: [episode.text]
    with tempfile.TemporaryDirectory(prefix="brainbob-contract-") as state:
        events.reset()
        store = MemoryStore(str(pathlib.Path(state) / "memory.jsonl"))
        agent = SimpleNamespace(answer=lambda question, memories, now=None, **kw:
                                Answer(" | ".join(m.text for m in memories) or "No memory", [m.id for m in memories]))
        app = create_app(store, None, agent, Evaluator(store), lambda q, gold, answer: gold == answer,
                         events=events, episode_factory=Episode, task_factory=Task,
                         org=Org.load(BACKEND / "fixtures/rusty_rod/org.json"),
                         episodes_path=str(pathlib.Path(state) / "episodes.jsonl"),
                         ingest=lambda ep, st, org: maintain.ingest(ep, st, org, judge=lambda *_: "unrelated"))
        print("CONTRACT TEST SERVER: deterministic model doubles, temporary state, no inference", flush=True)
        uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "3001")))
