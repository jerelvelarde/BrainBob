// Browser integration fixture only. No inference, production data, or filesystem writes.
// Run: node apps/web/scripts/contract-fixture.mjs (stop before starting the real backend).
import { createServer } from "node:http";
const memories = new Map(), episodes = new Map(), tasks = new Map(), clients = new Set(), events = [];
let memoryNumber = 0, taskNumber = 0;
const emit = (type, data) => {
  const event = { type, ts: Date.now() / 1000, seq: events.length + 1, ...data };
  events.push(structuredClone(event));
  for (const client of clients) client.write(`id: ${event.seq}\ndata: ${JSON.stringify(event)}\n\n`);
};
const add = (text, scope, author = "Contract fixture", supersedes = null, owner = null) => {
  const id = `fixture-m${++memoryNumber}`, origin = `fixture-ep${memoryNumber}`;
  episodes.set(origin, { id: origin, text: `[CONTRACT FIXTURE] ${text}`, date: "2026-10-17", source: "Contract fixture · no inference", scope });
  const memory = { id, text: `[Fixture] ${text}`, scope, author, origin, date: "2026-10-17", status: owner ? "locked" : "trial", reason: "", flagged: false, supersedes, owner };
  memories.set(id, memory); emit("memory.added", { memory: structuredClone(memory) }); return memory;
};
add("Atlas pilot is approved for November 6, 2026.", "rusty-rod");
add("Cite the approved organization commitment in client updates.", "rusty-rod/sales");
add("sales-01 prefers concise client updates.", "rusty-rod/sales/sales-01");
const visible = (scope, reader) => !reader || reader === scope || reader.startsWith(`${scope}/`);
const retire = (m, reason, confirmed) => { m.status = "retired"; m.flagged = false; m.reason = reason; emit("memory.retired", { memory_id: m.id, reason, task_ids: [], ...(confirmed ? { confirmed: true } : {}) }); };

const server = createServer(async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "http://127.0.0.1:3000");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Last-Event-ID");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  if (req.method === "OPTIONS") { res.writeHead(204); res.end(); return; }
  const url = new URL(req.url, "http://127.0.0.1:3001");
  const send = (value, status = 200) => { res.writeHead(status, { "Content-Type": "application/json" }); res.end(JSON.stringify(value)); };
  if (url.pathname === "/events") {
    res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" });
    const after = Number(url.searchParams.get("after") ?? req.headers["last-event-id"] ?? 0);
    for (const event of events.filter((e) => e.seq > after)) res.write(`id: ${event.seq}\ndata: ${JSON.stringify(event)}\n\n`);
    res.write(`id: ${events.length}\ndata: ${JSON.stringify({ type: "replay.done", seq: events.length })}\n\n`);
    clients.add(res); req.on("close", () => clients.delete(res)); return;
  }
  let body = {};
  if (req.method === "POST") { let raw = ""; for await (const chunk of req) raw += chunk; try { body = JSON.parse(raw || "{}"); } catch { send({ detail: "Invalid JSON" }, 422); return; } }
  if (url.pathname === "/memories") return send([...memories.values()]);
  if (url.pathname.startsWith("/episodes/")) { const ep = episodes.get(url.pathname.split("/")[2]); return send(ep ?? { detail: "unknown episode" }, ep ? 200 : 404); }
  if (url.pathname === "/episodes") { const m = add(body.text, body.scope, body.author); emit("episode.ingested", { episode_id: m.origin, source: "contract-fixture", n_memories: 1 }); return send({ episode_id: m.origin, memories: [m] }); }
  if (url.pathname === "/ask") {
    const found = [...memories.values()].filter((m) => m.status !== "retired" && visible(m.scope, body.reader));
    const task_id = `fixture-t${++taskNumber}`, cited_ids = found.map((m) => m.id);
    const answer = "CONTRACT FIXTURE — no model call. The approved Atlas pilot is November 6, 2026.";
    tasks.set(task_id, cited_ids); emit("memory.retrieved", { task_id, memory_ids: cited_ids }); emit("answer.produced", { task_id, answer, cited_ids });
    return send({ task_id, answer, cited_ids, memories: found });
  }
  if (url.pathname === "/feedback") {
    const ids = tasks.get(body.task_id); if (!ids) return send({ detail: "unknown task_id" }, 404);
    emit("evaluation.started", { task_id: body.task_id, memory_ids: ids });
    ids.forEach((id, i) => emit("memory.checked", { task_id: body.task_id, memory_id: id, with_correct: i !== 0, without_correct: i !== 1, flipped: i < 2 }));
    const evidence = ids.slice(0, 2).flatMap((id, i) => [true, false].map((shown) => ({ memory_id: id, task_id: body.task_id, shown, correct: i === 0 ? !shown : shown })));
    for (const e of evidence) emit("evidence.recorded", { ...e, author: "Contract fixture" });
    emit("evaluation.finished", { task_id: body.task_id, checked: ids.length, flips: Math.min(ids.length, 2) }); return send({ evidence });
  }
  if (url.pathname === "/review") {
    const m = memories.get("fixture-m1"), decisions = [];
    if (m.status === "locked") { m.flagged = true; m.reason = "Contract fixture: harmful locked rule"; emit("memory.flagged", { memory_id: m.id, reason: m.reason }); decisions.push({ memory_id: m.id, action: "flag", reason: m.reason, task_ids: [] }); }
    return send({ decisions });
  }
  const match = url.pathname.match(/^\/memories\/([^/]+)\/(history|correct|retire|lock|resolve)$/);
  if (match) {
    const [, id, action] = match, m = memories.get(id); if (!m) return send({ detail: "unknown memory id" }, 404);
    if (action === "history") {
      let first = m; while (first.supersedes) first = memories.get(first.supersedes);
      const chain = [first]; let next; while ((next = [...memories.values()].find((v) => v.supersedes === chain.at(-1).id))) chain.push(next);
      const ids = new Set(chain.map((v) => v.id)); return send({ chain, events: events.filter((e) => ids.has(e.memory_id) || ids.has(e.new_id) || ids.has(e.memory?.id)) });
    }
    if ((action === "resolve" && m.owner !== body.owner) || (["correct", "retire"].includes(action) && m.status === "locked") || (action === "lock" && m.status === "locked" && m.owner !== body.owner)) return send({ detail: "Only the recorded owner can resolve this memory" }, 403);
    if (action === "lock") { m.status = "locked"; m.owner = body.owner; emit("memory.locked", { memory_id: id, owner: body.owner }); return send({ memory: m }); }
    const operation = action === "resolve" ? body.action : action;
    let result = m;
    if (operation === "correct") { result = add(body.text, m.scope, body.author ?? body.owner, id, action === "resolve" ? body.owner : null); retire(m, `superseded by ${result.id}`); }
    else if (operation === "retire") retire(m, body.reason ?? `retired by owner ${body.owner}`);
    else m.flagged = false;
    if (action === "resolve") emit("memory.resolved", { memory_id: id, owner: body.owner, action: operation, new_id: result.id === id ? null : result.id });
    else if (action === "correct") emit("memory.corrected", { memory_id: id, new_id: result.id, author: body.author });
    return send({ memory: result, ...(operation === "correct" ? { retired_id: id } : {}) });
  }
  send({ detail: "No fixture route" }, 404);
});
server.listen(3001, "127.0.0.1", () => console.log("CONTRACT FIXTURE on 127.0.0.1:3001 — no Crusoe inference; memory resets on stop."));
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => { for (const client of clients) client.end(); server.close(() => process.exit(0)); });
