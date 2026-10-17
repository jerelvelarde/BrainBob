# BrainBob demo: presenter script

Generated from `src/story.json`. Product screens are actual browser captures of the scripted walkthrough. The separate backend segment summarizes recorded real model calls. Results are measured artifacts, not new runs.

## Three-minute showcase

### 0:00–0:10 · BrainBob

**Say:** When agents share memory, one stale fact can spread across the whole team. We built BrainBob to make shared memory current, scoped, and inspectable.

**Show:** Open /demo. Show the complete brain office before opening any panels. State that this is the scripted product walkthrough.

**On-screen disclosure:** ACTUAL APP · SCRIPTED WALKTHROUGH

### 0:10–0:24 · An approved fact has a source

**Say:** Here is Rusty Rod, our fictional company. Sales needs the Atlas pilot date. The organization memory says November sixth, with an approval source and revision one. That gives the next agent a fact it can trace.

**Show:** Scenario 1, An approved commitment. Open Evidence. Point to the approved commitment and atlas-date-r1. Click the record to inspect its source if presenting live.

**On-screen disclosure:** SCRIPTED FIXTURE · NO INFERENCE

### 0:24–0:36 · An estimate stays tentative

**Say:** Engineering now estimates November thirteenth. That estimate stays tentative and does not overwrite the approval. Private team context stays scoped, even when an executive asks.

**Show:** Scenario 2, An estimate is not a promise. Show Iris and the tentative conflict. Scenario 3 shows the Sales view still using November 6 without Engineering's private estimate.

**On-screen disclosure:** SCRIPTED FIXTURE · NO INFERENCE

### 0:36–0:50 · Approval creates a new revision

**Say:** An authorized approval changes the date. BrainBob creates revision two for November thirteenth and retires the superseded record, preserving its history. The reporting goal stays active. Correcting one fact should preserve other useful knowledge.

**Show:** Scenario 4, A correction with authority. Show Mara, the new date, and the retired predecessor. Scroll the evidence panel if necessary to compare revisions 1 and 2.

**On-screen disclosure:** SCRIPTED FIXTURE · NO INFERENCE

### 0:50–1:04 · A fresh agent gets current context

**Say:** Switch to Leo, a different Sales member. His fresh agent gets November thirteenth and the unchanged reporting goal, citing both records. Maya’s preferences and Engineering’s private estimate do not enter his session.

**Show:** Scenario 5, A fresh Sales agent gets it right. Point to Leo and the scripted answer citing atlas-date-r2 and atlas-goal-r1. Do not describe this authored answer as a live model response.

**On-screen disclosure:** SCRIPTED ANSWER · NO INFERENCE

### 1:04–1:16 · The session file shows what travels

**Say:** The desk opens Leo’s session file. His preferences, Sales guidance, and organization facts form one inspectable dossier. Records retain their sources and revisions. Download exports the file as Markdown.

**Show:** Stay on scenario 5. Close Evidence and open Session file. Inspect the three tiers and Download session .md. On the live route this is a snapshot of returned Ask records, not a complete model-input trace.

**On-screen disclosure:** SCRIPTED SESSION FILE

### 1:16–1:28 · Context is part of the conversation

**Say:** Click Bob for personalized chat, with starters drawn from accessible memories. The main route calls the Python backend through CopilotKit. This demo previews saved context without inference.

**Show:** Close the file and click Chat or the seated Bob. Show Leo's three memory-based prompts. Close and reopen to demonstrate conversation persistence for this member and step.

**On-screen disclosure:** SCRIPTED CHAT PREVIEW

### 1:28–1:44 · Missing evidence preserves uncertainty

**Say:** Older evidence cannot undo later approval. This audit samples ten of the latest fifty conversations but misses the approval. BrainBob reports insufficient evidence and retains the record. Missing evidence is not a reason to delete it.

**Show:** Show scenario 6 briefly, then scenario 7. Open Evidence. Point to seed 17, 10 of 50 conversations, Approval evidence covered: No, and the retain judgment. This is a demonstration seed, not a scored audit.

**On-screen disclosure:** SCRIPTED AUDIT · SELECTED SEED 17

### 1:44–1:56 · What we built

**Say:** We built the Python memory service and event-driven office. Scoped retrieval and maintenance preserve history. Crusoe serves the models. CopilotKit connects the conversation.

**Show:** Show the implementation summary. Do not call the store SQLite. Distinguish direct Crusoe calls from the unimplemented NemoClaw and Switchyard integrations.

**On-screen disclosure:** IMPLEMENTED CODE · INTEGRATION BOUNDARIES BELOW

### 1:56–2:14 · A recorded real-model correction loop

**Say:** A separate recorded run uses real models on synthetic data. Bad memory produces six P M. Removing it fixes the answer. After three harmful-task signals and fresh confirmation, review retires that claim and promotes a useful one. Another agent answers ten P M.

**Show:** Present the recorded October 17, 13:16 PDT trace. Show wrong answer m2, leave-one-out check, confirmed retirement m2, promotion m3, and new answer m1. Two harmful-task signals were seeded with real calls before the visible check. This legacy scenario is separate from Rusty Rod UI integration.

**On-screen disclosure:** RECORDED BACKEND RUN · SYNTHETIC INPUT · LEGACY MODE

### 2:14–2:32 · Maintenance keeps the right fact active

**Say:** Thirty held-out synthetic scenarios produced twelve of thirteen correct updates, versus zero for append-only memory. Zero of thirty-two valid memories were wrongly retired. Answers scored sixty-eight of seventy-six versus sixty-seven. The answer gain is not significant. The recent audit added no gain.

**Show:** Show update counts and the retention result first, then answer accuracy and its paired confidence interval. Explain that memory-state correctness and downstream answer correctness are different outcomes.

**On-screen disclosure:** MEASURED RESULT · 30 SYNTHETIC HELD-OUT SCENARIOS

### 2:32–2:48 · Less context, with an accuracy tradeoff

**Say:** On fifty LongMemEval questions, average answer context fell from about one hundred nine thousand tokens to twenty-seven hundred. Roughly forty times smaller. Correct answers fell from thirty-nine to thirty-five. This shows a context tradeoff, not accuracy parity.

**Show:** Show average context tokens and both correct/total counts together. This run tests extraction and retrieval, not the audit. Judge differs from the official protocol.

**On-screen disclosure:** MEASURED RESULT · LONGMEMEVAL 50-QUESTION SUBSET

### 2:48–3:00 · Shared memory, with a visible history

**Say:** BrainBob makes the memory behind an answer inspectable. We built the memory lifecycle and the office that explains it. Next: authentication, durable sessions, and stronger uncertainty handling.

**Show:** End on repository and next steps. NemoClaw and Switchyard remain unintegrated. The current UI-to-backend flow has fixture verification; do not claim a newly verified end-to-end Crusoe UI session.

**On-screen disclosure:** BRAINBOB · RECURSIVE AGENTS HACKATHON · OCT 17, 2026

## One-minute cut

### 0:00–0:07 · BrainBob

**Say:** One stale memory can mislead an entire agent team. BrainBob makes shared memory current and inspectable.

**Show:** Open /demo. Show the complete brain office before opening any panels. State that this is the scripted product walkthrough.

**On-screen disclosure:** ACTUAL APP · SCRIPTED WALKTHROUGH

### 0:07–0:15 · An approved fact has a source

**Say:** In this scripted walkthrough, Sales reads an approved November sixth commitment, with a source and revision.

**Show:** Scenario 1, An approved commitment. Open Evidence. Point to the approved commitment and atlas-date-r1. Click the record to inspect its source if presenting live.

**On-screen disclosure:** SCRIPTED FIXTURE · NO INFERENCE

### 0:15–0:24 · Approval creates a new revision

**Say:** A later approval creates November thirteenth as revision two. The old fact stays in history. Other valid knowledge survives.

**Show:** Scenario 4, A correction with authority. Show Mara, the new date, and the retired predecessor. Scroll the evidence panel if necessary to compare revisions 1 and 2.

**On-screen disclosure:** SCRIPTED FIXTURE · NO INFERENCE

### 0:24–0:33 · A fresh agent gets current context

**Say:** A fresh Sales agent gets the corrected date and the unchanged goal. Its session file keeps individual, team, and organization context inspectable.

**Show:** Scenario 5, A fresh Sales agent gets it right. Point to Leo and the scripted answer citing atlas-date-r2 and atlas-goal-r1. Do not describe this authored answer as a live model response.

**On-screen disclosure:** SCRIPTED ANSWER · NO INFERENCE

### 0:33–0:42 · A recorded real-model correction loop

**Say:** Separately, a recorded real-model run shows a harmful memory retired after fresh confirmation, followed by a corrected answer from another agent.

**Show:** Present the recorded October 17, 13:16 PDT trace. Show wrong answer m2, leave-one-out check, confirmed retirement m2, promotion m3, and new answer m1. Two harmful-task signals were seeded with real calls before the visible check. This legacy scenario is separate from Rusty Rod UI integration.

**On-screen disclosure:** RECORDED BACKEND RUN · SYNTHETIC INPUT · LEGACY MODE

### 0:42–0:53 · Maintenance keeps the right fact active

**Say:** Held-out synthetic tests show twelve of thirteen correct updates, versus zero for append-only memory. No valid memories were wrongly retired. Answer gains were not significant.

**Show:** Show update counts and the retention result first, then answer accuracy and its paired confidence interval. Explain that memory-state correctness and downstream answer correctness are different outcomes.

**On-screen disclosure:** MEASURED RESULT · 30 SYNTHETIC HELD-OUT SCENARIOS

### 0:53–1:00 · Shared memory, with a visible history

**Say:** We built the memory lifecycle and the office that explains it. BrainBob: shared memory, with a visible history.

**Show:** End on repository and next steps. NemoClaw and Switchyard remain unintegrated. The current UI-to-backend flow has fixture verification; do not claim a newly verified end-to-end Crusoe UI session.

**On-screen disclosure:** BRAINBOB · RECURSIVE AGENTS HACKATHON · OCT 17, 2026

## Live rehearsal and fallback

1. Run the frontend with `pnpm dev` from the repository root. Open `/demo`. It requires no backend key.
2. Follow the scenario selector and controls listed above. Allow each animation to settle. Keep the scripted label visible.
3. Use the rendered film if the browser or graphics stall. Say that it is a prepared presentation of captured screens.
4. Present the backend segment as a recorded run. Its legacy identities differ from the current Rusty Rod selector, so do not connect that seeded scenario to this UI and claim they are the same live session.
5. For a separate live backend demonstration, use `backend/demo/run_scenario.py` with an isolated backend and the documented environment. It makes paid inference calls. Do not reset another developer’s running state.
6. Do not equate source correctness with leave-one-out usefulness. The latter asks whether removing a memory changes a graded answer.
7. During Q&A, acknowledge unauthenticated demo member markers, pending durable server sessions, weak uncertainty answers, and unintegrated NemoClaw/Switchyard.

The WAV voice is a synthetic rehearsal guide. Replace each matching file under `public/audio/` with a human recording within its scene duration, then render without rerunning assets. Captions are sentence-level estimates, not forced-aligned transcripts.
