import { clientOrganization, defaultReader, demoMembers, demoTeams, organizationScope } from "./sample-company";
import type { DemoRecord, DemoSource } from "./correctness-demo";

// Policy/reference documents are not conversations in the recent-conversation audit sample.
export const contextSources: DemoSource[] = [
  { id: "client-brief", scope: organizationScope, at: "2026-10-12T09:00:00-07:00", author: "exec-01", authority: "Approved client brief (fixture)", text: `${clientOrganization.name} is Rusty Rod’s logistics client for the Atlas pilot. This published brief grants no access to the client’s private records.`, step: 0 },
  { id: "office-policy", scope: organizationScope, at: "2026-10-12T10:00:00-07:00", author: "exec-03", authority: "Office policy (fixture)", text: "Bicycle parking is on the east side of the office.", step: 0 },
  ...demoTeams.map((team) => ({ id: `${team.slug}-atlas-guide`, scope: `${organizationScope}/${team.slug}`, at: "2026-10-12T11:00:00-07:00", author: `${team.prefix}-01`, authority: "Team working agreement (fixture)", step: 0,
    text: team.slug === "sales" ? "Client updates must cite the current approved commitment and preserve the client’s reporting goal." : team.slug === "executive" ? "Publish approved commitment changes with the approver, date, and superseded revision." : "Keep delivery estimates tentative until an authorized organization commitment is published." })),
  ...demoMembers.filter((member) => member.path !== defaultReader).map((member) => ({ id: `${member.id}-working-style`, scope: member.path, at: "2026-10-12T12:00:00-07:00", author: member.id, authority: "Individual working preference (fixture)", step: 0,
    text: member.team === "sales" ? "Lead with the approved delivery date, then the client outcome and next step." : member.team === "engineering" ? "Keep assumptions and unresolved dependencies explicit in project updates." : "Summarize the approved decision and its source before the rationale." })),
];
export const contextRecords: DemoRecord[] = contextSources.map((source) => ({ id: `${source.id}-r1`, scope: source.scope, text: source.text, revision: 1, sourceId: source.id, status: "active", tasks: source.id === "office-policy" ? ["office-logistics"] : ["atlas-update"] }));
