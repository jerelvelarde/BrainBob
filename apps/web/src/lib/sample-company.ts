import type { MemoryScope } from "./memory";

export const organizationScope = "rusty-rod";
export const clientOrganization = { id: "atlas-harbor", name: "Atlas Harbor", kind: "Logistics company", relationship: "Client", project: "Atlas pilot" } as const;
export const companyTeams = [
  { slug: "executive", label: "Executive", prefix: "exec", count: 3, names: ["Mara Ellis", "Theo Bennett", "Nadia Chen"] },
  { slug: "sales", label: "Sales", prefix: "sales", count: 5, names: ["Maya Flores", "Leo Park", "Priya Shah", "Oscar Reed", "Zoe Brooks"] },
  { slug: "engineering", label: "Engineering", prefix: "eng", count: 10, names: ["Iris Tan", "Owen Patel", "Ada Morgan", "Finn Rivera", "Nora Kim", "Eli Cooper", "Lena Ortiz", "Kai Thompson", "Ruby Singh", "Sam Walker"] },
] as const;
export type TeamSlug = typeof companyTeams[number]["slug"];
export const companyMembers = companyTeams.flatMap((team) => Array.from({ length: team.count }, (_, i) => {
  const id = `${team.prefix}-${String(i + 1).padStart(2, "0")}`;
  return { id, label: team.names[i], team: team.slug, path: `${organizationScope}/${team.slug}/${id}`, scope: "individual" as const };
}));
export const defaultReader = `${organizationScope}/sales/sales-01`;
export const companyScopes: { path: string; label: string; scope: MemoryScope }[] = [
  { path: organizationScope, label: "Rusty Rod", scope: "organization" },
  ...companyTeams.map((team) => ({ path: `${organizationScope}/${team.slug}`, label: team.label, scope: "team" as const })),
  ...companyMembers,
];

/** Presentation policy only. Real authorization must be enforced by the backend. */
export function canReadScope(scope: string, reader: string) {
  const parent = scope.split("/").filter(Boolean), child = reader.split("/").filter(Boolean);
  return parent.length > 0 && parent.length <= child.length && parent.every((part, i) => part === child[i]);
}
export function companyScope(path: string) { return companyScopes.find((scope) => scope.path === path); }
export function memberForReader(reader: string) { return companyMembers.find((person) => person.path === reader); }
export function teamForReader(reader: string) { return companyTeams.find((team) => team.slug === memberForReader(reader)?.team); }
export function memberName(id: string) { return companyMembers.find((person) => person.id === id)?.label ?? id; }
export function memberId(reader: string) { return memberForReader(reader)?.id ?? reader; }

/** Drawer labels are public synthetic company metadata; contents still follow scope ancestry. */
export function drawersForTier(scope: MemoryScope, reader: string) {
  const entries = scope === "individual" ? companyMembers
    : scope === "team" ? companyScopes.filter((item) => item.scope === "team")
    : [{ path: organizationScope, label: "Rusty Rod" }, { path: clientOrganization.id, label: clientOrganization.name }];
  return entries.map((entry) => ({ path: entry.path, label: entry.label, accessible: Boolean(memberForReader(reader)) && canReadScope(entry.path, reader) }));
}
