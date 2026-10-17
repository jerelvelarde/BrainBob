import { cabinetLabels, canReadScope, companyScope, defaultReader, organizationScope } from "./sample-company";
import type { SceneCue } from "./scene-animation";

const org = organizationScope;
const engineering = `${org}/engineering`;
export type DemoSource = { id: string; scope: string; at: string; author: string; authority: string; text: string; step: number };
export type DemoRecord = { id: string; scope: string; text: string; revision: number; sourceId: string; status: "active" | "retired" | "tentative" | "unresolved"; supersedes?: string };
const sources: DemoSource[] = [
  { id: "atlas-approval-01", scope: org, at: "2026-10-14T09:00:00-07:00", author: "exec-01", authority: "Authorized commitment approver (fixture)", text: "Approved client commitment: deliver the Atlas pilot on November 6, 2026.", step: 0 },
  { id: "atlas-goal-01", scope: org, at: "2026-10-14T09:15:00-07:00", author: "exec-01", authority: "Approved project brief (fixture)", text: "Atlas must reduce the time consultants spend preparing client reports.", step: 0 },
  { id: "sales-note-01", scope: defaultReader, at: "2026-10-14T10:00:00-07:00", author: "sales-01", authority: "Personal working preference (fixture)", text: "Use a concise, three-sentence client update.", step: 0 },
  { id: "atlas-estimate-01", scope: engineering, at: "2026-10-15T14:00:00-07:00", author: "eng-01", authority: "Tentative estimate; no commitment approval", text: "Our tentative estimate is November 13, 2026. This is not an approved change to the client commitment.", step: 1 },
  { id: "atlas-risk-01", scope: engineering, at: "2026-10-15T14:05:00-07:00", author: "eng-02", authority: "Unresolved team question (fixture)", text: "Whether the integration dependency will be ready is still unknown. Do not promise readiness.", step: 1 },
  { id: "atlas-approval-02", scope: org, at: "2026-10-16T11:00:00-07:00", author: "exec-01", authority: "Authorized commitment approver (fixture)", text: "Approved correction: the Atlas pilot commitment is now November 13, 2026, replacing November 6. The reporting goal is unchanged.", step: 3 },
];

const steps = [
  { title: "An approved commitment", detail: "File November 6 with its approval source.", action: "created", scope: org, reader: defaultReader, sources: ["atlas-approval-01", "atlas-goal-01"], decision: "Supported by an approved source" },
  { title: "An estimate is not a promise", detail: "Engineering proposes November 13. The approved commitment stays November 6.", action: "evaluated", scope: engineering, reader: `${engineering}/eng-01`, sources: ["atlas-estimate-01", "atlas-risk-01", "atlas-approval-01"], decision: "Tentative conflict · no overwrite" },
  { title: "Sales sees the approved fact", detail: "A Sales agent uses November 6. Private Engineering discussions stay outside this view.", action: "retrieved", scope: org, reader: defaultReader, sources: ["atlas-approval-01"], decision: "Approved commitment retained" },
  { title: "A correction with authority", detail: "The later approval creates revision 2: November 13. Revision 1 stays in history.", action: "updated", scope: org, reader: `${org}/executive/exec-01`, sources: ["atlas-approval-01", "atlas-approval-02"], decision: "Authorized correction · traceable new revision" },
  { title: "A fresh Sales agent gets it right", detail: "sales-02 uses November 13 from organization memory. The client’s reporting goal stays active.", action: "answered", scope: org, reader: `${org}/sales/sales-02`, sources: ["atlas-approval-02", "atlas-goal-01"], decision: "Current revision supplied to a fresh agent" },
  { title: "Old evidence cannot undo approval", detail: "The earlier November 6 conversation resurfaces. Its timestamp precedes the approved correction, so revision 2 stays current.", action: "evaluated", scope: org, reader: defaultReader, sources: ["atlas-approval-01", "atlas-approval-02"], decision: "Stale source · no overwrite" },
  { title: "Missing evidence is not a delete order", detail: "Sample recent conversations, record coverage, and preserve valid knowledge when evidence is missing.", action: "evaluated", scope: org, reader: defaultReader, sources: ["atlas-approval-02", "atlas-goal-01"], decision: "Coverage and judgment reported separately" },
] as const;
export const demoStepCount = steps.length;
export const demoStepTitles = steps.map((step) => step.title);
export function stepReader(index: number) { return steps[index].reader; }

/** Deterministic fixture sampler: latest 50 eligible conversations, without replacement. */
export function sampleConversations<T extends { id: string; at: string; scope: string }>(conversations: readonly T[], reader: string, seed: number, count = 10) {
  const eligible = conversations.filter((item) => canReadScope(item.scope, reader)).toSorted((a, b) => a.at.localeCompare(b.at)).slice(-50);
  let state = seed >>> 0;
  const shuffled = [...eligible];
  for (let i = shuffled.length - 1; i > 0; i--) {
    state = (Math.imul(1664525, state) + 1013904223) >>> 0;
    const j = Math.floor((state / 4294967296) * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return { seed, eligibleIds: eligible.map((item) => item.id), selectedIds: shuffled.slice(0, count).map((item) => item.id) };
}

export function demoView(index: number, reader: string) {
  const step = steps[index];
  const canSeeStep = canReadScope(step.scope, reader);
  const availableSources = sources.filter((source) => source.step <= index && canReadScope(source.scope, reader));
  const visibleSourceIds = new Set(availableSources.map((source) => source.id));
  const allRecords: DemoRecord[] = [
    { id: "atlas-date-r1", scope: org, text: "Atlas pilot: November 6, 2026", revision: 1, sourceId: "atlas-approval-01", status: index >= 3 ? "retired" : "active" },
    { id: "atlas-goal-r1", scope: org, text: "Reduce client-report preparation time", revision: 1, sourceId: "atlas-goal-01", status: "active" },
    { id: "sales-style-r1", scope: defaultReader, text: "Use a concise, three-sentence update", revision: 1, sourceId: "sales-note-01", status: "active" },
    ...(index >= 1 ? [
      { id: "atlas-estimate-r1", scope: engineering, text: "November 13 is a tentative estimate", revision: 1, sourceId: "atlas-estimate-01", status: "tentative" as const },
      { id: "atlas-risk-r1", scope: engineering, text: "Integration readiness remains unknown", revision: 1, sourceId: "atlas-risk-01", status: "unresolved" as const },
    ] : []),
    ...(index >= 3 ? [{ id: "atlas-date-r2", scope: org, text: "Atlas pilot: November 13, 2026", revision: 2, sourceId: "atlas-approval-02", status: "active" as const, supersedes: "atlas-date-r1" }] : []),
  ];
  const records = allRecords.filter((record) => canReadScope(record.scope, reader));
  const routine = Array.from({ length: 52 }, (_, i) => ({ id: `routine-${String(i + 1).padStart(2, "0")}`, at: `2026-10-13T${String(Math.floor(i / 3)).padStart(2, "0")}:${String((i % 3) * 20).padStart(2, "0")}:00-07:00`, scope: org }));
  const audit = index === 6 ? sampleConversations([...routine, ...availableSources], reader, 17) : undefined;
  const covered = audit?.selectedIds.includes("atlas-approval-02");
  const sceneScope = companyScope(step.scope)!.scope;
  const cue: SceneCue | undefined = canSeeStep ? {
    id: `atlas-fixture-${index}-${reader}`, source: "fixture", action: step.action, scope: sceneScope, title: step.title,
    seconds: 9, records: records.filter((record) => record.scope === step.scope && record.status !== "retired").map((record) => ({ id: record.id, scope: sceneScope })),
    // Source correctness is not the backend's leave-one-out usefulness verdict.
    evaluation: step.action === "evaluated" ? { phase: "check" } : undefined,
    evaluationLabel: step.action === "evaluated" ? index === 1 ? "TENTATIVE · HOLD" : index === 5 ? "STALE · KEEP CURRENT" : covered ? "SOURCE IN SAMPLE" : "EVIDENCE MISSING · KEEP" : undefined,
  } : undefined;
  return {
    index, reader, labels: cabinetLabels(reader), cue,
    title: canSeeStep ? step.title : "Private team activity",
    detail: canSeeStep ? step.detail : "This member’s view does not include that team’s source, record, or decision.",
    decision: canSeeStep ? step.decision : "Outside this preview’s scope",
    sourceIds: canSeeStep ? step.sources.filter((id) => visibleSourceIds.has(id)) : [],
    sources: availableSources,
    records,
    currentCommitment: index >= 3 ? "November 13, 2026" : "November 6, 2026",
    answer: index === 2 || index === 4 ? { text: `The approved Atlas pilot commitment is ${index === 4 ? "November 13" : "November 6"}, 2026. The reporting goal is unchanged.`, citedIds: [index === 4 ? "atlas-date-r2" : "atlas-date-r1", "atlas-goal-r1"], agent: index === 4 ? "Fresh agent for sales-02" : "Agent for sales-01" } : undefined,
    audit: audit ? { ...audit, decisiveEvidenceCovered: covered, judgment: covered ? "Approval source is available for a check" : "Insufficient evidence in this sample; retain the record", cutoff: availableSources.at(-1)?.at } : undefined,
    model: null, execution: "scripted fixture" as const, usefulness: "Not run", cost: null,
  };
}

/** Exports only this member's synthetic view, never the whole fixture source collection. */
export function exportDemoView(index: number, reader: string) {
  const { cue: _cue, labels: _labels, ...view } = demoView(index, reader);
  return { format: "brainbob-rusty-rod-preview-v1", ...view, authorization: "Client-side preview only; not server authorization evidence" };
}
