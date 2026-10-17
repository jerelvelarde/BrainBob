import { canReadScope, clientOrganization, companyScope, memberForReader, memberName, teamForReader } from "./sample-company";

export type SessionRecord = { id: string; scope: string; text: string; revision: number; sourceId: string; status: "active" | "retired" | "tentative" | "unresolved"; tasks?: string[] };
export type SessionSource = { id: string; scope: string; text: string; at: string; author: string; authority: string };
export const atlasSessionTask = { id: "atlas-update", title: "Prepare the Atlas pilot client update" };

/** Deterministic fixture assembly, not a server authorization or relevance engine. */
export function buildSessionFile(records: readonly SessionRecord[], sources: readonly SessionSource[], reader: string, snapshot: number) {
  const member = memberForReader(reader), team = teamForReader(reader);
  if (!member || !team) throw new Error("Select a known Rusty Rod member to assemble a session file.");
  const visibleSources = new Map(sources.filter((source) => canReadScope(source.scope, reader)).map((source) => [source.id, source]));
  const relevant = records.filter((record) => canReadScope(record.scope, reader) && record.status !== "retired" && record.tasks?.includes(atlasSessionTask.id));
  const selected = relevant.filter((record) => visibleSources.has(record.sourceId));
  const includedSources = [...new Set(selected.map((record) => record.sourceId))].map((id) => visibleSources.get(id)!);
  const sections = (["individual", "team", "organization"] as const).map((scope) => ({
    scope, label: scope === "individual" ? member.label : scope === "team" ? team.label : "Rusty Rod",
    records: selected.filter((record) => companyScope(record.scope)?.scope === scope),
  }));
  return { id: `${member.id}-${atlasSessionTask.id}-step-${snapshot + 1}`, filename: `${member.id}-atlas-session.md`,
    member: { id: member.id, name: member.label, reader }, team: team.label, client: clientOrganization.name,
    task: atlasSessionTask, snapshot, sections, sources: includedSources, recordCount: selected.length, missingEvidenceCount: relevant.length - selected.length,
    selection: "Authored Atlas task relevance; current, accessible records with accessible evidence only",
    execution: "scripted fixture", authorization: "Client-side preview; server authorization required" };
}
export type SessionFile = ReturnType<typeof buildSessionFile>;

export function sessionFileMarkdown(file: SessionFile) {
  const lines = [`# Agent session: ${file.member.name}`, "", `Task: ${file.task.title}`, `Client: ${file.client}`,
    `Acting for: ${file.member.id} (${file.member.reader})`, `Team: ${file.team}`, `Snapshot: walkthrough step ${file.snapshot + 1}`,
    "", "Scripted fixture. Task relevance is authored; no live inference or server authorization is claimed.",
    "Use only active records as facts. Tentative estimates and unresolved questions are context, not approved commitments."];
  if (file.missingEvidenceCount) lines.push("", `Incomplete evidence: ${file.missingEvidenceCount} relevant record(s) omitted because their evidence was unavailable. Do not assume this context is complete.`);
  for (const section of file.sections) {
    lines.push("", `## ${section.scope[0].toUpperCase() + section.scope.slice(1)} — ${section.label}`, "");
    if (!section.records.length) lines.push("No relevant, supported memory in this scope.");
    for (const record of section.records) lines.push(`- [${record.status.toUpperCase()}] ${record.text} (${record.id}, revision ${record.revision}; source: ${record.sourceId})`);
  }
  lines.push("", "## Evidence", "");
  for (const source of file.sources) lines.push(`### ${source.id}`, `${source.at} · ${memberName(source.author)} (${source.author}) · ${source.authority}`, "", source.text, "");
  return lines.join("\n") + "\n";
}
