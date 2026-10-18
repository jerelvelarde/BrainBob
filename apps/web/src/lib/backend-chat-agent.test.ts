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
  it("routes an explicit personal remember command through extraction and reports the real correction", async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ episode_id: "ep-chat", memories: [{ memory_id: "m-new", action: "supersede", text: "Maya prefers two bullets.", reason: "approved correction of m-old" }] }));
    vi.stubGlobal("fetch", fetcher);
    const answered = vi.fn();
    const events = await lastValueFrom(new BackendChatAgent(() => context("ask"), answered, vi.fn()).run(input("Remember: I prefer two bullets.")).pipe(toArray()));
    expect(fetcher.mock.calls[0][0]).toContain("/episodes");
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toMatchObject({ text: "Maya Flores: I prefer two bullets.", scope: defaultReader, author: "sales-01", authority: "approved", source: "brainbob-chat" });
    expect(events.find((e) => e.type === "TOOL_CALL_START")).toMatchObject({ toolCallName: "save_memory" });
    expect(events.find((e) => e.type === "TEXT_MESSAGE_CONTENT")).toMatchObject({ delta: "Updated: Maya prefers two bullets." });
    expect(answered).not.toHaveBeenCalled();
  });

  it("does not turn questions or quoted instructions into memory writes", async () => {
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(response({ task_id: "t1", answer: "Answer", cited_ids: [], memories: [] })));
    vi.stubGlobal("fetch", fetcher);
    for (const text of ["Do you remember my preference?", 'Explain the phrase "Remember: two bullets"', "Don't forget the proposal", 'Explain "delete that from memory"', "Can you explain how memory works?"]) {
      await lastValueFrom(new BackendChatAgent(() => context("ask"), vi.fn(), vi.fn()).run(input(text)).pipe(toArray()));
    }
    expect(fetcher.mock.calls.every(([url]) => url.endsWith("/ask"))).toBe(true);
  });

  it("saves the user's preceding statement, not an unrelated assistant answer, then retires the returned record", async () => {
    const memory = { id: "m-new", text: "Maya prefers tea during planning sessions.", scope: defaultReader, author: "sales-01", origin: "ep1", date: "2026-10-17", status: "trial" };
    const fetcher = vi.fn()
      .mockResolvedValueOnce(response({ task_id: "t1", answer: "An unrelated deadline is November 13.", cited_ids: ["m-old"], memories: [] }))
      .mockResolvedValueOnce(response({ episode_id: "ep1", memories: [{ memory_id: memory.id, action: "add", text: memory.text, reason: "new note" }] }))
      .mockResolvedValueOnce(response([memory]))
      .mockResolvedValueOnce(response({ memory: { ...memory, status: "retired" } }));
    vi.stubGlobal("fetch", fetcher);
    const agent = new BackendChatAgent(() => context("ask"), vi.fn(), vi.fn());
    await lastValueFrom(agent.run(input("I prefer tea during planning sessions.")).pipe(toArray()));
    await lastValueFrom(agent.run(input("add that to memory")).pipe(toArray()));
    expect(JSON.parse(fetcher.mock.calls[1][1].body).text).toBe("Maya Flores: I prefer tea during planning sessions.");
    const events = await lastValueFrom(agent.run(input("delete that from memory")).pipe(toArray()));
    expect(fetcher.mock.calls[3][0]).toBe("/api/brainbob/memories/m-new/retire");
    expect(fetcher.mock.calls[3][1]).toMatchObject({ headers: { "X-BrainBob-Member": "sales-01" }, signal: expect.any(AbortSignal) });
    expect(events.find((e) => e.type === "TOOL_CALL_START")).toMatchObject({ toolCallName: "retire_memory" });
    expect(events.find((e) => e.type === "TEXT_MESSAGE_CONTENT")).toMatchObject({ delta: expect.stringContaining(`Removed from active memory: ${memory.text}`) });
  });

  it("uses visible user history for add-that without saving generated prose", async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ episode_id: "ep1", memories: [] }));
    vi.stubGlobal("fetch", fetcher);
    const run = input("Please add that to memory");
    run.messages.unshift({ id: "u0", role: "user", content: "My planning day is Tuesday." }, { id: "a0", role: "assistant", content: "I don't know." });
    await lastValueFrom(new BackendChatAgent(() => context("ask"), vi.fn(), vi.fn()).run(run).pipe(toArray()));
    expect(JSON.parse(fetcher.mock.calls[0][1].body).text).toBe("Maya Flores: My planning day is Tuesday.");
  });

  it("clarifies missing notes and ambiguous deletions without mutating anything", async () => {
    const memories = ["m1", "m2"].map((id) => ({ id, text: `Planning preference ${id}`, scope: defaultReader, author: "sales-01", origin: "ep1", date: "2026-10-17", status: "trial" }));
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(response(memories)));
    vi.stubGlobal("fetch", fetcher);
    const agent = new BackendChatAgent(() => context("ask"), vi.fn(), vi.fn());
    const missing = await lastValueFrom(agent.run(input("Remember that")).pipe(toArray()));
    expect(missing.find((e) => e.type === "TEXT_MESSAGE_CONTENT")).toMatchObject({ delta: expect.stringContaining("What would you like me to remember?") });
    expect(fetcher).not.toHaveBeenCalled();
    const ambiguous = await lastValueFrom(agent.run(input("delete planning preference from memory")).pipe(toArray()));
    expect(ambiguous.find((e) => e.type === "TEXT_MESSAGE_CONTENT")).toMatchObject({ delta: expect.stringContaining("Which memory should I remove?") });
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0][1].method).toBe("GET");
  });

  it("does not turn a rejected save into permission to delete the existing conflict", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response({ episode_id: "ep1", memories: [{ memory_id: "m1", action: "reject", text: "My planning day is Tuesday", reason: "duplicate" }] }))
      .mockResolvedValueOnce(response([{ id: "m1", text: "My planning day is Tuesday", scope: defaultReader, author: "sales-01", origin: "ep1", date: "2026-10-17", status: "trial" }]));
    vi.stubGlobal("fetch", fetcher);
    const agent = new BackendChatAgent(() => context("ask"), vi.fn(), vi.fn());
    await lastValueFrom(agent.run(input("Remember: My planning day is Tuesday")).pipe(toArray()));
    const events = await lastValueFrom(agent.run(input("delete that from memory")).pipe(toArray()));
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(events.find((e) => e.type === "TEXT_MESSAGE_CONTENT")).toMatchObject({ delta: expect.stringContaining("Nothing has been removed") });
  });

  it("preserves lock errors, requires retired status, and never carries references across accounts", async () => {
    const memory = { id: "m1", text: "Planning preference", scope: defaultReader, author: "sales-01", origin: "ep1", date: "2026-10-17", status: "locked" };
    const fetcher = vi.fn()
      .mockResolvedValueOnce(response([memory])).mockResolvedValueOnce(response({ detail: "not the owner" }, 403))
      .mockResolvedValueOnce(response([memory])).mockResolvedValueOnce(response({ memory }))
      .mockResolvedValueOnce(response({ episode_id: "ep1", memories: [{ ...memory, status: "trial" }] }))
      .mockResolvedValueOnce(response([memory]));
    vi.stubGlobal("fetch", fetcher);
    let state = context("ask");
    const agent = new BackendChatAgent(() => state, vi.fn(), vi.fn());
    const denied = await lastValueFrom(agent.run(input("delete memory m1")).pipe(toArray()));
    expect(denied.at(-1)).toMatchObject({ type: "RUN_ERROR", message: "not the owner" });
    const unconfirmed = await lastValueFrom(agent.run(input("delete memory m1")).pipe(toArray()));
    expect(unconfirmed.at(-1)).toMatchObject({ type: "RUN_ERROR", message: expect.stringContaining("did not confirm") });
    await lastValueFrom(agent.run(input("Remember my planning preference")).pipe(toArray()));
    state = { ...state, reader: "rusty-rod/sales/sales-02", author: "sales-02" };
    const changed = await lastValueFrom(agent.run(input("delete that from memory")).pipe(toArray()));
    expect(changed.find((e) => e.type === "TEXT_MESSAGE_CONTENT")).toMatchObject({ delta: expect.stringContaining("Which memory") });
    expect(fetcher).toHaveBeenCalledTimes(6);
  });

  it("keeps denied, tentative and rejected chat writes distinct from saved updates", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response({ detail: "Not allowed" }, 403)).mockResolvedValueOnce(response({ episode_id: "ep", memories: [{ memory_id: "m2", action: "tentative", text: "New preference", reason: "locked source" }, { memory_id: null, action: "reject", text: "Old fact", reason: "duplicate" }] }));
    vi.stubGlobal("fetch", fetcher);
    const agent = new BackendChatAgent(() => context("ask"), vi.fn(), vi.fn());
    const denied = await lastValueFrom(agent.run(input("Remember: a preference")).pipe(toArray()));
    expect(denied.at(-1)?.type).toBe("RUN_ERROR");
    expect(JSON.stringify(denied)).not.toContain('"delta":"Updated');
    const checked = await lastValueFrom(agent.run(input("Remember: another preference")).pipe(toArray()));
    expect(checked.find((e) => e.type === "TEXT_MESSAGE_CONTENT")).toMatchObject({ delta: "Kept for review: New preference (locked source)\n\nNot saved: Old fact (duplicate)" });
    await expect(async () => brainApi.rememberPersonal("Fact", "rusty-rod", "sales-01")).rejects.toThrow("own individual session");
    await expect(async () => brainApi.rememberPersonal("Fact", defaultReader, "sales-02")).rejects.toThrow("own individual session");
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("sends questions with a reader and emits the backend answer and AG-UI lifecycle", async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ task_id: "t1", answer: "November 13, 2026", cited_ids: [], memories: [] }));
    vi.stubGlobal("fetch", fetcher);
    const answered = vi.fn(), failed = vi.fn(), activity = vi.fn();
    const events = await lastValueFrom(new BackendChatAgent(() => context("ask"), answered, failed, activity).run(input("When do we launch?")).pipe(toArray()));
    expect(fetcher.mock.calls[0][0]).toContain("/ask");
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toMatchObject({ question: expect.stringContaining("Current request: When do we launch?"), reader: defaultReader });
    expect(JSON.parse(fetcher.mock.calls[0][1].body).question).toContain("Maya Flores");
    expect(events.map((e) => e.type)).toEqual(["RUN_STARTED", "TOOL_CALL_START", "TOOL_CALL_ARGS", "TOOL_CALL_END", "TOOL_CALL_RESULT", "TEXT_MESSAGE_START", "TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END", "RUN_FINISHED"]);
    expect(events.find((event) => event.type === "TEXT_MESSAGE_CONTENT")).toMatchObject({ delta: "November 13, 2026" });
    const receipt = answered.mock.calls[0][1];
    expect(receipt).toMatchObject({ requestId: "run-1", question: "When do we launch?" });
    expect(events.find((event) => event.type === "TEXT_MESSAGE_START")).toMatchObject({ messageId: receipt.messageId });
    expect(events.find((event) => event.type === "TOOL_CALL_START")).toMatchObject({ toolCallName: "consult_memory" });
    expect(events.find((event) => event.type === "TOOL_CALL_RESULT")).toMatchObject({ content: expect.stringContaining(receipt.messageId) });
    expect(activity.mock.calls.map(([event]) => event.type)).toEqual(["started", "answered"]);
    expect(activity.mock.calls[0][0]).toMatchObject({ requestId: "run-1", question: "When do we launch?" });
  });

  it("binds each retrieval receipt to its own reply across follow-ups", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(response({ task_id: "first", answer: "First reply", cited_ids: [], memories: [] }))
      .mockResolvedValueOnce(response({ task_id: "second", answer: "Follow-up reply", cited_ids: [], memories: [] })));
    const answered = vi.fn();
    const agent = new BackendChatAgent(() => context("ask"), answered, vi.fn());
    const runs = [
      await lastValueFrom(agent.run(input("First question")).pipe(toArray())),
      await lastValueFrom(agent.run({ ...input("Follow-up"), runId: "run-2" }).pipe(toArray())),
    ];
    const first = answered.mock.calls[0][1], second = answered.mock.calls[1][1];
    expect(first.messageId).not.toBe(second.messageId);
    expect(first.question).toBe("First question");
    expect(second.requestId).toBe("run-2");
    runs.forEach((events, index) => {
      const tool = events.find((event) => event.type === "TOOL_CALL_START");
      const result = events.find((event) => event.type === "TOOL_CALL_RESULT");
      expect(result).toMatchObject({ toolCallId: tool?.toolCallId,
        content: expect.stringContaining(answered.mock.calls[index][1].messageId) });
      expect(events.find((event) => event.type === "TEXT_MESSAGE_START")).toMatchObject({ messageId: answered.mock.calls[index][1].messageId });
    });
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

  it("invalidates stale answering context after a correction and after external memory changes", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(response({ task_id: "t1", answer: "Maya prefers paragraphs.", cited_ids: [], memories: [] }))
      .mockResolvedValueOnce(response({ episode_id: "ep2", memories: [{ memory_id: "m-new", action: "supersede", text: "Maya prefers bullets.", reason: "correction" }] }))
      .mockResolvedValueOnce(response({ task_id: "t2", answer: "Maya prefers bullets.", cited_ids: [], memories: [] }))
      .mockResolvedValueOnce(response({ task_id: "t3", answer: "A fresh answer", cited_ids: [], memories: [] }));
    vi.stubGlobal("fetch", fetcher);
    let memoryVersion = "before";
    const agent = new BackendChatAgent(() => ({ ...context("ask"), memoryVersion }), vi.fn(), vi.fn());
    await lastValueFrom(agent.run(input("How do I prefer updates?")).pipe(toArray()));
    await lastValueFrom(agent.run(input("Remember: I want bullets now, not paragraphs")).pipe(toArray()));
    await lastValueFrom(agent.run(input("How do I prefer updates?")).pipe(toArray()));
    expect(JSON.parse(fetcher.mock.calls[2][1].body).question).not.toContain("Maya prefers paragraphs.");
    memoryVersion = "external-retirement";
    await lastValueFrom(agent.run(input("How do I prefer updates?")).pipe(toArray()));
    expect(JSON.parse(fetcher.mock.calls[3][1].body).question).not.toContain("Maya prefers bullets.");
  });

  it("uses Nemotron's semantic decision for a plain project update and keeps it a personal report", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(response({ plan: { operation: "save", text: "Maya reports that the Atlas pilot now requires live voice.", kind: "report" }, model: "nemotron-test" }))
      .mockResolvedValueOnce(response({ episode_id: "ep1", memories: [{ memory_id: "m-report", action: "add", text: "Maya reports a live-voice requirement.", reason: "report" }] }));
    vi.stubGlobal("fetch", fetcher);
    const events = await lastValueFrom(new BackendChatAgent(() => ({ ...context("ask"), conversational: true }), vi.fn(), vi.fn()).run(input("The Atlas pilot added live voice as a requirement")).pipe(toArray()));
    expect(fetcher.mock.calls[0][0]).toBe("/api/conversation");
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toMatchObject({ scope: defaultReader, author: "sales-01", authority: "discussion" });
    expect(events.filter((e) => e.type === "TOOL_CALL_START").map((e) => e.toolCallName)).toEqual(["understand_request", "save_memory"]);
    expect(events.find((e) => e.type === "TEXT_MESSAGE_CONTENT")).toMatchObject({ delta: expect.stringContaining("doesn’t change approved shared requirements") });
  });

  it("handles general conversation without asking the benchmark question-answering endpoint", async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ plan: { operation: "reply", text: "Happy to help. What are we working on?" }, model: "nemotron-test" }));
    vi.stubGlobal("fetch", fetcher);
    const events = await lastValueFrom(new BackendChatAgent(() => ({ ...context("ask"), conversational: true }), vi.fn(), vi.fn()).run(input("Hey Bob")).pipe(toArray()));
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(events.find((e) => e.type === "TEXT_MESSAGE_CONTENT")).toMatchObject({ delta: "Happy to help. What are we working on?" });
  });

  it("does not pass a pre-correction assistant answer to the conversation model", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(response({ plan: { operation: "ask", question: "How does Maya prefer updates?" }, model: "test" }))
      .mockResolvedValueOnce(response({ task_id: "t1", answer: "Maya prefers paragraphs.", cited_ids: [], memories: [] }))
      .mockResolvedValueOnce(response({ plan: { operation: "save", text: "Maya prefers client updates as bullet points.", kind: "preference" }, model: "test" }))
      .mockResolvedValueOnce(response({ episode_id: "ep2", memories: [{ memory_id: "m-new", action: "supersede", text: "Maya prefers client updates as bullet points.", reason: "correction" }] }))
      .mockResolvedValueOnce(response({ plan: { operation: "ask", question: "How does Maya prefer updates?" }, model: "test" }))
      .mockResolvedValueOnce(response({ task_id: "t2", answer: "Bullet points", cited_ids: [], memories: [] }));
    vi.stubGlobal("fetch", fetcher);
    const agent = new BackendChatAgent(() => ({ ...context("ask"), conversational: true }), vi.fn(), vi.fn());
    for (const text of ["How do I prefer updates?", "Actually I want bullet points now", "How do I prefer updates?"]) await lastValueFrom(agent.run(input(text)).pipe(toArray()));
    expect(fetcher.mock.calls[4][1].body).not.toContain("Maya prefers paragraphs");
    expect(fetcher.mock.calls[5][1].body).not.toContain("Maya prefers paragraphs");
    expect(JSON.parse(fetcher.mock.calls[3][1].body).text).toContain("client updates");
  });

  it("retains the user's topic when an SSE memory change invalidates assistant prose", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(response({ plan: { operation: "save", text: "Maya's notebook is Sunbeam", kind: "preference" }, model: "test" }))
      .mockResolvedValueOnce(response({ episode_id: "ep1", memories: [{ memory_id: "m1", action: "add", text: "Maya's notebook is Sunbeam", reason: "new" }] }))
      .mockResolvedValueOnce(response({ plan: { operation: "reply", text: "Clarification", }, model: "test" }));
    vi.stubGlobal("fetch", fetcher);
    let memoryVersion = "before";
    const agent = new BackendChatAgent(() => ({ ...context("ask"), memoryVersion, conversational: true }), vi.fn(), vi.fn());
    await lastValueFrom(agent.run(input("My notebook is Sunbeam")).pipe(toArray()));
    memoryVersion = "after-sse";
    await lastValueFrom(agent.run(input("Actually it is Moonbeam now")).pipe(toArray()));
    const planned = JSON.parse(fetcher.mock.calls[2][1].body);
    expect(planned.messages).toContainEqual({ role: "user", content: "My notebook is Sunbeam" });
    expect(planned.messages.some((message: {role: string}) => message.role === "assistant")).toBe(false);
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
