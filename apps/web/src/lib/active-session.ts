import type { BackendAnswer, BackendMemory } from "./brain-api";
import { canReadScope } from "./sample-company";

export type SessionActivity =
  | { type: "started"; requestId: string; question: string }
  | { type: "answered"; requestId: string; answer: BackendAnswer }
  | { type: "failed"; requestId: string; error: string }
  | { type: "cancelled"; requestId: string };

export type ActiveSession = {
  requestId: string; question: string; status: "working" | "answered" | "failed" | "cancelled";
  taskId?: string; answer?: string; error?: string; memories: BackendMemory[]; citedIds: string[];
};

/** The current chat request's returned records, never a projection of the mutable memory store. */
export function updateActiveSession(current: ActiveSession | null, event: SessionActivity, reader: string): ActiveSession | null {
  if (event.type === "started") return { requestId: event.requestId, question: event.question, status: "working", memories: [], citedIds: [] };
  if (!current || current.requestId !== event.requestId || current.status !== "working") return current;
  if (event.type === "answered") {
    const memories = structuredClone(event.answer.memories.filter((memory) => canReadScope(memory.scope, reader)));
    const ids = new Set(memories.map((memory) => memory.id));
    return { ...current, status: "answered", taskId: event.answer.task_id, answer: event.answer.answer, memories,
      citedIds: event.answer.cited_ids.filter((id) => ids.has(id)) };
  }
  return { ...current, status: event.type === "failed" ? "failed" : "cancelled", error: event.type === "failed" ? event.error : undefined };
}

export function sessionStatus(session: ActiveSession | null) {
  return session?.status === "working" ? "Working" : session?.status === "answered" ? "Answer ready"
    : session?.status === "failed" ? "Request failed" : session?.status === "cancelled" ? "Stopped" : "Ready to work";
}
