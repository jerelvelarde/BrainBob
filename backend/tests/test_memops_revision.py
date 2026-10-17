"""Canonical adapter pinning with fake modules: no torch, downloads, or inference."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/memops-small"
sys.path.insert(0, str(EXP))
import bridge


def fake_runtime(monkeypatch):
    calls = []
    model = SimpleNamespace(eval=lambda: None)
    model.to = lambda device: model
    class Loader:
        @staticmethod
        def from_pretrained(source, **kwargs):
            return model
    class Peft:
        @staticmethod
        def from_pretrained(base, source, **kwargs):
            calls.append((source, kwargs))
            return model
    class API:
        def __init__(self, **kwargs): pass
        def model_info(self, source, revision=None):
            calls.append(("model_info", {"source": source, "revision": revision}))
            return SimpleNamespace(sha=revision or "resolved-other-revision")
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(
        bfloat16="fake-bf16", float32="fake-fp32", cuda=SimpleNamespace(is_available=lambda: False)))
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(AutoModelForCausalLM=Loader, AutoTokenizer=Loader))
    monkeypatch.setitem(sys.modules, "peft", SimpleNamespace(PeftModel=Peft))
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(HfApi=API))
    return calls


@pytest.mark.parametrize("adapter,requested,expected", [
    (bridge.CANONICAL_ADAPTER, None, bridge.CANONICAL_ADAPTER_REVISION),
    (bridge.CANONICAL_ADAPTER, "explicit-revision", "explicit-revision"),
    ("other/repository", None, None),
])
def test_local_generator_passes_revision_to_peft_and_provenance(monkeypatch, adapter, requested, expected):
    calls = fake_runtime(monkeypatch)
    generator = bridge.local_generator(adapter=adapter, adapter_revision=requested)
    assert calls == [(adapter, {"revision": expected})]
    assert generator.model_id.endswith("+" + adapter + ("@" + expected if expected else ""))
    assert bridge.make_judge(generator).model_id == generator.model_id


def test_local_directory_does_not_receive_hub_pin(monkeypatch, tmp_path):
    calls = fake_runtime(monkeypatch)
    generator = bridge.local_generator(adapter=str(tmp_path))
    assert calls == [(str(tmp_path), {"revision": None})]
    assert generator.model_id.endswith("+" + str(tmp_path))


@pytest.mark.parametrize("requested", [None, "explicit-revision"])
def test_predict_uses_same_canonical_revision_for_loading_and_metadata(monkeypatch, tmp_path, requested):
    calls = fake_runtime(monkeypatch)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    spec = importlib.util.spec_from_file_location("memops_predict_revision_test", EXP / "predict.py")
    predict = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(predict)
    assert predict.CANONICAL_ADAPTER_REVISION == bridge.CANONICAL_ADAPTER_REVISION
    helper = SimpleNamespace(BASE_REVISION="base-revision", predict=lambda *args: [],
                             submission=lambda rows: rows, versions=lambda: {})
    monkeypatch.setattr(predict, "_load_lib", lambda *args: helper)
    inputs, output = tmp_path / "inputs.jsonl", tmp_path / "outputs.jsonl"
    inputs.write_text("")
    argv = ["predict.py", "--inputs", str(inputs), "--out", str(output), "--adapter", bridge.CANONICAL_ADAPTER]
    if requested: argv += ["--adapter-revision", requested]
    monkeypatch.setattr(sys, "argv", argv)
    predict.main()
    revision = requested or bridge.CANONICAL_ADAPTER_REVISION
    assert calls[0] == (bridge.CANONICAL_ADAPTER, {"revision": revision, "token": None})
    assert calls[1] == ("model_info", {"source": bridge.CANONICAL_ADAPTER, "revision": revision})
    side = json.loads(Path(str(output) + ".probs.json").read_text())
    assert side["model"]["adapter"]["revision"] == revision
