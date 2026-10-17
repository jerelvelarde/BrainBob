import { afterEach, describe, expect, it, vi } from "vitest";
import { lastValueFrom, toArray } from "rxjs";
import type { RunAgentInput } from "@copilotkit/react-core/v2";
import { BackendChatAgent, type ChatContext } from "./backend-chat-agent";
import { brainApi } from "./brain-api";
import { defaultReader } from "./sample-company";

// The UI barrel imports CSS. Exercise the protocol bridge in Node with the AG-UI SDK;
// the installed CopilotKit provider and its bundled client are checked in the browser.
vi.mock("@copilotkit/react-core/v2", async () => ({ ...await import("@ag-ui/client"), ...await import("@ag-ui/core") }));

const input = (text: string): RunAgentInput => ({ threadId: "test", runId: "run-1", state: {}, tools: [], context: [], forwardedProps: {}, messages: [{ id: "u1", role: "user", content: text }] });
const response = (body: object, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const context = (mode: ChatContext["mode"]): ChatContext => ({ mode, reader: defaultReader, author: "sales-01", taskId: "t1", readOnly: false });
afterEach(() => vi.unstubAllGlobals());

describe("CopilotKit backend bridge", () => {
  it("sends questions with a reader and emits the backend answer and AG-UI lifecycle", async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ task_id: "t1", answer: "November 13, 2026", cited_ids: [], memories: [] }));
    vi.stubGlobal("fetch", fetcher);
    const answered = vi.fn(), failed = vi.fn(), activity = vi.fn();
    const events = await lastValueFrom(new BackendChatAgent(() => context("ask"), answered, failed, activity).run(input("When do we launch?")).pipe(toArray()));
    expect(fetcher.mock.calls[0][0]).toContain("/ask");
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toMatchObject({ question: expect.stringContaining("Current request: When do we launch?"), reader: defaultReader });
    expect(JSON.parse(fetcher.mock.calls[0][1].body).question).toContain("Maya Flores");
    expect(events.map((e) => e.type)).toEqual(["RUN_STARTED", "TEXT_MESSAGE_START", "TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END", "RUN_FINISHED"]);
    expect(events[2]).toMatchObject({ delta: "November 13, 2026" }); expect(answered).toHaveBeenCalledOnce();
    expect(activity.mock.calls.map(([event]) => event.type)).toEqual(["started", "answered"]);
    expect(activity.mock.calls[0][0]).toMatchObject({ requestId: "run-1", question: "When do we launch?" });
  });

  it("ends the desk's working state on cancellation and request failure", async () => {
    const activity = vi.fn();
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    const subscription = new BackendChatAgent(() => context("ask"), vi.fn(), vi.fn(), activity).run(input("Question")).subscribe();
    subscription.unsubscribe();
    expect(activity.mock.calls.map(([event]) => event.type)).toEqual(["started", "cancelled"]);
    activity.mockClear();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ detail: "Unavailable" }, 503)));
    await lastValueFrom(new BackendChatAgent(() => context("ask"), vi.fn(), vi.fn(), activity).run(input("Question")).pipe(toArray()));
    expect(activity.mock.calls.map(([event]) => event.type)).toEqual(["started", "failed"]);
  });

  it("writes the original conversation with its scope and author", async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ episode_id: "ep1", memories: [] })); vi.stubGlobal("fetch", fetcher);
    await lastValueFrom(new BackendChatAgent(() => context("remember"), vi.fn(), vi.fn()).run(input("sales-01: Call ACME at 10 AM.")).pipe(toArray()));
    expect(fetcher.mock.calls[0][0]).toContain("/episodes");
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toMatchObject({ text: "sales-01: Call ACME at 10 AM.", scope: defaultReader, author: "sales-01" });
  });

  it("reports org-mode tentative and rejected decisions without claiming they were all stored", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ episode_id: "ep1", memories: [
      { memory_id: "m2", action: "tentative", text: "November 13 estimate", reason: "conflicts with m1" },
      { memory_id: null, action: "reject", text: "November 6", reason: "stale" },
    ] })));
    const events = await lastValueFrom(new BackendChatAgent(() => context("remember"), vi.fn(), vi.fn()).run(input("Estimate")).pipe(toArray()));
    expect(events[2]).toMatchObject({ delta: expect.stringContaining("tentative: November 13 estimate") });
    expect(JSON.stringify(events)).toContain("reject: November 6");
    expect(JSON.stringify(events)).not.toContain("Filed 2");
  });

  it("sends feedback only to the selected task and reviews without inventing confirmation", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response({ evidence: [] })).mockResolvedValueOnce(response({ decisions: [] })); vi.stubGlobal("fetch", fetcher);
    let mode: ChatContext["mode"] = "feedback";
    const agent = new BackendChatAgent(() => context(mode), vi.fn(), vi.fn());
    await lastValueFrom(agent.run(input("November 13, 2026")).pipe(toArray()));
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ task_id: "t1", correct_answer: "November 13, 2026" });
    mode = "review";
    const events = await lastValueFrom(agent.run(input("Review")).pipe(toArray()));
    expect(fetcher.mock.calls[1][0]).toContain("/review"); expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({});
    expect(JSON.stringify(events)).not.toContain("confirmed");
  });

  it("keeps follow-ups in this desk and excludes evaluation gold from answering context", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(response({ task_id: "t1", answer: "Draft for Elena: pilot is November 13.", cited_ids: [], memories: [] }))
      .mockResolvedValueOnce(response({ evidence: [] }))
      .mockResolvedValueOnce(response({ task_id: "t2", answer: "Shorter draft.", cited_ids: [], memories: [] }))
      .mockResolvedValueOnce(response({ task_id: "t3", answer: "A fresh answer.", cited_ids: [], memories: [] }));
    vi.stubGlobal("fetch", fetcher);
    let mode: ChatContext["mode"] = "ask";
    const agent = new BackendChatAgent(() => context(mode), vi.fn(), vi.fn());
    await lastValueFrom(agent.run(input("Draft an Atlas update")).pipe(toArray()));
    mode = "feedback";
    await lastValueFrom(agent.run(input("SECRET EVALUATION GOLD")).pipe(toArray()));
    mode = "ask";
    await lastValueFrom(agent.run(input("Make it shorter")).pipe(toArray()));
    const followup = JSON.parse(fetcher.mock.calls[2][1].body).question;
    expect(followup).toContain("Draft for Elena");
    expect(followup).not.toContain("SECRET EVALUATION GOLD");
    await lastValueFrom(new BackendChatAgent(() => context("ask"), vi.fn(), vi.fn()).run(input("Hello")).pipe(toArray()));
    expect(JSON.parse(fetcher.mock.calls[3][1].body).question).not.toContain("Draft for Elena");
  });

  it("fails an empty provider answer without recording a successful desk file", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ task_id: "empty", answer: "", cited_ids: [], memories: [] })));
    const answered = vi.fn(), activity = vi.fn();
    const events = await lastValueFrom(new BackendChatAgent(() => context("ask"), answered, vi.fn(), activity).run(input("Hello")).pipe(toArray()));
    expect(events.at(-1)?.type).toBe("RUN_ERROR");
    expect(answered).not.toHaveBeenCalled();
    expect(activity.mock.calls.at(-1)?.[0].type).toBe("failed");
  });

  it("blocks retrace writes and feedback without a task, with no HTTP request", async () => {
    const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
    for (const state of [{ ...context("remember"), readOnly: true }, { ...context("feedback"), taskId: undefined }]) {
      const events = await lastValueFrom(new BackendChatAgent(() => state, vi.fn(), vi.fn()).run(input("hello")).pipe(toArray()));
      expect(events.at(-1)?.type).toBe("RUN_ERROR");
    }
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("reports backend failures as errors instead of successful memory receipts", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ detail: "unknown task_id" }, 404)));
    const failed = vi.fn();
    const events = await lastValueFrom(new BackendChatAgent(() => context("feedback"), vi.fn(), failed).run(input("correct answer")).pipe(toArray()));
    expect(events.map((e) => e.type)).toEqual(["RUN_STARTED", "RUN_ERROR"]); expect(failed).toHaveBeenLastCalledWith("unknown task_id");
  });

  it("preserves owner-denial errors and rejects malformed response bodies", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(response({ detail: "sales-01 is not the owner of m1" }, 403)).mockResolvedValueOnce(response({ memories: "broken" })));
    await expect(brainApi.resolve("m1", "sales-01", "retire")).rejects.toThrow("not the owner");
    await expect(brainApi.memories("sales-01")).rejects.toThrow("unexpected response");
  });
});
