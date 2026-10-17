# BrainBob — Demo Runbook

Use this as a rehearsal outline. Demonstrate only features that work in the submitted build and clearly identify work created during the hackathon.

## Before Judging

- [ ] Confirm the submitted commit and the exact features being demonstrated.
- [ ] Fill in the [evidence sheet](evidence.md), including contributions and measured results.
- [ ] Verify repository, demo, and video links are accessible.
- [ ] Prepare an isolated fixture and a fresh agent conversation.
- [ ] Check the actual harness, routing, and inference connections used by the demo.
- [ ] Label scripted actions and recorded replay visibly.
- [ ] Rehearse in three minutes and prepare one to two minutes of Q&A.

## Three-Minute Live Demo

| Time | Action | Point to establish |
| --- | --- | --- |
| 0:00–0:20 | Introduce Shared Brain and the brain office. | New agents repeatedly pay for context and can act on stale knowledge. |
| 0:20–0:50 | Agent A records a launch date; show its source and team scope. | Useful knowledge is stored with evidence and a revision. |
| 0:50–1:20 | Start a fresh Agent B and ask it to use that knowledge. | Shared memory survives the agent handoff. |
| 1:20–1:55 | Introduce an owner correction; show the check and committed update, then ask again. | The next answer uses the current fact. Identify a targeted correction separately from a random audit. |
| 1:55–2:25 | Click the memory and retrace its source, evaluation, revisions, and use. | The animation corresponds to inspectable events; history is preserved. |
| 2:25–2:50 | Show paired task results and context/total-token measurements. | Memory improves output quality and reduces repeated context. Present only measured results. |
| 2:50–3:00 | State what the team built and what remains planned. | Original contributions and implementation limits are clear. |

If live inference fails, show the failure and explicitly switch to a recorded trace. Do not describe replay or a scripted scene as a successful live agent run. If a planned step is not implemented, omit its success claim and explain the current boundary.

## One-Minute Submission Video

| Time | Content |
| --- | --- |
| 0:00–0:10 | Shared Brain problem and the team's original contribution. |
| 0:10–0:25 | A fresh agent retrieves another agent's shared knowledge. |
| 0:25–0:40 | A correction updates memory and changes the next answer. |
| 0:40–0:52 | Retrace the change in the brain visualization and evidence inspector. |
| 0:52–1:00 | Measured result, repository, and demo destination. |

Adapt the video to the working submission; keep preview/replay labels visible.

## Likely Q&A

- What is shared between agents, and how are individual/team/organization scopes enforced?
- How do you handle two agents updating the same fact?
- What evidence can justify an update or forgetting a memory?
- What happens when a random audit misses the correction-bearing conversation?
- How do you measure quality independently of the memory evaluator's own judgment?
- How much do extraction, maintenance, routing, and answering cost together?
- Which calls actually use NemoClaw, Switchyard, Crusoe, and NVIDIA models?
- Which parts were built during the event, and which libraries or assets were reused?
