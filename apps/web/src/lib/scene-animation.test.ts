import { describe, expect, it } from "vitest";
import { initialTrace, makeEvent, projectMemories, scopes } from "./memory";
import { backendSceneActions, cinematicsAt, cueFromMemory, samplePath, sceneClips, workerPerformance, type SceneAction } from "./scene-animation";

describe("scene choreography", () => {
  it("replays a recorded action without changing its memory projection", () => {
    const seed = initialTrace();
    const event = makeEvent("forgotten", seed, "coffee");
    const trace = [...seed, event];
    const before = JSON.stringify(trace);
    const cue = cueFromMemory(event)!;
    const first = workerPerformance(cue.action, cue.scope, 0, .6);
    workerPerformance(cue.action, cue.scope, 0, .9);
    expect(workerPerformance(cue.action, cue.scope, 0, .6)).toEqual(first);
    expect(JSON.stringify(trace)).toBe(before);
    expect(projectMemories(trace).find((m) => m.id === "coffee")?.status).toBe("forgotten");
    expect(cueFromMemory(seed[0])).toBeUndefined();
  });

  it("directs retrieval to the selected scope before returning to the task desk", () => {
    const positions = scopes.map((scope) => workerPerformance("retrieved", scope, 1, .4).x);
    expect(new Set(positions).size).toBe(3);
    for (const scope of scopes) {
      expect(workerPerformance("retrieved", scope, 1, .4).paper).toBe(true);
      expect(workerPerformance("retrieved", scope, 1, 1)).toMatchObject({ x: .7, z: 2.5, moving: false, paper: false });
    }
  });

  it("keeps the evaluator calm while runners bring records", () => {
    expect(workerPerformance("evaluated", "team", 4, .6)).toMatchObject({ pose: "inspect", expression: "focused", moving: false });
    expect(workerPerformance("evaluated", "team", 1, .6)).toMatchObject({ pose: "panic", expression: "worried", paper: true });
    expect(workerPerformance("evaluated", "team", 1, 1).pose).toBe("present");
  });

  it("uses distinct worker positions during office panic", () => {
    const positions = Array.from({ length: 6 }, (_, i) => workerPerformance("forgotten", "team", i, .62));
    for (let i = 0; i < positions.length; i++) for (let j = i + 1; j < positions.length; j++) {
      expect(Math.hypot(positions[i].x - positions[j].x, positions[i].z - positions[j].z)).toBeGreaterThan(.8);
    }
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

  it("restores lighting and camera at the end or when a dramatic cue is replaced", () => {
    const neutral = { darkness: 0, heat: 0, zoom: 1 };
    for (const action of ["forgotten", "evaluated"] as const) {
      expect(cinematicsAt(action, 0)).toEqual(neutral);
      expect(cinematicsAt(action, 1)).toEqual(neutral);
      expect(cinematicsAt(action, .12).zoom).toBeGreaterThan(cinematicsAt(action, .62).zoom);
      for (let p = 0; p <= 1; p += .01) {
        const frame = cinematicsAt(action, p);
        expect(frame.zoom).toBeLessThanOrEqual(1.1);
        expect(frame.darkness).toBeGreaterThanOrEqual(0);
        expect(frame.darkness).toBeLessThanOrEqual(1);
      }
    }
    for (const action of ["retrieved", "flagged", undefined] as const) expect(cinematicsAt(action, .62)).toEqual(neutral);
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
