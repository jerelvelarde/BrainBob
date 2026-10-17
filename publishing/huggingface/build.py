"""Build the public Bob pilot from an immutable Git revision; never upload a tree."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def selected(path: str) -> bool:
    # Only source, fixtures, tests and documentation in these two packages.
    parts = Path(path).parts
    package = path.startswith(("bobbench/", "benchmarks/bob/"))
    excluded = {"results", ".cache", "__pycache__", ".pytest_cache"}
    return (package and not excluded.intersection(parts)
            and Path(path).suffix in {".py", ".json", ".jsonl", ".md"}
            or path == "docs/bob-benchmark-spec.md")


def build(out: Path, ref: str = "HEAD") -> dict:
    revision = git("rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()
    paths = git("ls-tree", "-r", "--name-only", revision).decode().splitlines()
    sources = {p: git("show", f"{revision}:{p}") for p in paths if selected(p)}
    # Read card from the same revision, so regenerating a release is reproducible.
    card = git("show", f"{revision}:publishing/huggingface/dataset-card.md").decode()
    out.mkdir(parents=True, exist_ok=False)

    def jsonl(name: str, rows: list[dict]) -> None:
        (out / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))

    worlds = []
    for path, content in sources.items():
        if path.startswith("bobbench/worlds/") and path.endswith(".json"):
            world = json.loads(content)
            worlds.append({
                "world_id": world["world_id"], "split": world["split"],
                "domain": world["domain"], "family": world["family"],
                "checkpoint_count": sum(i["type"] == "checkpoint" for i in world["timeline"]),
                "world_json": json.dumps(world, ensure_ascii=False),
            })
    jsonl("organizational-public-dev.jsonl", [w for w in worlds if w["split"] == "public-dev"])
    jsonl("organizational-pilot.jsonl", [w for w in worlds if w["split"] == "pilot"])
    for split in ("dev", "eval"):
        (out / f"memory-pairs-{split}.jsonl").write_bytes(sources[f"benchmarks/bob/{split}.jsonl"])
    structured = json.loads(sources["benchmarks/bob/worlds.json"])
    jsonl("structured-pilot.jsonl", [{
        "world_id": w["id"],
        "checkpoint_count": sum(s["type"] == "checkpoint" for s in w["steps"]),
        "world_json": json.dumps(w, ensure_ascii=False),
    } for w in structured])
    with zipfile.ZipFile(out / "bob-source.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, content in sorted(sources.items()):
            info = zipfile.ZipInfo(path, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    (out / "README.md").write_text(card.replace("{{SOURCE_REVISION}}", revision))
    digest = lambda data: hashlib.sha256(data).hexdigest()
    manifest = {
        "release": "public-pilot-v0.1", "source_revision": revision,
        "source_repository": "https://github.com/jerelvelarde/BrainBob",
        "counts": {"organizational_worlds": len(worlds),
                   "organizational_checkpoints": sum(w["checkpoint_count"] for w in worlds),
                   "memory_pairs_dev": len(sources["benchmarks/bob/dev.jsonl"].splitlines()),
                   "memory_pairs_eval": len(sources["benchmarks/bob/eval.jsonl"].splitlines()),
                   "structured_worlds": len(structured),
                   "structured_checkpoints": sum(s["type"] == "checkpoint" for w in structured for s in w["steps"])},
        "source_sha256": {p: digest(data) for p, data in sorted(sources.items())},
        "artifact_sha256": {p.name: digest(p.read_bytes()) for p in sorted(out.iterdir())},
    }
    (out / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    parser.add_argument("--ref", default="HEAD", help="Committed source revision")
    args = parser.parse_args()
    print(json.dumps(build(args.out, args.ref), indent=2))
