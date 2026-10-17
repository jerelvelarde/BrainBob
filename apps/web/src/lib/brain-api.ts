import { z } from "zod";

export const BACKEND_URL = (process.env.NEXT_PUBLIC_BRAINBOB_API_URL ?? "http://127.0.0.1:3001").replace(/\/$/, "");
export const readers = [
  { path: "krusty-krab", label: "Krusty Krab", scope: "organization" },
  { path: "krusty-krab/sales", label: "Sales Team", scope: "team" },
  { path: "krusty-krab/sales/john", label: "John", scope: "individual" },
] as const;

export function canRead(scope: string, reader: string) {
  const parent = scope.split("/").filter(Boolean), child = reader.split("/").filter(Boolean);
  return parent.length > 0 && parent.length <= child.length && parent.every((part, i) => part === child[i]);
}
export function sceneScope(path: string) {
  return readers.find((r) => r.path === path)?.scope;
}
export function scopeLabel(path: string) { return readers.find((r) => r.path === path)?.label ?? path; }

export const backendMemorySchema = z.object({
  id: z.string(), text: z.string(), author: z.string(), origin: z.string(), date: z.string(),
  status: z.enum(["trial", "promoted", "retired", "locked"]), scope: z.string(),
  reason: z.string().default(""), flagged: z.boolean().default(false),
  supersedes: z.string().nullable().default(null), owner: z.string().nullable().default(null),
});
export type BackendMemory = z.infer<typeof backendMemorySchema>;
const base = { seq: z.number().int().nonnegative(), ts: z.number() };
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

async function request<T extends z.ZodTypeAny>(path: string, schema: T, body?: object, signal?: AbortSignal): Promise<z.output<T>> {
  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}${path}`, { method: body ? "POST" : "GET", headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined, signal, cache: "no-store" });
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
export const brainApi = {
  memories: (signal?: AbortSignal) => request("/memories", z.array(backendMemorySchema), undefined, signal),
  ask: (question: string, reader: string, signal?: AbortSignal) => request("/ask", answerSchema, { question, reader }, signal),
  remember: (text: string, scope: string, author: string, signal?: AbortSignal) => request("/episodes", z.object({ episode_id: z.string(), memories: z.array(backendMemorySchema) }), { text, scope, author, source: "brainbob-chat" }, signal),
  feedback: (task_id: string, correct_answer: string, signal?: AbortSignal) => request("/feedback", z.object({ evidence: z.array(evidenceSchema) }), { task_id, correct_answer }, signal),
  review: (signal?: AbortSignal) => request("/review", decisionsSchema, {}, signal),
  episode: (id: string, signal?: AbortSignal) => request(`/episodes/${encodeURIComponent(id)}`, episodeSchema, undefined, signal),
  history: (id: string, signal?: AbortSignal) => request(`${midPath(id)}/history`, historySchema, undefined, signal),
  correct: (id: string, text: string, author: string) => request(`${midPath(id)}/correct`, z.object({ memory: backendMemorySchema, retired_id: z.string() }), { text, author }),
  retire: (id: string, reason: string, author: string) => request(`${midPath(id)}/retire`, z.object({ memory: backendMemorySchema }), { reason, author }),
  lock: (id: string, owner: string) => request(`${midPath(id)}/lock`, z.object({ memory: backendMemorySchema }), { owner }),
  resolve: (id: string, owner: string, action: "keep" | "retire" | "correct", text?: string) => request(`${midPath(id)}/resolve`, z.object({ memory: backendMemorySchema }), { owner, action, text }),
};
