import { canRead, sceneScope, type BackendMemory } from "./brain-api";
import type { DeskId } from "./desk-sessions";
import type { SceneCue, Point } from "./scene-animation";
import { memberForReader } from "./sample-company";

export const deskDestinations: Record<DeskId, Point> = { left: [-3.1, 1.5], center: [.7, 1.2], right: [4.3, -.4] };

/** A receipt for a real /memories load, not a fabricated persisted retrieval event. */
export function sessionFileCues(memories: BackendMemory[], reader: string, sessionId: string, desk: DeskId): SceneCue[] {
  const name = memberForReader(reader)?.label.split(" ")[0] ?? "Your";
  const records = memories.flatMap((memory) => {
    const scope = sceneScope(memory.scope);
    return scope && memory.status !== "retired" && canRead(memory.scope, reader) ? [{ id: memory.id, scope }] : [];
  });
  return (["individual", "team", "organization"] as const).flatMap((scope) => {
    const group = records.filter((record) => record.scope === scope);
    return group.length ? [{ id: `session-${sessionId}-${scope}`, action: "retrieved" as const, scope, source: "session" as const,
      title: `Getting ${name}’s session file`, seconds: 3, records: group, destination: deskDestinations[desk] }] : [];
  });
}
