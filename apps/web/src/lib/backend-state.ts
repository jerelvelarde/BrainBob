import { canRead, sceneScope, type BackendEvent, type BackendMemory, type StoredEvent } from "./brain-api";
import type { SceneCue, SceneAction } from "./scene-animation";

export type BackendState = { seq: number; replaying: boolean; memories: Record<string, BackendMemory>; events: StoredEvent[] };
export const emptyBackendState = (): BackendState => ({ seq: 0, replaying: true, memories: {}, events: [] });

export function projectBackendEvent(memories: Record<string, BackendMemory>, event: StoredEvent) {
  if (event.type === "memory.added") return { ...memories, [event.memory.id]: event.memory };
  if (!("memory_id" in event) || !memories[event.memory_id]) return memories;
  const memory = memories[event.memory_id];
  let change: Partial<BackendMemory> | undefined;
  switch (event.type) {
    case "memory.promoted": change = { status: "promoted", reason: event.reason }; break;
    case "memory.retired": change = { status: "retired", flagged: false, reason: event.reason }; break;
    case "memory.flagged": change = { flagged: true, reason: event.reason }; break;
    case "memory.locked": change = { status: "locked", owner: event.owner, reason: `locked by ${event.owner}` }; break;
    case "memory.resolved": change = { flagged: false }; break;
  }
  return change ? { ...memories, [memory.id]: { ...memory, ...change } } : memories;
}

/** Replay is state-only. Sequence guards also cover duplicate reconnect deliveries. */
export function acceptBackendEvent(state: BackendState, event: BackendEvent): { state: BackendState; animate: boolean } {
  if (event.type === "replay.done") {
    if (event.seq < state.seq) throw new Error("Backend history was reset. Reload to synchronize the new history.");
    return { state: { ...state, seq: event.seq, replaying: false }, animate: false };
  }
  if (event.seq <= state.seq) return { state, animate: false };
  return { state: { ...state, seq: event.seq, memories: projectBackendEvent(state.memories, event), events: [...state.events, event] }, animate: !state.replaying };
}

export function memoriesAt(events: StoredEvent[], seq: number) {
  return events.reduce<Record<string, BackendMemory>>((map, event) => event.seq <= seq ? projectBackendEvent(map, event) : map, {});
}

export function eventMemoryIds(event: StoredEvent, events: StoredEvent[] = []): string[] {
  if (event.type === "memory.added") return [event.memory.id];
  if (event.type === "memory.conflict") return [event.new_id, event.old_id];
  if ("memory_id" in event) return [event.memory_id, ...("new_id" in event && event.new_id ? [event.new_id] : [])];
  if ("memory_ids" in event) return event.memory_ids;
  if (event.type === "answer.produced") return event.cited_ids;
  if (event.type === "evaluation.finished") {
    const started = events.findLast((e) => e.type === "evaluation.started" && e.task_id === event.task_id);
    return started?.type === "evaluation.started" ? started.memory_ids : [];
  }
  return [];
}

export function eventDescription(event: StoredEvent) {
  switch (event.type) {
    case "memory.added": return event.memory.supersedes ? "Correction filed as a new memory" : "New memory filed";
    case "memory.retrieved": return `Retrieved ${event.memory_ids.length} memories`;
    case "evaluation.started": return `Checks the cited memories · ${event.memory_ids.length} cited`;
    case "memory.checked": return event.reason === "confirm failed" ? "Fresh confirmation failed · memory kept" : event.flipped ? event.with_correct ? "Helpful: removing it made the answer wrong" : "Harmful: removing it made the answer right" : "No correctness flip";
    case "evaluation.finished": return `Checked ${event.checked}, ${event.flips} flips`;
    case "memory.retired": return event.confirmed === true ? "Retired · fresh confirmation passed" : event.reason.startsWith("superseded by ") ? "Prior memory superseded" : "Retired";
    case "memory.flagged": return "Flagged for its owner · memory kept";
    case "memory.locked": return `Locked by ${event.owner}`;
    case "memory.resolved": return `Owner chose ${event.action}`;
    case "memory.promoted": return "Promoted with evidence";
    case "memory.corrected": return "Correction linked to its predecessor";
    case "answer.produced": return "Answer delivered with citations";
    case "evidence.recorded": return "Evidence recorded";
    case "episode.ingested": return `Conversation processed · ${event.n_memories} memories`;
    case "memory.rejected": return `Not stored: ${event.reason}`;
    case "memory.conflict": return "Tentative conflict · existing memory retained";
    case "audit.started": return `Correctness audit · ${event.sampled_ids.length} of ${event.eligible_ids.length} conversations`;
    case "audit.checked": return `Source correctness: ${event.verdict} · ${event.reason}`;
    case "audit.finished": return `Correctness audit complete · ${event.checked} checks, ${event.insufficient} insufficient`;
  }
}

/** Scene cues are derived receipts. They never mutate the store or call the API. */
export function cuesForEvent(event: StoredEvent, state: BackendState, reader: string): SceneCue[] {
  const ids = eventMemoryIds(event, state.events);
  const records = ids.flatMap((id) => {
    const memory = state.memories[id];
    const scope = memory && sceneScope(memory.scope);
    return memory && scope && canRead(memory.scope, reader) ? [{ id, scope }] : [];
  });
  if (!records.length) return []; // Unscoped global events cannot be attributed to this reader.
  let action: SceneAction;
  switch (event.type) {
    case "memory.added": action = event.memory.supersedes ? "updated" : "created"; break;
    case "memory.retrieved": action = "retrieved"; break;
    case "answer.produced": action = "answered"; break;
    case "evaluation.started": case "memory.checked": case "evaluation.finished": case "audit.checked": action = "evaluated"; break;
    case "memory.promoted": action = "promoted"; break;
    case "memory.retired": if (event.reason.startsWith("superseded by ")) return []; action = "forgotten"; break;
    case "memory.flagged": case "memory.conflict": action = "flagged"; break;
    case "memory.locked": action = "locked"; break;
    case "memory.resolved": if (event.action !== "keep") return []; action = "resolved"; break;
    default: return []; // Evidence and correction bookkeeping must not duplicate check/rewrite scenes.
  }
  const groups = action === "retrieved" ? [...new Set(records.map((r) => r.scope))] : [records[0].scope];
  return groups.map((scope) => ({ id: `backend-${event.seq}-${scope}`, action, scope, source: "backend", title: eventDescription(event),
    seconds: action === "forgotten" ? 10 : action === "evaluated" ? 3 : 4,
    records: action === "retrieved" ? records.filter((r) => r.scope === scope) : records,
    noticeLabel: event.type === "memory.conflict" ? "TENTATIVE · REVIEW" : undefined,
    evaluationLabel: event.type === "audit.checked" ? `SOURCE · ${event.verdict.toUpperCase()}` : undefined,
    evaluation: event.type === "evaluation.started" ? { phase: "start" as const }
      : event.type === "memory.checked" ? { phase: "check" as const, verdict: event.reason === "confirm failed" ? "unconfirmed" as const : !event.flipped ? "unchanged" as const : event.with_correct ? "helpful" as const : "harmful" as const }
      : event.type === "evaluation.finished" ? { phase: "finish" as const }
      : event.type === "audit.checked" ? { phase: "start" as const } : undefined,
  }));
}
