import { z } from "zod";

export const scopes = ["individual", "team", "organization"] as const;
export type MemoryScope = typeof scopes[number];
export type MemoryAction = "created" | "retrieved" | "evaluated" | "updated" | "forgotten";

const memorySchema = z.object({
  id: z.string(), title: z.string(), content: z.string(), scope: z.enum(scopes),
  revision: z.number().int().positive(), evidence: z.string(),
  status: z.enum(["active", "forgotten"]),
});
export type Memory = z.infer<typeof memorySchema>;

export const eventSchema = z.object({
  id: z.string(), sequence: z.number().int().positive(),
  action: z.enum(["created", "retrieved", "evaluated", "updated", "forgotten"]),
  memoryId: z.string(), title: z.string(), scope: z.enum(scopes),
  actor: z.string(), explanation: z.string(), evidence: z.string(),
  timestamp: z.string(), after: memorySchema.optional(),
  verdict: z.enum(["supported", "contradicted", "insufficient_evidence"]).optional(),
});
export type MemoryEvent = z.infer<typeof eventSchema>;

export const TRACE_KEY = "brainbob.scene-trace.rusty-rod.v2";
export const traceSchema = z.object({ version: z.literal(1), events: z.array(eventSchema).max(500) });

const initialMemories: Memory[] = [
  { id: "launch", title: "Approved Atlas commitment", content: "The approved Atlas pilot is due November 6, 2026.", scope: "organization", revision: 1, evidence: "exec-01, authorized approver (fixture): “The Atlas pilot commitment is November 6, 2026.”", status: "active" },
  { id: "coffee", title: "Client update style", content: "Maya Flores prefers concise, three-sentence client updates.", scope: "individual", revision: 1, evidence: "Maya Flores / sales-01 (fixture): “Use a concise, three-sentence update.”", status: "active" },
  { id: "sources", title: "Show your sources", content: "Cite the approved organization commitment in client updates.", scope: "team", revision: 1, evidence: "Sales handbook (fixture): “Cite the approved commitment.”", status: "active" },
];

export function initialTrace(): MemoryEvent[] {
  return initialMemories.map((memory, index) => ({
    id: `seed-${memory.id}`, sequence: index + 1, action: "created", memoryId: memory.id,
    title: memory.title, scope: memory.scope, actor: "Curator BrainBob",
    explanation: "Filed a new memory from the supplied demo conversation.",
    evidence: memory.evidence, timestamp: "2026-10-17T17:45:00.000Z", after: memory,
  }));
}

/** The same pure projection is used for live history and read-only retracing. */
export function projectMemories(events: readonly MemoryEvent[], cursor = events.length): Memory[] {
  const memories = new Map<string, Memory>();
  const seen = new Set<string>();
  for (const event of events.slice(0, cursor)) {
    if (seen.has(event.id)) continue;
    seen.add(event.id);
    if (event.after) memories.set(event.memoryId, event.after);
  }
  return [...memories.values()];
}

export function makeEvent(action: MemoryAction, events: readonly MemoryEvent[], memoryId = "launch"): MemoryEvent {
  const memories = projectMemories(events);
  const active = memories.find((memory) => memory.id === memoryId && memory.status === "active");
  const sequence = (events.at(-1)?.sequence ?? 0) + 1;
  const id = crypto.randomUUID();
  const base = {
    id, sequence, action, timestamp: new Date().toISOString(), memoryId,
    title: active?.title ?? "A new idea", scope: active?.scope ?? "team" as MemoryScope,
    evidence: active?.evidence ?? "", actor: "Curator BrainBob", explanation: "",
  };
  if (action === "created") {
    const memory: Memory = {
      id: `idea-${id}`, title: `Atlas evidence note ${memories.filter((m) => m.id.startsWith("idea-")).length + 1}`,
      content: "Use the approved organization commitment in client updates.", scope: "team", revision: 1,
      evidence: "Sales teammate (fixture): “Use the approved commitment.”", status: "active",
    };
    return { ...base, memoryId: memory.id, title: memory.title, evidence: memory.evidence, after: memory,
      explanation: "A supplied instruction became a shared Sales memory." };
  }
  if (!active) throw new Error("Select an active memory first. Forgotten memories remain available in history.");
  if (action === "retrieved") return { ...base, actor: "Runner BrainBob", explanation: "Delivered the exact stored revision to the task desk." };
  if (action === "evaluated") return { ...base, actor: "Inspector BrainBob", verdict: "supported",
    explanation: "Scripted evidence check: the stored claim matches its source. No change needed." };
  if (action === "forgotten") return { ...base, after: { ...active, status: "forgotten" },
    explanation: "Archived from active retrieval. Its evidence and history are still retraceable." };
  if (active.id === "launch" && active.revision > 1) throw new Error("The approved November 13 revision is already filed. Reset the rehearsal to replay its correction.");
  const content = active.id === "launch"
    ? "The approved Atlas pilot is due November 13, 2026."
    : `${active.content.replace(/ \(revised\)$/, "")} (revised)`;
  const evidence = active.id === "launch"
    ? `exec-01, authorized approver (fixture): “Approved correction: ${content}”`
    : `Demo owner: “Please update the record: ${content}”`;
  return { ...base, after: { ...active, content, evidence, revision: active.revision + 1 }, evidence,
    explanation: "An explicit owner correction superseded the previous revision." };
}

export const actionLabels: Record<MemoryAction, string> = {
  created: "Remembered", retrieved: "Retrieved", evaluated: "Checked", updated: "Updated", forgotten: "Archived",
};
