import { afterEach, describe, expect, it, vi } from "vitest";
import { requireDemoAccess } from "./demo-access";
import { GET, POST } from "../app/api/brainbob/[...path]/route";

const password = "test-demo-password-123456";
const authorization = `Basic ${Buffer.from(`brainbob:${password}`).toString("base64")}`;
const context = (path = ["memories"]) => ({ params: Promise.resolve({ path }) });
const request = (path = "memories", init: RequestInit = {}) => new Request(`https://demo.example/api/brainbob/${path}`, init);
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });

function hosted() {
  vi.stubEnv("VERCEL", "1");
  vi.stubEnv("BRAINBOB_DEMO_PASSWORD", password);
  vi.stubEnv("BRAINBOB_API_URL", "https://backend.example");
}

describe("hosted demo", () => {
  it("fails closed without a password and rejects bad credentials", () => {
    hosted();
    vi.stubEnv("BRAINBOB_DEMO_PASSWORD", "");
    expect(requireDemoAccess(request())?.status).toBe(503);
    vi.stubEnv("BRAINBOB_DEMO_PASSWORD", password);
    expect(requireDemoAccess(request())?.status).toBe(401);
    expect(requireDemoAccess(request("", { headers: { authorization: "Basic wrong" } }))?.status).toBe(401);
    expect(requireDemoAccess(request("", { headers: { authorization } }))).toBeUndefined();
  });
  it("blocks cross-origin writes despite valid ambient credentials", () => {
    hosted();
    expect(requireDemoAccess(request("ask", { method: "POST", headers: { authorization, origin: "https://attacker.example" } }))?.status).toBe(403);
  });
  it("authenticates the API independently and rejects missing or insecure hosted backends", async () => {
    hosted();
    expect((await GET(request(), context())).status).toBe(401);
    for (const url of ["", "http://backend.example", "https://user:secret@backend.example"]) {
      vi.stubEnv("BRAINBOB_API_URL", url);
      expect((await GET(request("memories", { headers: { authorization } }), context())).status).toBe(503);
    }
  });
  it("preserves method, query, identity, auth and body without forwarding cookies", async () => {
    hosted();
    const fetcher = vi.fn().mockResolvedValue(Response.json({ answer: "ok" }));
    vi.stubGlobal("fetch", fetcher);
    const response = await POST(request("ask?after=7", { method: "POST", headers: { authorization, "x-brainbob-member": "sales-01", cookie: "private=value" }, body: '{"question":"hi"}' }), context(["ask"]));
    const [url, init] = fetcher.mock.calls[0];
    expect(url.href).toBe("https://backend.example/ask?after=7");
    expect(init.method).toBe("POST");
    expect(init.body).toBe('{"question":"hi"}');
    expect(init.headers.get("authorization")).toBe(authorization);
    expect(init.headers.get("x-brainbob-member")).toBe("sales-01");
    expect(init.headers.has("cookie")).toBe(false);
    expect(await response.json()).toEqual({ answer: "ok" });
    expect(response.headers.get("cache-control")).toContain("no-store");
  });
  it("forwards SSE before completion and propagates cancellation", async () => {
    hosted();
    const cancel = vi.fn();
    const upstream = new ReadableStream({ start(controller) { controller.enqueue(new TextEncoder().encode('data: {"type":"replay.done"}\n\n')); }, cancel });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(upstream, { headers: { "Content-Type": "text/event-stream" } })));
    const response = await GET(request("events", { headers: { authorization } }), context(["events"]));
    const reader = response.body!.getReader();
    expect(new TextDecoder().decode((await reader.read()).value)).toContain("replay.done");
    await reader.cancel();
    expect(cancel).toHaveBeenCalled();
  });
  it("reports timeout without retrying mutations", async () => {
    hosted();
    const fetcher = vi.fn().mockRejectedValue(new DOMException("timeout", "TimeoutError"));
    vi.stubGlobal("fetch", fetcher);
    expect((await POST(request("ask", { method: "POST", headers: { authorization } }), context(["ask"]))).status).toBe(504);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});
