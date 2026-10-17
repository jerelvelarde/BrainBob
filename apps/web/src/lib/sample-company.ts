import type { MemoryScope } from "./memory";

export const organizationScope = "rusty-rod";
export const clientOrganization = { id: "atlas-harbor", name: "Atlas Harbor", kind: "Logistics company", relationship: "Client", project: "Atlas pilot" } as const;
export const demoTeams = [
  { slug: "executive", label: "Executive", prefix: "exec", count: 3, x: -3.8, color: "#93bac3", names: ["Mara Ellis", "Theo Bennett", "Nadia Chen"] },
  { slug: "sales", label: "Sales", prefix: "sales", count: 5, x: -.5, color: "#d7b268", names: ["Maya Flores", "Leo Park", "Priya Shah", "Oscar Reed", "Zoe Brooks"] },
  { slug: "engineering", label: "Engineering", prefix: "eng", count: 10, x: 3.2, color: "#baa6ce", names: ["Iris Tan", "Owen Patel", "Ada Morgan", "Finn Rivera", "Nora Kim", "Eli Cooper", "Lena Ortiz", "Kai Thompson", "Ruby Singh", "Sam Walker"] },
] as const;
export type TeamSlug = typeof demoTeams[number]["slug"];
export const demoMembers = demoTeams.flatMap((team) => Array.from({ length: team.count }, (_, i) => {
  const id = `${team.prefix}-${String(i + 1).padStart(2, "0")}`;
  return { id, label: team.names[i], team: team.slug, path: `${organizationScope}/${team.slug}/${id}`, scope: "individual" as const };
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
export function memberForReader(reader: string) { return demoMembers.find((person) => person.path === reader); }
export function teamForReader(reader: string) { return demoTeams.find((team) => team.slug === memberForReader(reader)?.team); }
export function memberName(id: string) { return demoMembers.find((person) => person.id === id)?.label ?? id; }
export function memberId(reader: string) { return memberForReader(reader)?.id ?? reader; }
