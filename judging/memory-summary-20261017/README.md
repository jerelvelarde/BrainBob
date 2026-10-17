# Memory summary and files tabs

Implementation: `62c05992da468735eef0da7cfbbf722a19290a9f`, committed October 17, 2026 at 4:16:05 PM PDT.

The full-screen chat Memory panel defaults to Summary. A dedicated, read-only `summarizer` role uses NVIDIA Nemotron Nano 30B-A3B on Crusoe. Memory files preserves the saved records, reply citations, and source/history inspection. The backend filters by the selected demo identity and excludes retired records before inference. Model and endpoint are configurable; existing member headers remain demo identity rather than authentication.

## Verification

- `pnpm typecheck`: passed.
- `pnpm test`: 41 tests passed in 8 files.
- `backend/.venv/bin/python -m pytest backend/tests/test_summary.py backend/tests/test_server.py backend/tests/test_llm.py backend/tests/test_acl.py -q`: 28 passed.
- A fresh direct Crusoe smoke call returned a nonempty summary using `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`: 226 prompt tokens, 87 completion tokens, zero cached calls. This used the single synthetic preference “Leo Park prefers bullet-point agendas and explicit follow-up owners.”
- `live-response.json` was collected through the running Next proxy before the implementation commit, with the same implementation source: 24 accessible records summarized for sales-02. Subsequent browser captures use sales-01 (Maya Flores).
- `verification.json` records successful desktop/mobile checks after the implementation commit: default tab, files, Arrow/Home/End keys, source inspector, no horizontal overflow at 390px, and no browser page errors.
- Error recovery deliberately intercepted only the summary request with HTTP 503. Files stayed usable; retry then used the actual local backend. Other browser data was live. Summaries can reuse the existing content-based inference cache.

## Capture provenance and limits

Screenshots were taken from the running local app after the implementation commit; exact capture timestamps are in `verification.json`. Unrelated demo/changelog edits and other agents’ untracked evidence existed in the shared checkout. The memory-summary source matched the implementation commit. Screenshots demonstrate appearance; the provider smoke call and actual endpoint response establish inference connectivity, not summary accuracy. No new factual-accuracy benchmark was performed. The input limit is 48,000 serialized record characters, with partial coverage disclosed. Summary generation cannot mutate saved memory.

## PR provenance

The feature was copied onto current `origin/main` as `20f1b376bd371cd35f023a5951c3154128cd3e86` for the PR. The memory-summary implementation files are identical to original local commit `62c05992da468735eef0da7cfbbf722a19290a9f`; unrelated local commits were excluded. Screenshots and the original verification record retain their original build identifier and capture times. This is not a new browser capture or model-quality evaluation.

PR branch verification: TypeScript, all 41 frontend tests, and the 28 targeted backend tests passed again. Checked 61 local documentation links and all changelog anchors, and confirmed all cherry-picked implementation files match the original capture build.
