import { describe, expect, it } from "vitest";
import { backendEventSchema, backendMemorySchema, canRead, type StoredEvent } from "./brain-api";
import { acceptBackendEvent, cuesForEvent, emptyBackendState, eventDescription, memoriesAt } from "./backend-state";
import { performanceForCue } from "./scene-animation";
import { defaultReader, organizationScope } from "./sample-company";
const readers = [{ path: organizationScope }, { path: `${organizationScope}/sales` }, { path: defaultReader }];

const memory = (id: string, scope: string = readers[1].path, supersedes: string | null = null) => backendMemorySchema.parse({ id, text: `${id} claim`, author: "sales-01", origin: "ep-1", date: "2026-10-17", status: "trial", scope, supersedes });
const wire = (seq: number, type: string, data: object = {}) => backendEventSchema.parse({ seq, ts: 1, type, ...data });

describe("backend event projection", () => {
  it("applies replay without animating, deduplicates deliveries, and resumes state-only until replay.done", () => {
    let state = emptyBackendState();
    const added = wire(1, "memory.added", { memory: memory("m1") });
    let accepted = acceptBackendEvent(state, added);
    expect(accepted.animate).toBe(false); state = accepted.state;
    state = acceptBackendEvent(state, wire(1, "replay.done")).state;
    accepted = acceptBackendEvent(state, wire(2, "memory.promoted", { memory_id: "m1", reason: "helpful" }));
    expect(accepted.animate).toBe(true); expect(accepted.state.memories.m1.status).toBe("promoted");
    state = accepted.state;
    expect(acceptBackendEvent(state, added)).toEqual({ state, animate: false });
    state = { ...state, replaying: true };
    accepted = acceptBackendEvent(state, wire(3, "memory.locked", { memory_id: "m1", owner: "exec-01" }));
    expect(accepted.animate).toBe(false);
    state = acceptBackendEvent(accepted.state, wire(3, "replay.done")).state;
    expect(state.seq).toBe(3); expect(state.memories.m1.owner).toBe("exec-01");
    expect(() => acceptBackendEvent(state, wire(0, "replay.done"))).toThrow("history was reset");
  });

  it("uses ancestor segments, not string prefixes, for reader visibility", () => {
    expect(readers.map((scope) => canRead(scope.path, readers[2].path))).toEqual([true, true, true]);
    expect(readers.map((scope) => canRead(scope.path, readers[1].path))).toEqual([true, true, false]);
    expect(canRead("rusty-rod/sales", "rusty-rod/salesforce/john")).toBe(false);
    expect(canRead("team", readers[2].path)).toBe(false);
    expect(canRead("", readers[2].path)).toBe(false);
  });

  it("retains correction predecessors and retraces their original state without a fire scene", () => {
    let state = emptyBackendState();
    for (const event of [wire(1, "memory.added", { memory: memory("m1") }), wire(2, "memory.added", { memory: memory("m2", readers[1].path, "m1") }), wire(3, "memory.retired", { memory_id: "m1", reason: "superseded by m2" })]) state = acceptBackendEvent(state, event).state;
    expect(state.memories.m1.status).toBe("retired"); expect(state.memories.m2.supersedes).toBe("m1");
    expect(memoriesAt(state.events, 1).m1.status).toBe("trial"); expect(memoriesAt(state.events, 1).m2).toBeUndefined();
    expect(cuesForEvent(state.events[1], state, readers[2].path)[0].action).toBe("updated");
    expect(cuesForEvent(state.events[2], state, readers[2].path)).toEqual([]);
  });

  it("flags locked records without retiring them and clears the flag on owner resolution", () => {
    let state = emptyBackendState();
    for (const event of [wire(1, "memory.added", { memory: memory("m1") }), wire(2, "memory.locked", { memory_id: "m1", owner: "exec-01" }), wire(3, "memory.flagged", { memory_id: "m1", reason: "harmful" })]) state = acceptBackendEvent(state, event).state;
    expect(state.memories.m1).toMatchObject({ status: "locked", flagged: true, owner: "exec-01" });
    expect(cuesForEvent(state.events[2], state, readers[2].path)[0].action).toBe("flagged");
    state = acceptBackendEvent(state, wire(4, "memory.resolved", { memory_id: "m1", owner: "exec-01", action: "keep", new_id: null })).state;
    expect(state.memories.m1).toMatchObject({ status: "locked", flagged: false });
  });

  it("only describes explicit fresh retirement confirmation", () => {
    for (const confirmed of [undefined, false]) {
      const event = wire(1, "memory.retired", { memory_id: "m1", reason: "manual", confirmed }) as StoredEvent;
      expect(eventDescription(event)).toBe("Retired");
    }
    expect(eventDescription(wire(1, "memory.retired", { memory_id: "m1", reason: "harmful", confirmed: true }) as StoredEvent)).toContain("fresh confirmation passed");
  });

  it("animates only visible cited memories and represents every check including no flip and failed confirmation", () => {
    let state = emptyBackendState();
    for (const [i, r] of readers.entries()) state = acceptBackendEvent(state, wire(i + 1, "memory.added", { memory: memory(`m${i}`, r.path) })).state;
    const started = wire(4, "evaluation.started", { task_id: "t1", memory_ids: ["m0", "m2"] }) as StoredEvent;
    state = acceptBackendEvent(state, started).state;
    expect(cuesForEvent(started, state, readers[2].path)[0].records?.map((r) => r.id)).toEqual(["m0", "m2"]);
    expect(cuesForEvent(started, state, readers[1].path)[0].records?.map((r) => r.id)).toEqual(["m0"]);
    for (const [with_correct, without_correct, expected] of [[true, false, "helpful"], [false, true, "harmful"], [true, true, "unchanged"]] as const) {
      const checked = wire(5, "memory.checked", { task_id: "t1", memory_id: "m2", with_correct, without_correct, flipped: with_correct !== without_correct }) as StoredEvent;
      expect(cuesForEvent(checked, state, readers[1].path)).toEqual([]);
      const cue = cuesForEvent(checked, state, readers[2].path)[0];
      expect(cue.evaluation?.verdict).toBe(expected); expect(cue.records).toEqual([{ id: "m2", scope: "individual" }]);
      expect(performanceForCue(cue, 4, .5).x).toBeCloseTo(-5.8);
    }
    const failed = wire(6, "memory.checked", { task_id: null, memory_id: "m0", with_correct: false, without_correct: false, flipped: false, reason: "confirm failed" }) as StoredEvent;
    expect(cuesForEvent(failed, state, readers[2].path)[0].evaluation?.verdict).toBe("unconfirmed");
    expect(eventDescription(failed)).toContain("memory kept");
  });
});
