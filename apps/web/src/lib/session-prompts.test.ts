import { describe, expect, it } from "vitest";
import { sessionPrompts, type PromptMemory } from "./session-prompts";
import { defaultReader } from "./sample-company";
import { demoView } from "./correctness-demo";

const memory = (id: string, scope: string, text: string, status = "active"): PromptMemory => ({ id, scope, text, status });
describe("personalized memory prompts", () => {
  it("offers exactly three tier prompts from the selected member's accessible records", () => {
    const records = [memory("own", defaultReader, "Keep updates short"), memory("team", "rusty-rod/sales", "Cite approved dates"), memory("org", "rusty-rod", "Atlas pilot November 6"), memory("secret", "rusty-rod/executive", "Confidential acquisition"), memory("other", "rusty-rod/sales/sales-02", "Private Leo preference")];
    const prompts = sessionPrompts(records, defaultReader);
    expect(prompts.map((prompt) => prompt.memoryId)).toEqual(["own", "team", "org"]);
    expect(prompts.map((prompt) => prompt.tier)).toEqual(["individual", "team", "organization"]);
    expect(JSON.stringify(prompts)).not.toMatch(/acquisition|Private Leo/);
    expect(prompts[2].title).toBe("Catch me up on Atlas");
  });
  it("excludes retired and flagged records, and labels tentative context as an open question", () => {
    const prompts = sessionPrompts([memory("old", "rusty-rod", "Old date", "retired"), { ...memory("flag", "rusty-rod", "Disputed fact"), flagged: true }, memory("estimate", "rusty-rod/sales", "November 13 estimate", "tentative")], defaultReader);
    expect(prompts[2].memoryId).toBeUndefined();
    expect(prompts[1]).toMatchObject({ title: "Untangle an open question", context: "Open question · November 13 estimate" });
    expect(prompts[1].message).toContain("separate approved facts from tentative");
  });
  it("provides honest discovery prompts when no memories are available", () => {
    const prompts = sessionPrompts([], defaultReader);
    expect(prompts).toHaveLength(3);
    expect(prompts.every((prompt) => !prompt.memoryId && prompt.message.includes("If no relevant memory"))).toBe(true);
    expect(JSON.stringify(prompts)).not.toContain("Atlas");
  });
  it("refreshes prompts to the current demo revision and person", () => {
    const maya = demoView(0, defaultReader).sessionFile;
    const iris = demoView(4, "rusty-rod/engineering/eng-01").sessionFile;
    const before = sessionPrompts(maya.sections.flatMap((section) => section.records), defaultReader);
    const after = sessionPrompts(iris.sections.flatMap((section) => section.records), iris.member.reader);
    expect(before[0].memoryId).not.toBe(after[0].memoryId);
    expect(after[2].context).toContain("November 13");
    expect(after[2].context).not.toContain("November 6");
  });
});
