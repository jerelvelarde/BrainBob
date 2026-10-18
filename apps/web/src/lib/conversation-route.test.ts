import { afterEach, describe, expect, it, vi } from "vitest";
import { POST } from "../app/api/conversation/route";
import { defaultReader } from "./sample-company";

const memory = { id: "m1", text: "Maya prefers bullets", scope: defaultReader, author: "sales-01", origin: "ep1", date: "2026-10-17", status: "trial" };
const response = (body: object, status = 200) => new Response(JSON.stringify(body), { status });
const request = (member = "sales-01") => new Request("http://localhost/api/conversation", { method: "POST", headers: { "Content-Type": "application/json", "X-BrainBob-Member": member }, body: JSON.stringify({ reader: defaultReader, messages: [{ role: "user", content: "I prefer bullet points now" }] }) });
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

describe("live conversation planning boundary", () => {
  it("accepts a targeted correction of the cited team memory without publishing a personal copy", async () => {
    vi.stubEnv("BRAINBOB_CHAT_API_KEY", "test-key-not-real");
    const plan = { operation: "correct", memoryId: "m22", match: "28 percent", text: "35 percent" };
    const fetcher = vi.fn().mockResolvedValueOnce(response([{ ...memory, id: "m22", scope: "rusty-rod/executive", text: "The Atlas margin floor is 28 percent; keep the target within Executive." }]))
      .mockImplementation(() => Promise.resolve(response({ choices: [{ message: { content: JSON.stringify(plan) } }] })));
    vi.stubGlobal("fetch", fetcher);
    const req = new Request("http://localhost/api/conversation", { method: "POST", headers: { "Content-Type": "application/json", "X-BrainBob-Member": "exec-01" }, body: JSON.stringify({ reader: "rusty-rod/executive/exec-01", recentMemoryIds: ["m22"], messages: [{ role: "user", content: "Update that to 35%" }] }) });
    const result = await POST(req);
    expect(result.status).toBe(200);
    expect(await result.json()).toMatchObject({ plan });
  });

  it("recovers once from malformed or truncated model output before returning a validated plan", async () => {
    vi.stubEnv("BRAINBOB_CHAT_API_KEY", "test-key-not-real");
    const fetcher = vi.fn().mockResolvedValueOnce(response([memory]))
      .mockResolvedValueOnce(response({ choices: [{ finish_reason: "length", message: { content: '{"operation":"ask","question":"Give me' } }] }))
      .mockResolvedValueOnce(response({ model: "actual-model", choices: [{ finish_reason: "stop", message: { content: '{"operation":"ask","question":"Prepare the whole project brief."}' } }] }));
    vi.stubGlobal("fetch", fetcher);
    const result = await POST(request());
    expect(result.status).toBe(200);
    expect(await result.json()).toMatchObject({ plan: { operation: "ask", question: "Prepare the whole project brief." } });
    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(JSON.parse(fetcher.mock.calls[1][1].body).response_format.type).toBe("json_schema");
  });

  it("fails closed after two invalid plans with a specific error and no mutation", async () => {
    vi.stubEnv("BRAINBOB_CHAT_API_KEY", "test-key-not-real");
    const fetcher = vi.fn().mockResolvedValueOnce(response([memory]))
      .mockImplementation(() => Promise.resolve(response({ choices: [{ message: { content: '{"operation":"save"}' } }] })));
    vi.stubGlobal("fetch", fetcher);
    const result = await POST(request());
    expect(result.status).toBe(502);
    expect(await result.json()).toMatchObject({ code: "invalid_model_output" });
    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(fetcher.mock.calls.every(([url]) => !url.includes("/episodes") && !url.includes("/retire"))).toBe(true);
  });
  it("loads only the bound member's permitted records and never exposes the credential", async () => {
    vi.stubEnv("BRAINBOB_CHAT_API_KEY", "test-key-not-real");
    const fetcher = vi.fn().mockResolvedValueOnce(response([memory, { ...memory, id: "old", status: "retired", text: "Old preference" }]))
      .mockResolvedValueOnce(response({ model: "actual-model", choices: [{ message: { content: JSON.stringify({ operation: "save", kind: "preference", text: "Maya prefers bullets." }) } }] }));
    vi.stubGlobal("fetch", fetcher);
    const result = await POST(request());
    expect(result.status).toBe(200);
    const body = await result.json();
    expect(body).toMatchObject({ plan: { operation: "save" }, model: "actual-model" });
    expect(JSON.stringify(body)).not.toContain("test-key-not-real");
    expect(fetcher.mock.calls[0][1].headers).toEqual({ "X-BrainBob-Member": "sales-01" });
    expect(fetcher.mock.calls[1][1].body).not.toContain("Old preference");
    expect(fetcher.mock.calls.every(([url]) => !url.includes("/episodes") && !url.includes("/retire"))).toBe(true);
  });
  it("rejects identity mismatch before any backend or model request", async () => {
    const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
    expect((await POST(request("eng-01"))).status).toBe(403);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("rejects invented deletion targets and does not leak provider errors", async () => {
    vi.stubEnv("BRAINBOB_CHAT_API_KEY", "test-key-not-real");
    const fetcher = vi.fn().mockResolvedValueOnce(response([memory])).mockResolvedValueOnce(response({ choices: [{ message: { content: '{"operation":"retire","memoryId":"private-record"}' } }] }))
      .mockResolvedValueOnce(response([memory])).mockRejectedValueOnce(new Error("test-key-not-real"));
    vi.stubGlobal("fetch", fetcher);
    expect(await (await POST(request())).json()).toMatchObject({ plan: { operation: "reply" } });
    const failed = await POST(request());
    expect(failed.status).toBe(502);
    expect(await failed.text()).not.toContain("test-key-not-real");
  });
  it("rejects a correction ID absent from the current permitted records", async () => {
    vi.stubEnv("BRAINBOB_CHAT_API_KEY", "test-key-not-real");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(response([memory])).mockResolvedValueOnce(response({ choices: [{ message: { content: JSON.stringify({ operation: "correct", memoryId: "private-record", match: "28 percent", text: "35 percent" }) } }] })));
    expect(await (await POST(request())).json()).toMatchObject({ plan: { operation: "reply" } });
  });
});
