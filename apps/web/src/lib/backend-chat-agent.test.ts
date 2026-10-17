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
    const answered = vi.fn(), failed = vi.fn();
    const events = await lastValueFrom(new BackendChatAgent(() => context("ask"), answered, failed).run(input("When do we launch?")).pipe(toArray()));
    expect(fetcher.mock.calls[0][0]).toContain("/ask");
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ question: "When do we launch?", reader: defaultReader });
    expect(events.map((e) => e.type)).toEqual(["RUN_STARTED", "TEXT_MESSAGE_START", "TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END", "RUN_FINISHED"]);
    expect(events[2]).toMatchObject({ delta: "November 13, 2026" }); expect(answered).toHaveBeenCalledOnce();
  });

  it("writes the original conversation with its scope and author", async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ episode_id: "ep1", memories: [] })); vi.stubGlobal("fetch", fetcher);
    await lastValueFrom(new BackendChatAgent(() => context("remember"), vi.fn(), vi.fn()).run(input("sales-01: Call ACME at 10 AM.")).pipe(toArray()));
    expect(fetcher.mock.calls[0][0]).toContain("/episodes");
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toMatchObject({ text: "sales-01: Call ACME at 10 AM.", scope: defaultReader, author: "sales-01" });
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
    await expect(brainApi.memories()).rejects.toThrow("unexpected response");
  });
});
