import { canReadScope, memberForReader, teamForReader } from "./sample-company";

export type PromptMemory = { id: string; text: string; scope: string; status: string; flagged?: boolean; date?: string };
export type SessionPrompt = { action: "draft" | "plan" | "clarify"; title: string; message: string; context: string; memoryId?: string };

/** Suggestions use authorized, current records. The backend retrieves the evidence again on send. */
export function sessionPrompts(records: readonly PromptMemory[], reader: string): SessionPrompt[] {
  if (!memberForReader(reader)) return [];
  const visible = records.filter((record) => canReadScope(record.scope, reader) && record.status !== "retired" && !record.flagged)
    .toSorted((a, b) => (b.date ?? "").localeCompare(a.date ?? ""));
  const current = visible.filter((record) => !["tentative", "unresolved"].includes(record.status));
  const project = current.find((record) => /atlas|pilot/i.test(record.text))
    ?? current.find((record) => /client/i.test(record.text) && !/prefers?/i.test(record.text));
  const style = current.find((record) => record.scope === reader && /prefer|updates|style|writing/i.test(record.text));
  const work = current.find((record) => record.id !== project?.id && record.id !== style?.id
    && /handoff|risk|review|block|next|test|checkpoint|agenda|call|meeting/i.test(record.text));
  const uncertain = visible.find((record) => ["tentative", "unresolved"].includes(record.status));
  const team = teamForReader(reader)?.slug;
  const projectName = project && /atlas/i.test(project.text) ? "Atlas" : "the client";
  function prompt(action: SessionPrompt["action"], title: string, task: string, memory?: PromptMemory, fallback = ""): SessionPrompt {
    return { action, title, message: task, memoryId: memory?.id,
      context: memory ? `${["tentative", "unresolved"].includes(memory.status) ? "Still open: " : ""}${memory.text}` : fallback };
  }
  return [
    prompt("draft", project ? (projectName === "Atlas" ? "Draft an Atlas update" : "Draft a client update") : "Draft my next update",
      `Draft ${project ? "an " + projectName : "my next"} client update in my usual style, with the approved date and next step.`, project ?? style,
      "Start with the commitments and writing preferences you have shared."),
    prompt("plan", team === "engineering" ? "Plan the next handoff" : team === "executive" ? "Prepare my decision brief" : "Prepare my next client call",
      team === "engineering" ? "Prepare my next engineering handoff, including owners and blockers."
        : team === "executive" ? "Prepare a brief on commitments, risks, and decisions that need my attention."
        : "Prepare an agenda for my next client call.", work ?? current.find((record) => record.id !== project?.id && record.id !== style?.id),
      "Turn the latest shared work into a short, useful checklist."),
    uncertain ? prompt("clarify", "Resolve an open question", "Help me resolve an open question. What approval or evidence is still needed?", uncertain)
      : prompt("clarify", style ? "Polish my next message" : "Find what needs attention", style ? "Help me draft a follow-up in my usual writing style."
        : "What needs my attention next?", style ?? current.find((record) => record.id !== project?.id && record.id !== work?.id),
        "Check for missing details before making a commitment."),
  ];
}
