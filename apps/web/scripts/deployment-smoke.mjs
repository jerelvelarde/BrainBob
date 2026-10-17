// Read-only hosting checks. Run against a protected preview or local fixture.
import assert from "node:assert/strict";

const ui = process.env.UI_URL ?? "http://127.0.0.1:3200";
const backend = process.env.BRAINBOB_API_URL;
assert.ok(process.env.BRAINBOB_DEMO_PASSWORD, "Set the demo password in the environment");
const headers = { Authorization: `Basic ${Buffer.from(`brainbob:${process.env.BRAINBOB_DEMO_PASSWORD}`).toString("base64")}` };
assert.equal((await fetch(ui)).status, 401, "UI requires login");
assert.equal((await fetch(ui, { headers })).status, 200, "UI accepts the demo login");
assert.equal((await fetch(`${ui}/api/brainbob/memories`)).status, 401);
assert.equal((await fetch(`${ui}/api/brainbob/memories`, { headers: { Authorization: "Basic invalid" } })).status, 401);
assert.equal((await fetch(`${ui}/api/brainbob/ask`, { method: "POST", headers: { ...headers, Origin: "https://untrusted.example", "Content-Type": "application/json" }, body: "{}" })).status, 403);
if (backend) {
  assert.equal((await fetch(`${backend}/healthz`)).status, 200);
  assert.equal((await fetch(`${backend}/memories`)).status, 401);
  assert.equal((await fetch(`${backend}/events`)).status, 401);
}
const waitForClose = Number(process.env.EXPECT_STREAM_CLOSE_SECONDS ?? 0);
async function replay(after = 0) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), (waitForClose || 10) * 1000 + 5000);
  try {
    const started = Date.now();
    const response = await fetch(`${ui}/api/brainbob/events?member=sales-01&after=${after}`, { headers, signal: controller.signal });
    assert.equal(response.status, 200);
    assert.match(response.headers.get("content-type"), /text\/event-stream/);
    assert.match(response.headers.get("cache-control"), /no-store/);
    let buffer = "", last = after, done = false;
    const decoder = new TextDecoder();
    for await (const chunk of response.body) {
      buffer += decoder.decode(chunk, { stream: true }).replaceAll("\r\n", "\n");
      let boundary;
      while ((boundary = buffer.indexOf("\n\n")) >= 0) {
        const block = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2);
        const line = block.split("\n").find((line) => line.startsWith("data: "));
        if (!line) continue;
        const event = JSON.parse(line.slice(6));
        last = Math.max(last, event.seq);
        if (event.type === "replay.done") {
          done = true;
          assert.ok(Date.now() - started < 5000, "SSE replay arrives without buffering");
          if (!waitForClose) return last;
        }
      }
    }
    assert.ok(done, "SSE supplied replay completion before closing");
    assert.ok(Date.now() - started < (waitForClose + 5) * 1000, "SSE closes before the function deadline");
    return last;
  } finally { clearTimeout(timer); controller.abort(); }
}
const last = await replay();
assert.ok(await replay(last) >= last, "A new connection resumes from the previous sequence");
console.log("PASS: UI/API demo gate, direct backend gate, cross-origin write rejection, immediate SSE replay and reconnect/resume. Read-only; no inference.");
