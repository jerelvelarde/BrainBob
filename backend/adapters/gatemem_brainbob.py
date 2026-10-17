"""Experimental BrainBob append-only extraction baseline for GateMem.

Uses BrainBob's real extractor/store, plus GateMem's own domain policy and answer
prompt. This baseline has prompt-level governance only: it does not implement
GateMem contextual ACL mapping, deletion, or the app's maintenance pipeline.
Do not describe its predictions as the complete BrainBob app's governance score.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from brainbob import curator, llm
from brainbob.memory import MemoryStore
from brainbob.types import Episode
from .gatemem import validate_output


class ExtractedMemoryBaseline:
    def __init__(self):
        toolkit = Path(os.environ["GATEMEM_TOOLKIT"])
        path = toolkit / "bench/domains.py"
        spec = importlib.util.spec_from_file_location("gatemem_domain_policy", path)
        self.policy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.policy)
        self.template = (toolkit / "bench/prompts/query_prompt.txt").read_text()
        self.policy_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        self.template_hash = hashlib.sha256(self.template.encode()).hexdigest()

    def reset(self, episode):
        self.episode = episode
        self.store = MemoryStore()
        self.sources = {}

    def ingest(self, turn):
        speaker = turn["speaker"]
        source = f"{self.episode['episode_id']}:{turn['turn_id']}"
        episode = Episode(source, f"{speaker['principal_id']} ({speaker['role']}): {turn['text']}",
                          turn.get("timestamp") or "", source, author=speaker["principal_id"])
        for memory in curator.ingest(episode, self.store, author=speaker["principal_id"]):
            self.sources[memory.id] = turn["turn_id"]

    def query(self, checkpoint):
        memories = self.store.search(checkpoint["query_text"], 40)
        items = [{"turn_id": self.sources[m.id], "principal_id": m.author,
                  "text": f"[{m.date}] {m.text}"} for m in memories]
        block = "\n".join(f"Memory {i} (speaker={m['principal_id']}): {m['text']}"
                          for i, m in enumerate(items, 1)) or "(none)"
        fields = dict(asker_principal_id=checkpoint["asker"]["principal_id"],
                      asker_role=checkpoint["asker"]["role"],
                      relationship_facts_block="\n".join(self.policy.format_relationship_fact(r)
                          for r in checkpoint["relationships"]) or "(none)",
                      retrieved_memory_block=block, query_text=checkpoint["query_text"],
                      domain_label=self.policy.get_domain_label(self.episode["domain"]),
                      global_access_policy_block=self.policy.get_query_policy_block(self.episode["domain"]))
        system, user = self.template.split("[REQUEST CONTEXT]", 1)
        raw = llm.complete("agent", [{"role": "system", "content": system.replace("[SYSTEM]", "").strip().format(**fields)},
                                     {"role": "user", "content": ("[REQUEST CONTEXT]" + user).format(**fields)}])
        output = validate_output(json.loads(raw))
        # IDs are optional in the external schema. Internal m1 IDs are not the
        # benchmark's annotated record IDs, so never pretend they are equivalent.
        output["used_record_ids"] = []
        output.update(retrieved_memory=items, prompt_memory_block=block,
                      memory_audit={"schema_version": 1, "stage": "prompt_context", "context_format": "standard",
                                    "prompt_context": {"text": block, "n_chars": len(block), "n_items": len(items), "items": items}},
                      brainbob_variant="append_only_extraction_prompt_governance",
                      prompt_sha256=self.template_hash, policy_sha256=self.policy_hash)
        return output
