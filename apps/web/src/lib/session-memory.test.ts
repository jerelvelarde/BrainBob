import { describe, expect, it } from "vitest";
import { demoView } from "./correctness-demo";
import { buildSessionFile, sessionFileMarkdown } from "./session-memory";
import { defaultReader, demoMembers, demoTeams, drawersForTier } from "./sample-company";
import { cueForSession, performanceForCue, scopeCharacters, type SceneCue } from "./scene-animation";

describe("tier cabinets and session files", () => {
  it("gives each member a distinct synthetic name without changing their stable ID", () => {
    expect(new Set(demoMembers.map((member) => member.label)).size).toBe(18);
    expect(demoMembers.find((member) => member.id === "sales-01")).toMatchObject({ label: "Maya Flores", path: defaultReader });
    expect(demoMembers.every((member) => member.label.includes(" ") && member.path.endsWith(member.id))).toBe(true);
  });

  it("opens exactly the member’s own, team, and organization drawers", () => {
    for (const member of demoMembers) {
      const tiers = ["individual", "team", "organization"] as const;
      const drawers = tiers.map((tier) => drawersForTier(tier, member.path));
      expect(drawers.map((items) => items.length)).toEqual([18, 3, 2]);
      expect(drawers.flat().filter((drawer) => drawer.accessible).map((drawer) => drawer.path)).toEqual([member.path, `rusty-rod/${member.team}`, "rusty-rod"]);
    }
    expect(drawersForTier("team", defaultReader).find((drawer) => drawer.label === "Executive")?.accessible).toBe(false);
    expect(drawersForTier("organization", "unknown").some((drawer) => drawer.accessible)).toBe(false);
  });

  it("assembles all three relevant memory levels and accessible evidence into one file", () => {
    const file = demoView(4, defaultReader).sessionFile;
    expect(file.sections.map((section) => section.scope)).toEqual(["individual", "team", "organization"]);
    expect(file.sections.every((section) => section.records.length > 0)).toBe(true);
    const records = file.sections.flatMap((section) => section.records);
    expect(records.map((record) => record.id)).toContain("sales-style-r1");
    expect(records.map((record) => record.id)).toContain("sales-atlas-guide-r1");
    expect(records.map((record) => record.id)).toContain("atlas-date-r2");
    expect(file.sources.every((source) => records.some((record) => record.sourceId === source.id))).toBe(true);
    const md = sessionFileMarkdown(file);
    expect(md).toContain("Maya Flores"); expect(md).toContain("Atlas Harbor"); expect(md).toContain("November 13");
    for (const omitted of ["Bicycle parking", "atlas-estimate-01", "eng-02", "atlas-risk-r1"]) expect(md).not.toContain(omitted);
    expect(records.some((record) => record.id === "atlas-date-r1")).toBe(false);
    expect(file.sources.some((source) => source.id === "atlas-approval-01")).toBe(false);
  });

  it("never borrows another member's private preference or a client's private records", () => {
    const maya = demoView(4, defaultReader), leo = demoView(4, "rusty-rod/sales/sales-02");
    const md = sessionFileMarkdown(leo.sessionFile);
    expect(md).not.toContain("sales-note-01"); expect(md).toContain("sales-02-working-style");
    const file = buildSessionFile([...maya.records, { id: "client-private", scope: "atlas-harbor", text: "Private client finance", revision: 1, sourceId: "client-private-source", status: "active", tasks: ["atlas-update"] }], [...maya.sources, { id: "client-private-source", scope: "atlas-harbor", text: "Private client finance", author: "client", authority: "Private", at: "2026-10-17" }], defaultReader, 4);
    expect(JSON.stringify(file)).not.toContain("Private client finance");
    const executive = sessionFileMarkdown(demoView(4, "rusty-rod/executive/exec-01").sessionFile);
    expect(executive).not.toContain("engineering-atlas-guide"); expect(executive).not.toContain("sales-note-01");
  });

  it("omits a record if its evidence is inaccessible or missing, even if the record is accessible", () => {
    const view = demoView(4, defaultReader);
    const extra = { id: "unsupported", scope: "rusty-rod", text: "Do not export", revision: 1, sourceId: "private-evidence", status: "active" as const, tasks: ["atlas-update"] };
    const file = buildSessionFile([...view.records, extra], [...view.sources, { id: "private-evidence", scope: "rusty-rod/engineering", text: "private source", at: "2026-10-17", author: "eng-01", authority: "Private" }], defaultReader, 4);
    expect(JSON.stringify(file)).not.toContain("Do not export");
    expect(file.missingEvidenceCount).toBe(1); expect(sessionFileMarkdown(file)).toContain("Incomplete evidence");
    expect(() => buildSessionFile(view.records, view.sources, "atlas-harbor/sales/user", 4)).toThrow("known Rusty Rod member");
  });

  it("retains uncertainty as labeled context and rebuilds the file when retracing", () => {
    const before = demoView(1, "rusty-rod/engineering/eng-01").sessionFile;
    const after = demoView(4, "rusty-rod/engineering/eng-01").sessionFile;
    expect(sessionFileMarkdown(before)).toContain("[TENTATIVE]");
    expect(sessionFileMarkdown(before)).toContain("[UNRESOLVED]");
    expect(before.sections.flatMap((section) => section.records).map((record) => record.id)).toContain("atlas-date-r1");
    expect(after.sections.flatMap((section) => section.records).map((record) => record.id)).not.toContain("atlas-date-r1");
  });

  it("routes each memory to its tier cabinet regardless of the member’s team", () => {
    for (const team of demoTeams) for (const scope of ["individual", "team", "organization"] as const) {
      const member = demoMembers.find((person) => person.team === team.slug)!;
      const cue: SceneCue = { id: "retrieval", action: "retrieved", scope, title: "Retrieve", source: "fixture", records: [{ id: "record", scope }] };
      const projected = cueForSession(cue, member.path)!;
      expect(projected.scope).toBe(scope); expect(projected.cabinetX).toBe(scopeCharacters[scope].x);
      expect(projected.records?.[0].cabinetX).toBe(scopeCharacters[scope].x);
      expect(performanceForCue(projected, 1, .4).x).toBe(scopeCharacters[scope].x);
      expect(cue.cabinetX).toBeUndefined();
    }
  });
});
