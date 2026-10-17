import type { MemoryScope } from "./memory";

export const organizationScope = "rusty-rod";
export const demoTeams = [
  { slug: "executive", label: "Executive", prefix: "exec", count: 3 },
  { slug: "sales", label: "Sales", prefix: "sales", count: 5 },
  { slug: "engineering", label: "Engineering", prefix: "eng", count: 10 },
] as const;
export const demoMembers = demoTeams.flatMap((team) => Array.from({ length: team.count }, (_, i) => {
  const id = `${team.prefix}-${String(i + 1).padStart(2, "0")}`;
  return { id, label: id, team: team.slug, path: `${organizationScope}/${team.slug}/${id}`, scope: "individual" as const };
}));
export const defaultReader = `${organizationScope}/sales/sales-01`;
export const demoScopes: { path: string; label: string; scope: MemoryScope }[] = [
  { path: organizationScope, label: "Rusty Rod", scope: "organization" },
  ...demoTeams.map((team) => ({ path: `${organizationScope}/${team.slug}`, label: team.label, scope: "team" as const })),
  ...demoMembers,
];

/** Presentation policy only. Real authorization must be enforced by the backend. */
export function canReadScope(scope: string, reader: string) {
  const parent = scope.split("/").filter(Boolean), child = reader.split("/").filter(Boolean);
  return parent.length > 0 && parent.length <= child.length && parent.every((part, i) => part === child[i]);
}
export function companyScope(path: string) { return demoScopes.find((scope) => scope.path === path); }
export function cabinetLabels(reader = defaultReader): Record<MemoryScope, string> {
  const member = demoMembers.find((person) => person.path === reader);
  const team = demoTeams.find((team) => team.slug === member?.team);
  return { organization: "Rusty Rod", team: team?.label ?? "Team", individual: member?.id ?? "Individual" };
}
