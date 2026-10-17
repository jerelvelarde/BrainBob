import { afterEach, describe, expect, it, vi } from "vitest";
import { brainApi, eventsUrl } from "./brain-api";
import { defaultReader } from "./sample-company";

afterEach(() => vi.unstubAllGlobals());

describe("Rusty Rod HTTP identity", () => {
  it("requests a read-only memory summary with identity and cancellation", async () => {
    const response = { summary: "A tentative plan.", model: "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", memory_count: 2, total_count: 3, truncated: true };
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(response)));
    vi.stubGlobal("fetch", fetcher);
    const abort = new AbortController();
    expect(await brainApi.memorySummary("sales-02", abort.signal)).toEqual(response);
    expect(fetcher).toHaveBeenCalledWith("/api/brainbob/memories/summary", expect.objectContaining({ method: "GET", headers: { "X-BrainBob-Member": "sales-02" }, signal: abort.signal, body: undefined }));
  });

  it("sends the selected member on every read, write, and review request", async () => {
    const memory = { id: "m1", text: "Tentative estimate", author: "sales-01", origin: "ep1", date: "2026-10-17", status: "tentative", scope: "rusty-rod/sales", authority: "tentative", model: "fixture-model", conflicts_with: ["m0"] };
    const replies = [ [memory], { task_id: "t1", answer: "Uncertain", cited_ids: [], memories: [memory] }, { episode_id: "ep1", memories: [{ memory_id: "m1", action: "tentative", reason: "conflicts with m0", text: memory.text }] }, { evidence: [] }, { decisions: [] }, { id: "ep1", text: "Estimate", date: "2026-10-17", source: "test", scope: "rusty-rod/sales" }, { chain: [memory], events: [] }, { memory, retired_id: "m0" }, { memory }, { memory }, { memory } ];
    const fetcher = vi.fn().mockImplementation(async () => new Response(JSON.stringify(replies.shift()), { status: 200 }));
    vi.stubGlobal("fetch", fetcher);
    const result = await brainApi.memories("sales-01");
    expect(result[0]).toMatchObject({ status: "tentative", authority: "tentative", model: "fixture-model", conflicts_with: ["m0"] });
    await brainApi.ask("When?", defaultReader);
    expect((await brainApi.remember("Estimate", defaultReader, "sales-01")).memories[0]).toMatchObject({ action: "tentative" });
    await brainApi.feedback("t1", "Unknown", "sales-01");
    await brainApi.review("sales-01");
    await brainApi.episode("ep1", "sales-01");
    await brainApi.history("m1", "sales-01");
    await brainApi.correct("m0", "New", "sales-01");
    await brainApi.retire("m1", "Obsolete", "sales-01");
    await brainApi.lock("m1", "sales-01");
    await brainApi.resolve("m1", "sales-01", "keep");
    expect(fetcher).toHaveBeenCalledTimes(11);
    for (const [, options] of fetcher.mock.calls) expect(options.headers["X-BrainBob-Member"]).toBe("sales-01");
    expect(JSON.parse(fetcher.mock.calls[2][1].body).authority).toBe("discussion");
  });

  it("uses a distinct member query for each SSE connection and preserves its resume sequence", () => {
    const sales = new URL(eventsUrl("sales-01", 27), "https://brainbob.example"), executive = new URL(eventsUrl("exec-01", 0), "https://brainbob.example");
    expect(sales.origin).toBe("https://brainbob.example");
    expect(sales.pathname).toBe("/api/brainbob/events");
    expect(sales.searchParams.get("member")).toBe("sales-01");
    expect(sales.searchParams.get("after")).toBe("27");
    expect(executive.searchParams.get("member")).toBe("exec-01");
    expect(executive.searchParams.get("after")).toBe("0");
  });
});
