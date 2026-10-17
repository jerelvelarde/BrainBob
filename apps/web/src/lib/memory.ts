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

export const actionLabels: Record<MemoryAction, string> = {
  created: "Remembered", retrieved: "Retrieved", evaluated: "Checked", updated: "Updated", forgotten: "Archived",
};
