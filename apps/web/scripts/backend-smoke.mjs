// Requires the contract Python server on :3001 and Next on :3000 (or UI_URL).
// Exercises the real Next proxy, Python routing, ACL, memory store, and SSE.
import assert from "node:assert/strict";

const base = `${process.env.UI_URL ?? "http://127.0.0.1:3000"}/api/brainbob`;
const member = "sales-01";
async function request(path, body, acting = member) {
  const response = await fetch(`${base}${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { "X-BrainBob-Member": acting, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  });
  assert.equal(response.status, 200, `${path}: ${await response.clone().text()}`);
  return response.json();
}

const source = await request("/episodes", { text: `Contract smoke ${Date.now()}: pilot November 6`, scope: "rusty-rod/sales", author: member });
const id = source.memories[0].memory_id;
assert.ok(id, "org maintenance returns a decision with the created memory id");
assert.ok((await request("/memories")).some((memory) => memory.id === id));
assert.ok(!(await request("/memories", undefined, "eng-01")).some((memory) => memory.id === id));
const answer = await request("/ask", { question: "pilot November", reader: "rusty-rod/sales/sales-01" });
assert.ok(answer.cited_ids.includes(id));
await request("/feedback", { task_id: answer.task_id, correct_answer: answer.answer });
await request("/review", {});
const corrected = await request(`/memories/${id}/correct`, { text: "Contract smoke: pilot November 7", author: member });
assert.equal(corrected.retired_id, id);
assert.equal((await request(`/memories/${corrected.memory.id}/history`)).chain.length, 2);
assert.equal((await request(`/episodes/${source.episode_id}`)).id, source.episode_id);
await request(`/memories/${corrected.memory.id}/lock`, { owner: member });
await request(`/memories/${corrected.memory.id}/resolve`, { owner: member, action: "keep" });

async function replay(after = 0) {
  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort(), 15000);
  try {
    const response = await fetch(`${base}/events?member=${member}&after=${after}`, { signal: abort.signal });
    assert.equal(response.status, 200);
    assert.match(response.headers.get("content-type"), /text\/event-stream/);
    let buffer = "";
    const decoder = new TextDecoder(), received = [];
    for await (const chunk of response.body) {
      buffer += decoder.decode(chunk, { stream: true }).replaceAll("\r\n", "\n");
      let boundary;
      while ((boundary = buffer.indexOf("\n\n")) >= 0) {
        const block = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2);
        const data = block.split("\n").find((line) => line.startsWith("data: "));
        if (!data) continue;
        const event = JSON.parse(data.slice(6)); received.push(event);
        if (event.type === "replay.done") return received;
      }
    }
    throw new Error("SSE ended before replay.done");
  } finally { clearTimeout(timer); abort.abort(); }
}

const events = await replay();
assert.ok(events.some((event) => event.type === "memory.added" && event.memory.id === id));
assert.ok(events.some((event) => event.type === "answer.produced" && event.task_id === answer.task_id));
assert.deepEqual(await replay(events.at(-1).seq), [events.at(-1)]);
console.log("PASS: same-origin HTTP + SSE, member filtering, ingest, ask, feedback, review, correction/history, source, lock/resolve, replay/resume. Deterministic models only; no quality score.");
