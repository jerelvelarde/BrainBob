import { describe, expect, it } from "vitest";
import { initialTrace, makeEvent, projectMemories, traceSchema } from "./memory";

describe("memory scene projection", () => {
  it("retraces the old value without mutating live history", () => {
    const seed = initialTrace();
    const update = makeEvent("updated", seed);
    const events = [...seed, update];
    expect(projectMemories(events).find((m) => m.id === "launch")?.content).toContain("25");
    expect(projectMemories(events, 3).find((m) => m.id === "launch")?.content).toContain("24");
    expect(seed).toEqual(initialTrace());
  });

  it("retains an archived memory's evidence and prevents ordinary retrieval", () => {
    const seed = initialTrace();
    const events = [...seed, makeEvent("forgotten", seed, "coffee")];
    const memory = projectMemories(events).find((m) => m.id === "coffee");
    expect(memory?.status).toBe("forgotten");
    expect(memory?.evidence).toContain("Black coffee");
    expect(() => makeEvent("retrieved", events, "coffee")).toThrow("active memory");
    expect(projectMemories(events, 3).find((m) => m.id === "coffee")?.status).toBe("active");
  });

  it("deduplicates event delivery and keeps reads/evaluations read-only", () => {
    const seed = initialTrace();
    const read = makeEvent("retrieved", seed);
    const check = makeEvent("evaluated", [...seed, read]);
    expect(projectMemories([...seed, seed[0], read, check])).toEqual(projectMemories(seed));
  });

  it("rejects invalid persisted traces", () => {
    expect(traceSchema.safeParse({ version: 1, events: [{ action: "invented" }] }).success).toBe(false);
    expect(traceSchema.safeParse({ version: 1, events: initialTrace() }).success).toBe(true);
  });
});
