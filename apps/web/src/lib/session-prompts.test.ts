import { describe, expect, it } from "vitest";
import { sessionPrompts, type PromptMemory } from "./session-prompts";
import { defaultReader } from "./sample-company";

const memory = (id: string, scope: string, text: string, status = "trial"): PromptMemory => ({ id, scope, text, status });
describe("contextual next actions", () => {
  it("offers useful actions without private context or tier labels", () => {
    const records = [memory("own", defaultReader, "Maya prefers warm client updates: progress, next step, and a question"), memory("team", "rusty-rod/sales", "Review the call agenda with Elena"), memory("org", "rusty-rod", "Atlas pilot November 13"), memory("secret", "rusty-rod/executive", "Confidential acquisition"), memory("other", "rusty-rod/sales/sales-02", "Private Leo preference")];
    const prompts = sessionPrompts(records, defaultReader);
    expect(prompts).toHaveLength(3);
    expect(prompts.map(p => p.title)).toEqual(["Draft an Atlas update", "Prepare my next client call", "Polish my next message"]);
    expect(JSON.stringify(prompts)).not.toMatch(/acquisition|Private Leo|individual memory|team memory|organization memory/);
    expect(prompts.map(p => p.memoryId)).toEqual(["org", "team", "own"]);
    // Facts displayed on a card are not sent back as authoritative retrieval evidence.
    expect(prompts[0].message).not.toContain("November 13");
  });
  it("excludes retired and flagged records and treats tentative context as unresolved", () => {
    const prompts = sessionPrompts([memory("old", "rusty-rod", "Old date", "retired"), {...memory("flag", "rusty-rod", "Disputed fact"), flagged:true}, memory("estimate", "rusty-rod/sales", "November 20 estimate", "tentative")], defaultReader);
    expect(JSON.stringify(prompts)).not.toMatch(/Old date|Disputed fact/);
    expect(prompts[2]).toMatchObject({ title:"Resolve an open question", context:"Still open: November 20 estimate" });
    expect(prompts[2].message).toContain("approval or evidence");
  });
  it("does not invent company facts for empty or unknown identities", () => {
    expect(sessionPrompts([], defaultReader)).toHaveLength(3);
    expect(JSON.stringify(sessionPrompts([], defaultReader))).not.toContain("Atlas");
    expect(sessionPrompts([memory("org", "rusty-rod", "Atlas")], "unknown")).toEqual([]);
  });
  it("changes actions with the person and newest available context", () => {
    const records = [{...memory("old", "rusty-rod", "Atlas November 6"), date:"2026-10-02", status:"retired"}, {...memory("new", "rusty-rod", "Atlas November 13"), date:"2026-10-15"}];
    const iris = sessionPrompts(records, "rusty-rod/engineering/eng-01");
    expect(iris[1].title).toBe("Plan the next handoff");
    expect(iris[0].context).toContain("November 13");
    expect(JSON.stringify(iris)).not.toContain("November 6");
  });
});
