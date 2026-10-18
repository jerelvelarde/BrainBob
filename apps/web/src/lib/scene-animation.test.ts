import { describe, expect, it } from "vitest";
import { projectMemories, scopes, type MemoryEvent } from "./memory";
import { backendSceneActions, cinematicsAt, cueFromMemory, memoryOperationAt, samplePath, sceneClips, workerPerformance, performanceForCue, type SceneAction } from "./scene-animation";

describe("scene choreography", () => {
  it("gives one memory Bob the complete create, update, and retirement job", () => {
    const cue = { id: "single-bob", scope: "team", source: "fixture", title: "Memory operation" } as const;
    for (const action of ["created", "updated", "forgotten"] as const) {
      expect(performanceForCue({ ...cue, action }, 0, 0)).toMatchObject({ x: -5.4, z: 2.5 });
      for (const p of [0, .25, .5, .75, 1]) {
        expect(performanceForCue({ ...cue, action }, 0, p).pose).not.toBe("panic");
      }
    }
    expect(performanceForCue({ ...cue, action: "created" }, 0, .1)).toMatchObject({ pose: "write", moving: false });
    expect(performanceForCue({ ...cue, action: "updated" }, 0, .52)).toMatchObject({ x: -5.4, z: 2.5, pose: "write", moving: false });
    expect(performanceForCue({ ...cue, action: "forgotten" }, 0, .5)).toMatchObject({ pose: "carry", paper: true });
    expect(performanceForCue({ ...cue, action: "forgotten" }, 0, 1)).toMatchObject({ x: 5.8, z: 2.85, paper: false });
  });

  it("hands off a single record and shreds only after Bob reaches the shredder", () => {
    for (const action of ["created", "updated", "forgotten"] as const) for (const scope of scopes) {
      const cue = { id: "record", action, scope, source: "fixture", title: "Record" } as const;
      for (let frame = 0; frame <= 100; frame++) {
        const p = frame / 100;
        const sample = memoryOperationAt(cue, p);
        // The held paper and the pickup/release mesh must never appear together.
        expect(sample.worker.paper && sample.transfer.visible).toBe(false);
        expect(sample.transfer.position.every(Number.isFinite)).toBe(true);
        expect(Math.abs(sample.worker.x)).toBeLessThan(7);
        expect(Math.abs(sample.worker.z)).toBeLessThan(5);
        if (sample.shredProgress > 0) expect(sample.worker).toMatchObject({ x: 5.8, z: 2.85, paper: false, moving: false });
        for (let index = 1; index < 6; index++) expect(performanceForCue(cue, index, p)).toMatchObject({ moving: false, paper: false, pose: "idle" });
      }
      const middle = memoryOperationAt(cue, .5);
      memoryOperationAt(cue, .9);
      expect(memoryOperationAt(cue, .5)).toEqual(middle);
      expect(memoryOperationAt(cue, 1).transfer.visible).toBe(false);
      if (action === "forgotten") expect(memoryOperationAt(cue, .82).transfer.position[1]).toBeGreaterThan(1);
    }
  });

  it("replays a recorded action without changing its memory projection", () => {
    const event: MemoryEvent = { id: "retirement", sequence: 1, action: "forgotten", memoryId: "record", title: "Retirement", scope: "team", actor: "owner", explanation: "Archived", evidence: "Source", timestamp: "2026-10-17T12:00:00Z" };
    const trace = [event];
    const before = JSON.stringify(trace);
    const cue = cueFromMemory(event)!;
    const first = workerPerformance(cue.action, cue.scope, 0, .6);
    workerPerformance(cue.action, cue.scope, 0, .9);
    expect(workerPerformance(cue.action, cue.scope, 0, .6)).toEqual(first);
    expect(JSON.stringify(trace)).toBe(before);
    expect(projectMemories(trace)).toEqual([]);
    expect(cueFromMemory()).toBeUndefined();
  });

  it("directs retrieval to the selected scope before returning to the task desk", () => {
    const positions = scopes.map((scope) => workerPerformance("retrieved", scope, 1, .4).x);
    expect(new Set(positions).size).toBe(3);
    for (const scope of scopes) {
      expect(workerPerformance("retrieved", scope, 1, .4).paper).toBe(true);
      expect(workerPerformance("retrieved", scope, 1, 1)).toMatchObject({ x: .7, z: 2.5, moving: false, paper: false });
    }
  });

  it("keeps the legacy evaluator pose calm", () => {
    expect(workerPerformance("evaluated", "team", 4, .6)).toMatchObject({ pose: "inspect", expression: "focused", moving: false });
    expect(workerPerformance("evaluated", "team", 1, .6)).toMatchObject({ pose: "panic", expression: "worried", paper: true });
    expect(workerPerformance("evaluated", "team", 1, 1).pose).toBe("present");
  });

  it("keeps every clip finite and within the office at seek boundaries", () => {
    for (const action of Object.keys(sceneClips) as SceneAction[]) for (const scope of scopes) {
      for (const p of [0, .15, .4, .62, .83, 1]) for (let i = 0; i < 6; i++) {
        const sample = workerPerformance(action, scope, i, p);
        expect([sample.x, sample.z, sample.angle, sample.distance].every(Number.isFinite)).toBe(true);
        expect(Math.abs(sample.x)).toBeLessThan(7);
        expect(Math.abs(sample.z)).toBeLessThan(5);
      }
    }
    expect(samplePath([[0, 0, 0], [1, 1, 1]], -1).x).toBe(0);
    expect(samplePath([[0, 0, 0], [1, 1, 1]], 2).x).toBe(1);
  });

  it("distinguishes promotion, content rewriting, flagging, and retirement", () => {
    expect(backendSceneActions["memory.promoted"]).toBe("promoted");
    expect(backendSceneActions["memory.retired"]).toBe("forgotten");
    expect(backendSceneActions["memory.flagged"]).toBe("flagged");
    expect(backendSceneActions["memory.rejected"]).toBe("rejected");
  });

  it("keeps the office lighting and camera neutral while retiring one record", () => {
    const neutral = { darkness: 0, heat: 0, zoom: 1 };
    for (const action of ["forgotten"] as const) {
      expect(cinematicsAt(action, 0)).toEqual(neutral);
      expect(cinematicsAt(action, 1)).toEqual(neutral);
      for (let p = 0; p <= 1; p += .01) {
        const frame = cinematicsAt(action, p);
        expect(frame).toEqual(neutral);
      }
    }
    for (const action of ["retrieved", "flagged", undefined] as const) expect(cinematicsAt(action, .62)).toEqual(neutral);
  });

  it("lets the evaluator enter and leave without dramatic lighting", () => {
    const cue = { id: "eval", action: "evaluated", scope: "team", source: "backend", title: "Check", evaluation: { phase: "start" } } as const;
    expect(performanceForCue(cue, 4, 0).x).toBeGreaterThan(7);
    expect(performanceForCue(cue, 4, 1)).toMatchObject({ x: 4.8, z: 2.3, moving: false });
    expect(performanceForCue({ ...cue, evaluation: { phase: "finish" } }, 4, 1).x).toBeGreaterThan(7);
    for (const progress of [0, .2, .6, 1]) expect(cinematicsAt("evaluated", progress)).toEqual({ darkness: 0, heat: 0, zoom: 1 });
  });

  it("keeps cinematic seeking deterministic and suppresses camera motion for reduced motion", () => {
    const frame = cinematicsAt("forgotten", .12);
    cinematicsAt("forgotten", .8);
    expect(cinematicsAt("forgotten", .12)).toEqual(frame);
    for (const action of ["forgotten", "evaluated"] as const) {
      for (const p of [0, .04, .12, .62, 1]) expect(cinematicsAt(action, p, true).zoom).toBe(1);
    }
  });
});
