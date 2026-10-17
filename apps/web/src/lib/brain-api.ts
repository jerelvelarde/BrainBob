import { z } from "zod";
import { canReadScope, companyScope, demoScopes, memberId } from "./sample-company";

// Keep browser requests on the UI origin; Next forwards them to BRAINBOB_API_URL.
// An explicit public URL remains available for deployments with direct API access.
export const BACKEND_URL = (process.env.NEXT_PUBLIC_BRAINBOB_API_URL ?? "/api/brainbob").replace(/\/$/, "");
export const readers = demoScopes;
export const canRead = canReadScope;
export function sceneScope(path: string) {
  return companyScope(path)?.scope;
}
export function scopeLabel(path: string) { return companyScope(path)?.label ?? path; }

export const backendMemorySchema = z.object({
  id: z.string(), text: z.string(), author: z.string(), origin: z.string(), date: z.string(),
  status: z.enum(["trial", "promoted", "retired", "locked", "tentative"]), scope: z.string(),
  reason: z.string().default(""), flagged: z.boolean().default(false),
  authority: z.enum(["approved", "tentative", "discussion"]).default("discussion"),
  model: z.string().nullable().default(null), conflicts_with: z.array(z.string()).default([]),
  supersedes: z.string().nullable().default(null), owner: z.string().nullable().default(null),
});
export type BackendMemory = z.infer<typeof backendMemorySchema>;
const base = { seq: z.number().int().nonnegative(), ts: z.number(), model: z.string().nullable().optional() };
const memoryId = { memory_id: z.string() };
const taskId = { task_id: z.string() };
export const backendEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("replay.done"), seq: base.seq }),
  z.object({ ...base, type: z.literal("episode.ingested"), episode_id: z.string(), source: z.string(), n_memories: z.number() }),
  z.object({ ...base, type: z.literal("memory.added"), memory: backendMemorySchema }),
  z.object({ ...base, type: z.literal("memory.rejected"), text: z.string(), reason: z.string() }),
  z.object({ ...base, ...taskId, type: z.literal("memory.retrieved"), memory_ids: z.array(z.string()) }),
  z.object({ ...base, ...taskId, type: z.literal("answer.produced"), answer: z.string(), cited_ids: z.array(z.string()) }),
  z.object({ ...base, ...memoryId, ...taskId, type: z.literal("evidence.recorded"), author: z.string(), shown: z.boolean(), correct: z.boolean() }),
  z.object({ ...base, ...taskId, type: z.literal("evaluation.started"), memory_ids: z.array(z.string()) }),
  z.object({ ...base, ...memoryId, type: z.literal("memory.checked"), task_id: z.string().nullable(), with_correct: z.boolean(), without_correct: z.boolean(), flipped: z.boolean(), reason: z.string().optional() }),
  z.object({ ...base, ...taskId, type: z.literal("evaluation.finished"), checked: z.number(), flips: z.number() }),
  z.object({ ...base, ...memoryId, type: z.literal("memory.promoted"), reason: z.string() }),
  z.object({ ...base, ...memoryId, type: z.literal("memory.retired"), reason: z.string(), task_ids: z.array(z.string()).default([]), confirmed: z.boolean().optional(), author: z.string().optional() }),
  z.object({ ...base, ...memoryId, type: z.literal("memory.flagged"), reason: z.string() }),
  z.object({ ...base, ...memoryId, type: z.literal("memory.locked"), owner: z.string() }),
  z.object({ ...base, ...memoryId, type: z.literal("memory.resolved"), owner: z.string(), action: z.enum(["keep", "retire", "correct"]), new_id: z.string().nullable() }),
  z.object({ ...base, ...memoryId, type: z.literal("memory.corrected"), new_id: z.string(), author: z.string() }),
  z.object({ ...base, type: z.literal("memory.conflict"), new_id: z.string(), old_id: z.string(), reason: z.string() }),
  z.object({ ...base, type: z.literal("audit.started"), seed: z.union([z.number(), z.string()]), eligible_ids: z.array(z.string()), sampled_ids: z.array(z.string()) }),
  z.object({ ...base, ...memoryId, type: z.literal("audit.checked"), episode_id: z.string(), verdict: z.enum(["supported", "contradicted", "insufficient"]), reason: z.string() }),
  z.object({ ...base, type: z.literal("audit.finished"), checked: z.number(), contradicted: z.number(), supported: z.number(), insufficient: z.number() }),
]);
export type BackendEvent = z.infer<typeof backendEventSchema>;
export type StoredEvent = Exclude<BackendEvent, { type: "replay.done" }>;
export const episodeSchema = z.object({ id: z.string(), text: z.string(), date: z.string(), source: z.string(), scope: z.string() });
export const historySchema = z.object({ chain: z.array(backendMemorySchema), events: z.array(backendEventSchema) });
export const answerSchema = z.object({ task_id: z.string(), answer: z.string(), cited_ids: z.array(z.string()), memories: z.array(backendMemorySchema) });
export type BackendAnswer = z.infer<typeof answerSchema>;
export type Episode = z.infer<typeof episodeSchema>;
export type MemoryHistory = z.infer<typeof historySchema>;
const evidenceSchema = z.object({ memory_id: z.string(), shown: z.boolean(), correct: z.boolean(), task_id: z.string() });
const decisionsSchema = z.object({ decisions: z.array(z.object({ memory_id: z.string(), action: z.enum(["promote", "retire", "flag"]), reason: z.string(), task_ids: z.array(z.string()) })) });

async function request<T extends z.ZodTypeAny>(member: string, path: string, schema: T, body?: object, signal?: AbortSignal): Promise<z.output<T>> {
  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}${path}`, { method: body ? "POST" : "GET", headers: { "X-BrainBob-Member": member, ...(body ? { "Content-Type": "application/json" } : {}) }, body: body ? JSON.stringify(body) : undefined, signal, cache: "no-store" });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error("Couldn’t reach the BrainBob backend. Check that it is running, then try again.");
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data.detail === "string" ? data.detail : `Backend request failed (${response.status}).`);
  }
  const parsed = schema.safeParse(await response.json());
  if (!parsed.success) throw new Error("The backend returned an unexpected response. Check that frontend and backend versions match.");
  return parsed.data;
}
const midPath = (id: string) => `/memories/${encodeURIComponent(id)}`;
// Org-mode ingestion returns maintenance decisions; legacy ingestion returns memories.
const ingestionDecisionSchema = z.object({ memory_id: z.string().nullable(), action: z.enum(["add", "tentative", "supersede", "reject"]), reason: z.string(), text: z.string().default(""), related: z.array(z.string()).default([]), model: z.string().nullable().optional() });
export function eventsUrl(member: string, after: number) {
  return `${BACKEND_URL}/events?${new URLSearchParams({ member, after: String(after) })}`;
}
export const brainApi = {
  memories: (member: string, signal?: AbortSignal) => request(member, "/memories", z.array(backendMemorySchema), undefined, signal),
  ask: (question: string, reader: string, signal?: AbortSignal) => request(memberId(reader), "/ask", answerSchema, { question, reader }, signal),
  remember: (text: string, scope: string, author: string, signal?: AbortSignal) => request(author, "/episodes", z.object({ episode_id: z.string(), memories: z.array(z.union([backendMemorySchema, ingestionDecisionSchema])) }), { text, scope, author, authority: "discussion", source: "brainbob-chat" }, signal),
  feedback: (task_id: string, correct_answer: string, member: string, signal?: AbortSignal) => request(member, "/feedback", z.object({ evidence: z.array(evidenceSchema) }), { task_id, correct_answer }, signal),
  review: (member: string, signal?: AbortSignal) => request(member, "/review", decisionsSchema, {}, signal),
  episode: (id: string, member: string, signal?: AbortSignal) => request(member, `/episodes/${encodeURIComponent(id)}`, episodeSchema, undefined, signal),
  history: (id: string, member: string, signal?: AbortSignal) => request(member, `${midPath(id)}/history`, historySchema, undefined, signal),
  correct: (id: string, text: string, author: string) => request(author, `${midPath(id)}/correct`, z.object({ memory: backendMemorySchema, retired_id: z.string() }), { text, author }),
  retire: (id: string, reason: string, author: string) => request(author, `${midPath(id)}/retire`, z.object({ memory: backendMemorySchema }), { reason, author }),
  lock: (id: string, owner: string) => request(owner, `${midPath(id)}/lock`, z.object({ memory: backendMemorySchema }), { owner }),
  resolve: (id: string, owner: string, action: "keep" | "retire" | "correct", text?: string) => request(owner, `${midPath(id)}/resolve`, z.object({ memory: backendMemorySchema }), { owner, action, text }),
};
