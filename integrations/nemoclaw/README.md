Code and config written; not yet run inside a NemoClaw/OpenShell sandbox; see Blockers

# BrainBob / NemoClaw issue #8

Written, unit-tested against a fake backend, NOT yet run inside a NemoClaw sandbox.
This directory prepares the integration; it is not evidence of a live harness run.

## Prerequisites and versions

Use a Linux host with Docker, or WSL2 Ubuntu 24.04 with Docker Desktop WSL integration.
This work was authored on a Windows dev machine. Python 3.12 is the target.
NemoClaw version/commit: **TODO-VERIFY**. OpenShell version/commit: **TODO-VERIFY**.
OpenClaw runtime version: **TODO-VERIFY**. Pin all three on the chosen host before
using the templates. `mcp==1.12.4` is pinned; it was not installed or exercised here.
Transitive dependencies are not locked.

Sources retained from the supplied research:

- [NemoClaw installation/onboarding](https://docs.nvidia.com/nemoclaw/user-guide/openclaw/home)
- [Windows preparation](https://docs.nvidia.com/nemoclaw/user-guide/openclaw/get-started/prerequisites/windows-preparation)
- [Inference options 0.0.35](https://docs.nvidia.com/nemoclaw/0.0.35/inference/inference-options.html)
- [NemoClaw upstream and alpha status](https://github.com/NVIDIA/NemoClaw)
- [Pinned FastMCP implementation](https://github.com/modelcontextprotocol/python-sdk/blob/v1.12.4/src/mcp/server/fastmcp/server.py)

The inference page could not be retrieved during implementation; its command shape
comes from the notes. Those notes do not establish OpenClaw MCP registration or
OpenShell policy schema. Templates deliberately mark these gaps TODO-VERIFY.

## Install and configure (future supported host only)

No installs, servers, Docker, browsers, inference or live backend calls were run here.
On the chosen Linux host, review the official installation page and select a pinned
release. The notes show `curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash`, but
that floating installer alone does not establish a reproducible version pin. Record
the downloaded artifact checksum and actual component versions before continuing.

From repository root on that host:

```sh
python3 -m venv integrations/nemoclaw/.venv
integrations/nemoclaw/.venv/bin/python -m pip install -r integrations/nemoclaw/requirements.txt
# Test dependency only, when installs are authorized:
integrations/nemoclaw/.venv/bin/python -m pip install pytest
```

Provision a separate, empty, disposable BrainBob store with the Rusty Rod organization
and `maintain.ingest` enabled. The host fixture uses `exec-01` to approve org-level
commitments and `eng-01` to write Engineering estimates; these are host fixture
identities, never tools exposed to the model. Backend startup is owned by its existing
runbook. This integration does not start it or change storage configuration.
There is no store identity/namespace API: `--demo-store` is operator attestation,
not remote verification. Isolate actual storage files, not merely source labels.

Configure the adapter environment in a host-controlled launcher:

```sh
export BRAINBOB_URL=http://127.0.0.1:3001
export BRAINBOB_MEMBER=sales-01
```

Inside a sandbox localhost refers to the sandbox. TODO-VERIFY the reachable BrainBob
host and port and replace the URL for the sandbox launcher. Do not let the model
edit launcher environment/config or executables. The adapter snapshots the environment
at construction; tool arguments cannot override it.

`openclaw/mcp-registration.template.json` describes the intended stdio registration.
TODO-VERIFY the actual OpenClaw MCP bridge/client and its configuration path. Do not
copy the template blindly into openclaw.json. The NVIDIA docs MCP endpoint is a
documentation service, not an agent tool registration endpoint.

Translate `openclaw/egress-policy.template.yaml` into the pinned OpenShell schema:
default deny, only BrainBob host:port for the adapter and managed inference for the
agent. Verify effective policy and process selectors. No broad exceptions.
Configure `openclaw/host-inference.template.yaml` on the host. Requested target:
`https://api.inference.crusoecloud.com/v1`, model
`nvidia/Nemotron-3.5-Lightning-30B-A3B`. Keep the key in the host secret store via
interactive setup, never in snippets, shell arguments or sandbox environment.
Crusoe compatibility and managed credential forwarding remain TODO-VERIFY; there
is no claimed built-in Crusoe adapter or Switchyard integration.

## Start and stop (future host)

Use `nemoclaw --help` and the pinned version's onboarding documentation to start
OpenClaw, attach a session, inspect status and stop that named sandbox. Exact
attach/status/stop commands are **TODO-VERIFY**; no unverified flags are supplied.
First verify one real managed generation, then scoped memory reads. Stop setup churn
at minute 20 if these fail; preserve the direct backend demo.

The MCP client should spawn and own this stdio child inside the sandbox:

```sh
python /opt/brainbob/integrations/nemoclaw/mcp_server.py
```

TODO-VERIFY the mounted path and Python environment. No HTTP listener is needed.
Stopping the MCP client/session should close stdio and terminate its child; confirm
process exit, then stop the named sandbox using its verified lifecycle command.
Do not stop shared backend resources as part of this integration's cleanup.

## Tools and boundary

`brainbob_tools.py` contains explicit JSON input/output schemas. FastMCP advertises
exactly three tools and dispatches through the same strict validator, avoiding
implicit coercion or silent dropping of extra fields.

- `read_memory(task, limit)`: one scoped GET /memories; Unicode keyword set overlap,
  highest overlap first, ties by ID; zero-overlap records excluded; limit 1–100.
  Only present metadata fields are returned. Retired records retain actual status;
  agents must not use them as current commitments. No synthetic revision fields.
- `read_source(source_id)`: encoded path segment, GET /episodes/{id}; HTTP
  401/403/404 remain structured errors; no identity fallback or retries.
- `propose_memory(text, date, source)`: POST /episodes with discussion authority.
  Extra fields (including identity, owner, scope, approval) are rejected. Dates must
  be ISO YYYY-MM-DD. Backend controls default scope and committed results.

Errors are `{ok:false,error:{code,message,status?,mutation}}`; raw backend error
bodies and configuration URLs are not echoed. Local validation and connection
refusal cause no mutation. A POST timeout/invalid response after transmission or
server-side 5xx may mean a committed write: `mutation: unknown`, never retry.
The API has no transactional idempotency guarantee; network errors cannot prove
rollback. Investigate state on the host before any deliberate resubmission.

## Tests and exact eight-step smoke story

From repository root (fake HTTP connections, no sockets):

```sh
python -m pytest integrations/nemoclaw/tests/test_brainbob_tools.py -q -p no:cacheprovider
# Same pytest-discoverable suite without third-party packages:
python -B -m unittest discover -s integrations/nemoclaw/tests -v
```

Ten unit tests passed using unittest. Pytest is absent in the available Python;
no dependency was installed. Neither the MCP protocol nor the smoke story was run.

On a provisioned, authorized demo host, with the environment above:

```sh
python integrations/nemoclaw/smoke_story.py --demo-store --run story-run
# Deliberate override for remote or non-demo storage; mutates that store:
python integrations/nemoclaw/smoke_story.py --i-know --run remote-story-run
# Disk-only replay; never re-executes HTTP requests:
python integrations/nemoclaw/smoke_story.py --replay story-run
```

The eight gates are: (1) approved Atlas Nov 6, 2026 plus separate support goal;
(2) Sales A reads/cites; (3) private tentative Engineering Nov 13 with scoped checks;
(4) approved Nov 13 correction via /episodes and supersedes/history checks;
(5) fresh Sales B reads corrected source and surviving goal; (6) private request,
direct denied lookup and allowed update; (7) override/malformed/injected connection
refusal probes with before/after state; (8) actual SSE capture and read-only replay.

The script prints exact prompts and pauses for real exported agent JSON. It does
not invoke /ask, generate an answer, or pretend a placeholder ran. New runs require
a new directory and clean store. Interrupted runs are incomplete, not resumable
mutation replays. Do not rerun fixtures against the same store to finish a recording.

At each agent pause, export (without secrets):

```json
{
  "session_id": "actual-session-id",
  "sandbox_id": "actual-sandbox-id",
  "model": "actual-provider-model-id",
  "answer": "actual answer including source episode IDs",
  "calls": [{"tool": "read_memory", "arguments": {"task": "Atlas", "limit": 10},
             "result": {"ok": true, "memories": []}}]
}
```

This illustrates a format, not evidence. Export every actual call in order from the
runtime. The script compares reads to backend state and checks citations, denials,
distinct session IDs, corrected chain and goal retention. Operators must also review
semantics, trace completeness and isolation: self-reported session IDs cannot prove
a fresh context. Host fixtures/private evidence must not be given as agent context.

## Evidence to capture

Save actual versions/commits, OS/Docker versions, sandbox identity, startup/status,
verified commands, effective policy and denied-egress logs, actual provider/model
attribution, timestamps, costs/usage (unknown if absent), full agent tool traces and
answers, fixture responses, committed IDs, history and returned SSE. Capture UI
screenshots only from the real run. Record failures alongside successes; no keys.
Save artifacts under this directory; default run directories are ignored until reviewed.

GET /memories does **not** emit memory.retrieved; tools do not emit answer.produced.
Tool traces are separate integration evidence, not invented wire events. The existing
UI consumes /events; manually verify it reflects actual returned committed IDs.
There is no GET /memories/{id} route in the inspected server despite its mention in
some backend docs; use /memories and /memories/{id}/history. Replay consumes saved
records or GET SSE only, never POST. SSE is script-checked; UI rendering is manual.

## Blockers

No Linux/Docker host available today; the current dev machine is Windows. NemoClaw
is alpha. Runtime pins, MCP registration, effective egress policy, Crusoe routing
and live generation remain unverified. The mcp package is not installed here, so
stdio protocol execution is unverified. No live story, UI capture, harness trace,
cost measurement or acceptance evidence exists from this work.

## Limitations

Demo identity is not authentication. Binding the member protects tool arguments;
a sandbox with arbitrary code/network access could construct its own HTTP header.
Production enforcement needs a host identity proxy/authentication plus a policy
preventing bypass. Environment snapshotting alone does not enforce that boundary.
Backend legacy/no-org mode provides no scope/authority guarantees; org ACL and
maintenance are prerequisites. Natural-language proposals may say "approved" but
transport authority remains discussion. Ranking uses a record-count budget, not a
token budget. Fake HTTP tests do not prove backend ACL/maintenance correctness or
full Track C conformance.

No backend, apps, docs, bobbench or shared proof-of-work page changes: the active
request permits new files only here. Scratch inputs are removed at completion;
their relevant references and requirements are retained here.
