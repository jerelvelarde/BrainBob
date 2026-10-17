"""GateMem incremental replay and external prediction format (no hidden-label access).

This is a protocol adapter, not the GateMem scorer. Official labels never reach
reset/ingest/query. The caller supplies a memory system implementing those methods.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ACTIONS = {"answer", "answer_redacted", "refuse", "no_memory"}
DOMAINS = ("medical", "office", "education", "household")


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _unique(rows, key):
    values = [row[key] for row in rows]
    if any(not isinstance(v, str) or not v for v in values):
        raise ValueError(f"{key} must be a nonempty string")
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate {key}")
    return dict(zip(values, rows))


def load(data_dir):
    """Validate the full domain before any inference; never skip broken joins."""
    directory = Path(data_dir)
    episodes = read_jsonl(directory / "episodes.jsonl")
    checkpoints = read_jsonl(directory / "checkpoints.jsonl")
    if not episodes or not checkpoints:
        raise ValueError("episodes and checkpoints must both be nonempty")
    by_id = _unique(episodes, "episode_id")
    _unique(checkpoints, "checkpoint_id")
    positions = {}
    for episode in episodes:
        if episode.get("domain") not in DOMAINS:
            raise ValueError(f"unknown domain for {episode['episode_id']}")
        turns = episode["turns"]
        _unique(turns, "turn_id")
        for turn in turns:
            public_turn(turn)  # fail before making any calls
        positions[episode["episode_id"]] = {t["turn_id"]: i for i, t in enumerate(turns)}
    for cp in checkpoints:
        if cp["episode_id"] not in by_id:
            raise ValueError(f"unknown episode in checkpoint {cp['checkpoint_id']}")
        if cp["as_of_turn_id"] not in positions[cp["episode_id"]]:
            raise ValueError(f"unknown as_of_turn_id in checkpoint {cp['checkpoint_id']}")
        public_query(cp, by_id[cp["episode_id"]])
    return episodes, checkpoints


def public_turn(turn):
    """Allowlist only observed text, timestamp, and speaker; exclude annotated ops."""
    speaker = turn["speaker"]
    return {"turn_id": turn["turn_id"], "timestamp": turn.get("timestamp"),
            "speaker": {"principal_id": speaker["principal_id"], "role": speaker["role"]},
            "text": turn["text"]}


def public_query(cp, episode):
    asker = cp["asker"]
    principal = asker["principal_id"]
    relationships = episode.get("entities", {}).get("relationships", [])
    # Same requester-centric scaffold boundary as the official base agent.
    visible = [r for r in relationships if any(
        str(k).lower().endswith("_id") and v == principal for k, v in r.items())]
    return deepcopy({"checkpoint_id": cp["checkpoint_id"], "episode_id": cp["episode_id"],
                     "as_of_turn_id": cp["as_of_turn_id"], "query_text": cp["query_text"],
                     "asker": {"principal_id": principal, "role": asker["role"]},
                     "relationships": visible})


def validate_output(output):
    if not isinstance(output, dict) or output.get("action") not in ACTIONS:
        raise ValueError("adapter must return a GateMem action")
    if not isinstance(output.get("answer"), str) or not output["answer"].strip():
        raise ValueError("adapter returned an empty or invalid answer")
    if not isinstance(output.get("answer_structured", {}), dict):
        raise ValueError("answer_structured must be an object")
    ids = output.get("used_record_ids", [])
    if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids):
        raise ValueError("used_record_ids must be a string list")
    return output


def replay(episodes, checkpoints, factory):
    """Yield external predictions; separate stores per episode, no query feedback.

    Factories receive no data. Reset receives only identity/domain. Each ingest
    sees the next observed turn. Query sees no labels, records, or future turns.
    """
    for episode in episodes:
        positions = {t["turn_id"]: i for i, t in enumerate(episode["turns"])}
        selected = sorted((cp for cp in checkpoints if cp["episode_id"] == episode["episode_id"]),
                          key=lambda cp: positions[cp["as_of_turn_id"]])
        if not selected:
            continue
        adapter = factory()
        adapter.reset({"episode_id": episode["episode_id"], "domain": episode["domain"]})
        cursor = 0
        for cp in selected:
            end = positions[cp["as_of_turn_id"]]
            while cursor <= end:
                adapter.ingest(deepcopy(public_turn(episode["turns"][cursor])))
                cursor += 1
            output = validate_output(adapter.query(public_query(cp, episode)))
            yield {"checkpoint_id": cp["checkpoint_id"], "output": output}


def preflight(data_dir):
    episodes, checkpoints = load(data_dir)
    return {"benchmark": "GateMem", "status": "data_validated_only", "score": None,
            "episodes": len(episodes), "checkpoints": len(checkpoints),
            "categories": dict(Counter(cp.get("query_type", "unknown") for cp in checkpoints)),
            "sha256": {name: hashlib.sha256((Path(data_dir) / name).read_bytes()).hexdigest()
                       for name in ("episodes.jsonl", "checkpoints.jsonl")}}
