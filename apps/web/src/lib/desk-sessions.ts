import { updateActiveSession, type ActiveSession, type SessionActivity } from "./active-session";

export type DeskId = "left" | "center" | "right";
export type LocalDeskSession = { id: DeskId; reader: string; revision: number; session: ActiveSession | null };
export const initialDeskId: DeskId = "center";
export function createDeskSessions(): LocalDeskSession[] {
  return [
    { id: "left", reader: "rusty-rod/engineering/eng-01", revision: 0, session: null },
    { id: "center", reader: "rusty-rod/sales/sales-01", revision: 0, session: null },
    { id: "right", reader: "rusty-rod/executive/exec-01", revision: 0, session: null },
  ];
}

/** Replacing one desk never resets another desk's transcript or answer file. */
export function resetDesk(sessions: LocalDeskSession[], id: DeskId, reader?: string) {
  return sessions.map((desk) => desk.id === id ? { ...desk, reader: reader ?? desk.reader, revision: desk.revision + 1, session: null } : desk);
}

/** Ignore completion from an agent whose desk was replaced while its request ran. */
export function recordDeskActivity(sessions: LocalDeskSession[], id: DeskId, revision: number, event: SessionActivity) {
  return sessions.map((desk) => desk.id === id && desk.revision === revision ? { ...desk, session: updateActiveSession(desk.session, event, desk.reader) } : desk);
}
