"""Protocol tests use synthetic plumbing fixtures; these are not benchmark scores."""
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from adapters import gatemem


def fixture():
    episode = {"episode_id": "e1", "domain": "medical", "records": ["HIDDEN"],
               "entities": {"relationships": [{"subject_id": "alice", "contact_id": "bob"},
                                                {"subject_id": "eve", "contact_id": "mallory"}]},
               "turns": [{"turn_id": "t1", "text": "observed", "speaker": {"principal_id": "alice", "role": "patient"},
                          "memory_ops": ["GOLD"], "record_refs": ["SECRET"]},
                         {"turn_id": "t2", "text": "future", "speaker": {"principal_id": "bob", "role": "family"}}]}
    checkpoint = {"checkpoint_id": "c1", "episode_id": "e1", "as_of_turn_id": "t1",
                  "asker": {"principal_id": "alice", "role": "patient"}, "query_text": "what?",
                  "query_type": "privacy", "expected_action": "refuse", "leak_targets": ["GOLD"],
                  "judge_spec": {"answer": "SECRET"}, "policy_snapshot": {"private": True}}
    return episode, checkpoint


def write_data(tmp_path, episode, checkpoints):
    (tmp_path / "episodes.jsonl").write_text(json.dumps(episode) + "\n")
    (tmp_path / "checkpoints.jsonl").write_text("\n".join(map(json.dumps, checkpoints)))


def test_no_labels_or_future_turns_and_incremental_order():
    e, cp = fixture()
    cp2 = {**cp, "checkpoint_id": "c2", "as_of_turn_id": "t2"}
    seen = []
    class Adapter:
        def reset(self, data):
            assert data == {"episode_id": "e1", "domain": "medical"}
            self.turns = []
        def ingest(self, turn):
            assert set(turn) == {"turn_id", "timestamp", "speaker", "text"}
            self.turns.append(turn["text"])
        def query(self, query):
            assert set(query) == {"checkpoint_id", "episode_id", "as_of_turn_id", "query_text", "asker", "relationships"}
            assert len(query["relationships"]) == 1
            seen.append(self.turns[:])
            return {"action": "answer", "answer": "test output"}
    rows = list(gatemem.replay([e], [cp2, cp], Adapter))
    assert seen == [["observed"], ["observed", "future"]]
    assert [row["checkpoint_id"] for row in rows] == ["c1", "c2"]


def test_isolation_between_episodes():
    e, cp = fixture()
    e2, cp2 = {**e, "episode_id": "e2"}, {**cp, "episode_id": "e2", "checkpoint_id": "c2"}
    instances = []
    class Adapter:
        def __init__(self): instances.append(self)
        def reset(self, data): self.turns = []
        def ingest(self, data): self.turns.append(data)
        def query(self, data):
            assert len(self.turns) == 1
            return {"action": "no_memory", "answer": "No data"}
    assert len(list(gatemem.replay([e, e2], [cp, cp2], Adapter))) == 2
    assert len(instances) == 2


@pytest.mark.parametrize("change,reason", [({"as_of_turn_id": "absent"}, "as_of_turn_id"),
                                          ({"episode_id": "absent"}, "episode")])
def test_broken_checkpoint_fails_before_inference(tmp_path, change, reason):
    e, cp = fixture()
    write_data(tmp_path, e, [{**cp, **change}])
    with pytest.raises(ValueError, match=reason): gatemem.load(tmp_path)


def test_duplicate_checkpoint_rejected(tmp_path):
    e, cp = fixture()
    write_data(tmp_path, e, [cp, cp])
    with pytest.raises(ValueError, match="duplicate checkpoint_id"): gatemem.load(tmp_path)


def test_preflight_is_unscored_and_fingerprinted(tmp_path):
    e, cp = fixture()
    write_data(tmp_path, e, [cp])
    report = gatemem.preflight(tmp_path)
    assert report["score"] is None
    assert report["checkpoints"] == 1
    assert all(len(value) == 64 for value in report["sha256"].values())


@pytest.mark.parametrize("output", [{}, {"action": "answer", "answer": ""},
                                   {"action": "skip", "answer": "wrong"},
                                   {"action": "answer", "answer": "x", "used_record_ids": "m1"}])
def test_invalid_prediction_fails(output):
    with pytest.raises(ValueError): gatemem.validate_output(output)


def test_builtin_baseline_uses_extractor_and_scoring_compatible_trace(tmp_path, monkeypatch):
    from adapters import gatemem_brainbob
    toolkit = tmp_path / "toolkit"
    (toolkit / "bench/prompts").mkdir(parents=True)
    (toolkit / "bench/domains.py").write_text(
        'def get_domain_label(domain): return domain\n'
        'def get_query_policy_block(domain): return "policy"\n'
        'def format_relationship_fact(rel): return str(rel)\n')
    (toolkit / "bench/prompts/query_prompt.txt").write_text(
        '[SYSTEM] {global_access_policy_block}\n[REQUEST CONTEXT] {asker_principal_id}\n'
        '{relationship_facts_block}\n{retrieved_memory_block}\n{query_text}')
    monkeypatch.setenv("GATEMEM_TOOLKIT", str(toolkit))
    monkeypatch.setattr(gatemem_brainbob.curator, "extract", lambda e, role: [e.text])
    prompts = []
    def answer(role, messages):
        prompts.extend(messages)
        return '{"action":"answer","answer":"observed","used_record_ids":["m1"]}'
    monkeypatch.setattr(gatemem_brainbob.llm, "complete", answer)
    e, cp = fixture()
    rows = list(gatemem.replay([e], [cp], gatemem_brainbob.ExtractedMemoryBaseline))
    output = rows[0]["output"]
    assert "observed" in output["prompt_memory_block"]
    assert output["memory_audit"]["prompt_context"]["text"] == output["prompt_memory_block"]
    assert output["used_record_ids"] == []
    assert all(secret not in json.dumps(prompts) for secret in ["future", "GOLD", "SECRET", "expected_action"])


def test_cli_preserves_partial_failure_and_refuses_overwrite(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("gatemem_cli", Path(__file__).resolve().parents[1] / "gatemem.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    e, cp = fixture()
    data = tmp_path / "data"
    data.mkdir()
    write_data(data, e, [cp, {**cp, "checkpoint_id": "c2", "as_of_turn_id": "t2"}])
    class FailingAdapter:
        def reset(self, episode): pass
        def ingest(self, turn): pass
        def query(self, checkpoint):
            if checkpoint["checkpoint_id"] == "c2": raise RuntimeError("unavailable")
            return {"action": "answer", "answer": "first"}
    monkeypatch.setattr(gatemem, "TestAdapter", FailingAdapter, raising=False)
    output = tmp_path / "run"
    monkeypatch.setattr(sys, "argv", ["gatemem.py", "predict", "--data-dir", str(data),
                                     "--adapter", "adapters.gatemem:TestAdapter", "--output", str(output)])
    with pytest.raises(RuntimeError): cli.main()
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "failed_incomplete"
    assert manifest["completed_checkpoints"] == 1
    assert manifest["selected_checkpoints"] == 2
    assert manifest["score"] is None
    assert len((output / "predictions.jsonl").read_text().splitlines()) == 1
    with pytest.raises(FileExistsError): cli.main()
