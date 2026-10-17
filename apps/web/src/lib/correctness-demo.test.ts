import { describe, expect, it } from "vitest";
import { demoView, exportDemoView, sampleConversations } from "./correctness-demo";
import { cabinetLabels, canReadScope, defaultReader, demoMembers, demoScopes, demoTeams } from "./sample-company";
import { sceneScope } from "./brain-api";

describe("Rusty Rod demo policy and evidence", () => {
  it("has 22 unique scopes and 18 members, each with exactly three ancestor scopes", () => {
    expect(demoMembers).toHaveLength(18); expect(demoScopes).toHaveLength(22);
    expect(new Set(demoScopes.map((scope) => scope.path)).size).toBe(22);
    expect(demoTeams.map((team) => demoMembers.filter((member) => member.team === team.slug).length)).toEqual([3, 5, 10]);
    for (const member of demoMembers) {
      expect(demoScopes.filter((scope) => canReadScope(scope.path, member.path))).toHaveLength(3);
      expect(cabinetLabels(member.path).individual).toBe(member.id);
      expect(sceneScope(member.path)).toBe("individual");
      expect(sceneScope(`rusty-rod/${member.team}`)).toBe("team");
    }
  });

  it("keeps tentative estimates and unresolved risks separate from the approved commitment", () => {
    const view = demoView(1, "rusty-rod/engineering/eng-01");
    expect(view.currentCommitment).toBe("November 6, 2026");
    expect(view.records.find((record) => record.id === "atlas-estimate-r1")?.status).toBe("tentative");
    expect(view.records.find((record) => record.id === "atlas-risk-r1")?.status).toBe("unresolved");
    expect(view.cue?.evaluation?.verdict).toBeUndefined();
    expect(view.usefulness).toBe("Not run");
  });

  it("creates a traceable correction, preserves unrelated knowledge, and retraces the old date", () => {
    const after = demoView(3, defaultReader), before = demoView(2, defaultReader);
    expect(before.currentCommitment).toBe("November 6, 2026");
    expect(after.currentCommitment).toBe("November 13, 2026");
    expect(after.records.find((record) => record.id === "atlas-date-r1")?.status).toBe("retired");
    expect(after.records.find((record) => record.id === "atlas-date-r2")).toMatchObject({ revision: 2, supersedes: "atlas-date-r1", sourceId: "atlas-approval-02" });
    expect(after.records.find((record) => record.id === "atlas-goal-r1")?.status).toBe("active");
    expect(demoView(4, "rusty-rod/sales/sales-02").answer?.citedIds).toEqual(["atlas-date-r2", "atlas-goal-r1"]);
  });

  it("filters private records, evidence, decision details, and exports even for Executive previews", () => {
    for (const reader of [defaultReader, "rusty-rod/executive/exec-01", "rusty-rod/sales/sales-02"]) {
      const view = demoView(1, reader);
      expect(view.cue).toBeUndefined(); expect(view.sourceIds).toEqual([]);
      const exported = JSON.stringify(exportDemoView(6, reader));
      for (const privateId of ["atlas-estimate", "atlas-risk", "eng-01", "eng-02"]) expect(exported).not.toContain(privateId);
      if (reader !== defaultReader) expect(exported).not.toContain("sales-note-01");
    }
    expect(canReadScope("rusty-rod/sales", "rusty-rod/salesforce/user")).toBe(false);
  });

  it("samples only the latest 50 eligible conversations reproducibly without replacement", () => {
    const conversations = Array.from({ length: 70 }, (_, i) => ({ id: `c${i}`, at: String(i).padStart(3, "0"), scope: i % 7 === 0 ? "rusty-rod/engineering" : "rusty-rod" }));
    const sample = sampleConversations(conversations, defaultReader, 17);
    expect(sample).toEqual(sampleConversations(conversations, defaultReader, 17));
    expect(sample.eligibleIds).toHaveLength(50); expect(new Set(sample.selectedIds).size).toBe(10);
    expect(sample.eligibleIds).not.toContain("c1");
    expect(sample.selectedIds.every((id) => sample.eligibleIds.includes(id))).toBe(true);
    expect(sample.selectedIds.some((id) => Number(id.slice(1)) % 7 === 0)).toBe(false);
  });

  it("discloses coverage independently of judgment and never deletes on a sample miss", () => {
    const view = demoView(6, defaultReader);
    expect(view.audit?.decisiveEvidenceCovered).toBe(view.audit?.selectedIds.includes("atlas-approval-02"));
    expect(view.audit?.decisiveEvidenceCovered).toBe(false);
    expect(view.audit?.judgment).toContain("Insufficient evidence");
    expect(view.records.find((record) => record.id === "atlas-goal-r1")?.status).toBe("active");
    expect(view.records.find((record) => record.id === "atlas-date-r2")?.status).toBe("active");
    expect(view.model).toBeNull(); expect(view.cost).toBeNull(); expect(view.execution).toBe("scripted fixture");
  });

  it("keeps the later approved revision when older evidence resurfaces", () => {
    const view = demoView(5, defaultReader);
    expect(view.decision).toBe("Stale source · no overwrite");
    expect(view.currentCommitment).toBe("November 13, 2026");
    expect(view.records.find((record) => record.id === "atlas-date-r2")?.status).toBe("active");
    expect(view.sourceIds).toEqual(["atlas-approval-01", "atlas-approval-02"]);
  });
});
