"""Print non-secret model handoff configuration without making inference calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from brainbob import llm


def report():
    root = Path(__file__).resolve().parent
    key_file_present = Path("~/.config/crusoe/api.key").expanduser().is_file()
    roles = llm.configuration()
    for role, cfg in roles.items():
        cfg["credential_configured"] = bool(os.environ.get(f"BRAINBOB_{role.upper()}_API_KEY") or
                                            os.environ.get("BRAINBOB_API_KEY") or key_file_present)
        cfg["price_status"] = "configured estimate" if cfg["model"] in llm.PRICE and cfg["base_url"] == llm.DEFAULT_BASE_URL else "unknown; legacy cost totals are not valid for this route"
    return {"mode": "offline_configuration_only", "endpoint_reachable": "not tested",
            "model_available": "not tested", "roles": roles,
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "prompt_file_sha256": {p: hashlib.sha256((root / "brainbob" / p).read_bytes()).hexdigest()
                                   for p in ("agent.py", "curator.py", "maintain.py", "audit.py")},
            "handoff_required": ["immutable checkpoint ID/hash and base model", "role being replaced",
                                 "OpenAI-compatible endpoint and credential configuration",
                                 "training data and benchmark contamination disclosure",
                                 "context limit, chat template and supported request parameters"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(report(), indent=2))
