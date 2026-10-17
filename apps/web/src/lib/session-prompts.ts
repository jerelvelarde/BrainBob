import { canReadScope, companyScope, memberForReader, teamForReader } from "./sample-company";
import type { MemoryScope } from "./memory";

export type PromptMemory = { id: string; text: string; scope: string; status: string; flagged?: boolean };
export type SessionPrompt = { tier: MemoryScope; title: string; message: string; context: string; memoryId?: string };

/** Deterministic starters from authorized-view records; no suggestion-model call. */
export function sessionPrompts(records: readonly PromptMemory[], reader: string): SessionPrompt[] {
  const member = memberForReader(reader), team = teamForReader(reader);
  const visible = member ? records.filter((record) => canReadScope(record.scope, reader) && record.status !== "retired" && !record.flagged) : [];
  return (["individual", "team", "organization"] as const).map((tier) => {
    const candidates = visible.filter((record) => companyScope(record.scope)?.scope === tier);
    const memory = candidates.find((record) => /atlas|prefer|working|commitment|client update/i.test(record.text)) ?? candidates[0];
    const uncertain = memory && ["tentative", "unresolved"].includes(memory.status);
    const title = uncertain ? "Untangle an open question" : tier === "individual" ? "Make it sound like me"
      : tier === "team" ? team?.slug === "sales" ? "Prepare a client update" : team?.slug === "engineering" ? "Review our assumptions" : "Recap our decisions"
      : memory && /atlas/i.test(memory.text) ? "Catch me up on Atlas" : "See the bigger picture";
    const task = tier === "individual" ? "Help me apply my saved working preferences to my next update."
      : tier === "team" ? `Help me prepare my next ${team?.label ?? "team"} update using our shared guidance.`
      : "Summarize the current company context relevant to my work and cite the supporting memories.";
    return { tier, title, memoryId: memory?.id,
      context: memory ? `${uncertain ? "Open question · " : ""}${memory.text}` : tier === "individual" ? "Find my saved preferences and working style."
        : tier === "team" ? `Find guidance shared with ${team?.label ?? "my team"}.` : "Find the latest shared company context.",
      message: memory ? `${task}\n\nRelevant saved context: “${memory.text}”\nCheck the current evidence; separate approved facts from tentative or unresolved context.` : `${task} If no relevant memory is available, tell me what is missing.` };
  });
}
