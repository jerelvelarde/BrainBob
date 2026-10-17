import { describe, expect, it } from "vitest";
import { backendMemorySchema } from "./brain-api";
import { updateActiveSession } from "./active-session";
import { defaultReader } from "./sample-company";

const memory = (id: string, scope: string) => backendMemorySchema.parse({ id, scope, text: "November 6", author: "exec-01", origin: "ep-1", date: "2026-10-17", status: "promoted" });
const start = () => updateActiveSession(null, { type: "started", requestId: "run-1", question: "When is Atlas due?" }, defaultReader);

describe("active session file", () => {
  it("freezes returned records and includes only the member's own, team, and organization scopes", () => {
    const records = [memory("own", defaultReader), memory("team", "rusty-rod/sales"), memory("org", "rusty-rod"), memory("private", "rusty-rod/executive"), memory("other", "rusty-rod/sales/sales-02")];
    const file = updateActiveSession(start(), { type: "answered", requestId: "run-1", answer: { task_id: "task-1", answer: "November 6", memories: records, cited_ids: ["org", "private"] } }, defaultReader)!;
    expect(file.memories.map((item) => item.id)).toEqual(["own", "team", "org"]);
    expect(file.citedIds).toEqual(["org"]);
    records[2].text = "November 13";
    records[2].conflicts_with.push("new-record");
    expect(file.memories[2].text).toBe("November 6");
    expect(file.memories[2].conflicts_with).toEqual([]);
  });
  it("ignores late responses and cancellation after completion", () => {
    const pending = start();
    expect(updateActiveSession(pending, { type: "failed", requestId: "older", error: "late" }, defaultReader)).toBe(pending);
    const done = updateActiveSession(pending, { type: "answered", requestId: "run-1", answer: { task_id: "t1", answer: "Unknown", memories: [], cited_ids: [] } }, defaultReader);
    expect(updateActiveSession(done, { type: "cancelled", requestId: "run-1" }, defaultReader)).toBe(done);
    expect(done?.memories).toEqual([]);
  });
  it("shows failure or cancellation without inventing a completed file", () => {
    expect(updateActiveSession(start(), { type: "failed", requestId: "run-1", error: "Offline" }, defaultReader)).toMatchObject({ status: "failed", error: "Offline", memories: [] });
    expect(updateActiveSession(start(), { type: "cancelled", requestId: "run-1" }, defaultReader)).toMatchObject({ status: "cancelled", memories: [] });
  });
});
