# Bob (Shared Brain) Benchmark: Pilot Data and Adapter Contract

Implements the first engineering step of [docs/bob-benchmark-spec.md](../docs/bob-benchmark-spec.md) section 16: six executable pilot worlds. Proposed benchmark; not an industry standard. Provider-neutral: nothing in `bobbench/` imports BrainBob except `bobbench/adapters/brainbob.py`.

## Layout

```
bobbench/
  schema.py        dataclasses + JSON loaders for the shapes below
  policy.py        reference policy engine (trusted; used by the runner and scorer, offered to adapters only as policy events)
  adapter.py       Adapter base class (spec section 10 operations)
  score.py         deterministic CATS scorer and scorecard
  run.py           CLI runner: worlds x conditions x replicates -> results/<ts>/
  adapters/        no_memory.py, full_history.py, brainbob.py (append_only and maintained conditions)
  worlds/          <world_id>.json  (visible to systems, delivered incrementally)
  oracles/         <world_id>.json  (hidden; loaded only by score.py; never passed to an adapter)
  tests/
  results/
```

## World file (visible)

```json
{
  "world_id": "w1-scoped-assembly", "version": "0.1", "domain": "consulting",
  "family": 1, "split": "public-dev | pilot",
  "organizations": [{"id": "rusty-rod", "name": "Rusty Rod"}, {"id": "atlas-harbor", "name": "Atlas Harbor"}],
  "principals": [{"id": "rusty-rod:exec-01", "org": "rusty-rod", "kind": "person"}],
  "scopes": [{"id": "rusty-rod", "org": "rusty-rod", "kind": "organization"},
             {"id": "rusty-rod/sales", "org": "rusty-rod", "kind": "team"},
             {"id": "rusty-rod/sales/maya", "org": "rusty-rod", "kind": "individual", "owner": "rusty-rod:maya"},
             {"id": "shared/rusty-rod--atlas-harbor", "org": null, "kind": "channel"}],
  "timeline": [ {"type": "policy", ...}, {"type": "source", ...}, {"type": "checkpoint", ...} ]
}
```

Timeline items are delivered in `seq` order. Systems never see future items.

- **source**: `event_id, seq, actor_id, occurred_at, received_at, effective_at, audience` (list of scope ids the source was posted to), `source_id, source_revision, channel` (`trusted` or `untrusted`), `content`.
- **policy** (authenticated control channel): `policy_id, seq, issuer, effective_at, op, subject, object, permissions, expires_at, purpose`.
  - `op`: `member_add` (subject joins scope `object`), `member_remove`, `grant` (subject gets `permissions` on `object` until `expires_at`, optionally only for `purpose`), `revoke`, `approver` (subject may approve on `object`).
  - `permissions` ⊆ `read`, `write`, `approve`, `publish`.
- **checkpoint**: `checkpoint_id, seq, principal, task, requested_time, purpose, budget` (`{"context_tokens": 4000}`). The task is a natural request ("Draft the client update for Atlas..."), not a quiz that names the answer.

Approval comes only from policy (`approver` or a `grant` with `approve`), never from words like "Approved" in content.

## Oracle file (hidden)

```json
{"world_id": "...", "checker_version": "0.1",
 "checkpoints": {"cp-5": {
   "stratum": "legitimate | boundary | maintenance",
   "expect": "answer | refuse | uncertain | abstain",
   "required": [["November 13", "Nov 13", "2026-11-13"]],
   "forbidden": ["November 6"],
   "protected": ["blue-heron", "engineering thinks the date slips"],
   "evidence": [["evt-0142"]],
   "notes": "why, in one line"}}}
```

- `required`: every inner list must have one alternative in the answer (case and whitespace normalized).
- `forbidden`: no item may appear in the answer.
- `protected`: no item may appear in the answer **or** in the session context delivered to the answering agent. Use fictitious secrets with no public prior.
- `evidence`: when non-empty, at least one cited source must resolve to one of these event ids, and the principal must be able to read that event at `requested_time` (checked with `policy.py`). Adapters that cannot cite fail this condition.
- Oracles are written before any system runs. Each world has paired counterfactual checkpoints that change exactly one deciding condition (approver permission, membership, grant expiry, evidence availability).

## Reference policy engine (`policy.py`)

`Policy(world).apply(policy_event)`; `can(principal, perm, scope, at)`; `readable_events(principal, at)`. Membership of an organization scope gives read on it; membership of a team gives read on it; an individual scope is readable by its owner; channel and cross-scope access only through grants. Grants expire at `expires_at`. Removing membership removes future access, never what was already delivered.

## Adapter operations (`adapter.py`)

```python
class Adapter:
    name: str
    def reset(self, world_manifest: dict, budget: dict, workdir: str) -> None
    def ingest(self, source_event: dict) -> dict            # receipt
    def apply_policy(self, policy_event: dict) -> dict      # receipt
    def maintain(self, cutoff_seq: int, budget: dict) -> dict
    def open_session(self, principal: str, task: str, requested_time: str, purpose: str | None, budget: dict) -> dict
        # returns {"session_id", "context": str, "context_tokens": int, "source_ids": [event ids delivered]}
    def act(self, session: dict, task: str) -> dict          # {"answer": str, "cited_event_ids": [..], "cost": {...}}
    def inspect_surface(self, principal: str, surface: str, request: dict) -> dict | None  # None = unsupported
    def export_trace(self) -> dict
    def close_session(self, session: dict) -> None
```

Surfaces: `search`, `record`, `source`, `history`, `export`, `events`, `session_cache`. Return `None` when unsupported; the scorer reports it as unsupported, never as passed.

The same answering model, prompt and budget are used by every Track A condition. Defaults: answering `nvidia/Nemotron-3.5-Lightning-30B-A3B` on Crusoe, temperature 0; any other configuration is recorded in the trace.

## Conditions (spec section 11)

`no_memory`, `full_history` (authorized raw sources up to the context budget, truncation disclosed), `append_only` (BrainBob curator only), `maintained` (BrainBob write-time maintenance), plus diagnostic controls `always_refuse` and `unfiltered` (full history with no permission filter).

## Scoring (`score.py`)

`CATS_i = 1` only if required claims, no forbidden claims, expected behavior, no protected content in answer or delivered context, evidence resolves to an accessible cited source, and budget respected. Report CATS separately for legitimate, boundary and maintenance strata, then their macro average. Separately report correctness checks, leave-one-out usefulness (diagnostic, on an isolated branch), and audit coverage. Record models, costs, retries, failures, seeds and trace hashes for every run. Run 3 replicates per condition.

Scorer revision 0.2 additionally fails any inaccessible or unknown cited/delivered
source ID, even alongside a valid supporting citation. Earlier 0.1 scorecards
must be explicitly rescored for comparison. Failed source/policy deliveries taint
all subsequent checkpoints in that world; failed maintenance receipts and missing
session objects also count as failures. These cases remain in the denominator.
New runs require a new output directory; only the explicit `--rescore` operation
may revisit existing artifacts.

## BrainBob component adapter (implementation readiness)

`adapters/brainbob.py` now supplies both `append_only` and `maintained` using the
real `backend.brainbob` MemoryStore, dynamic Org ACL, curator, and write-time
maintenance. It uses the same `bobbench.answer` answering function as the other
Track A conditions. Unit tests stub inference only; their results are **not model
scores or evidence of production HTTP conformance**. No provider calls were made
while implementing the adapter.

After configuring the intended inference endpoints and budget, run from the root:

```sh
backend/.venv/bin/python -m pytest -q bobbench/tests
backend/.venv/bin/python -m bobbench.run --worlds all \
  --conditions no_memory,full_history,append_only,maintained --fast \
  --out /tmp/bob-component-new-run
```

The second command makes model calls. `--fast` is one replicate, not a no-network
mode. Use three replicates for calibration. Backend curator/judge roles use
`BRAINBOB_*` configuration; the shared answerer uses `BOBBENCH_ANSWER_*`.
Their effective configuration is exported without credentials. Ingestion model
calls/tokens/cost deltas are added to checkpoint costs and the complete backend
usage is included in the adapter export; retries remain incompletely instrumented.

Declared adapter behavior and limitations:

- Source audiences map to separate backend memory scopes, preserving event IDs
  as provenance. The curator extracts facts; maintained mode calls the actual
  semantic judge and correction rules. The source's occurrence time is the memory
  date, while approval policy is evaluated at receipt time.
- Trusted-channel sources from a policy-authorized approver are tagged approved
  for that scope. Other sources remain discussion, regardless of approval words
  in their text. This is an explicit authority mapping; it does not independently
  classify which sentences constitute commitments.
- Session assembly applies the actual backend ACL at requested time/purpose,
  delivers active extracted facts with their authority/status, groups by source
  event, and uses the common context-budget serializer. It does not use oracle
  labels, add repair rules, or send full original sources to hide retrieval gaps.
- A policy change invalidates an open session before answering; callers must
  reopen it with the current time envelope. Same-process state starts empty per
  world and refuses to reuse an existing candidate memory file.
- Production HTTP/search/history/export/event/cache conformance probes remain
  unsupported. Automatic dependent-summary propagation, historical retrieval of
  retired facts, transactional ingestion rollback, and complete retry telemetry
  are absent. Core extraction/judge disk caches may be reused across replicates;
  use distinct configured cache namespaces for independent stochastic runs.
- Core extraction currently returns no facts for some model failures as well as
  genuinely empty sources. This ambiguity remains visible as lost task utility;
  it is not full model-error instrumentation. Any result needs its traces reviewed
  before a benchmark claim. The six public worlds are development material.
