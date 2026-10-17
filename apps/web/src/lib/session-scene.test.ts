import { describe, expect, it } from "vitest";
import { backendMemorySchema } from "./brain-api";
import { sessionFileCues, deskDestinations } from "./session-scene";
import { performanceForCue, cueForSession } from "./scene-animation";
import { defaultReader } from "./sample-company";

const memory = (id: string, scope: string, status = "trial") => backendMemorySchema.parse({ id, scope, status, text: id, author: "sales-01", origin: "ep-1", date: "2026-10-17" });

describe("session file presentation", () => {
  it("collects only the person's live accessible context, never executive, peer or retired records", () => {
    const records = [memory("me", defaultReader), memory("sales", "rusty-rod/sales"), memory("org", "rusty-rod"),
      memory("executive", "rusty-rod/executive"), memory("peer", "rusty-rod/sales/sales-02"), memory("retired", defaultReader, "retired")];
    const before = structuredClone(records);
    const cues = sessionFileCues(records, defaultReader, "center-1", "center");
    expect(cues.flatMap((cue) => cue.records?.map((record) => record.id))).toEqual(["me", "sales", "org"]);
    expect(new Set(cues.map((cue) => cue.scope)).size).toBe(3);
    expect(cues.every((cue) => cue.source === "session")).toBe(true);
    expect(records).toEqual(before);
  });

  it("delivers to the selected desk and never invents a file for an empty context", () => {
    expect(sessionFileCues([], defaultReader, "empty", "left")).toEqual([]);
    for (const desk of ["left", "center", "right"] as const) {
      const cue = cueForSession(sessionFileCues([memory("org", "rusty-rod")], defaultReader, desk, desk)[0], defaultReader)!;
      const arrived = performanceForCue(cue, 1, 1);
      expect(arrived.x).toBe(deskDestinations[desk][0]);
      expect(arrived.z).toBeCloseTo(deskDestinations[desk][1] + .9);
      expect(arrived.moving).toBe(false);
    }
  });
});
