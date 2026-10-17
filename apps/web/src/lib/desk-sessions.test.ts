import { describe, expect, it } from "vitest";
import { createDeskSessions, recordDeskActivity, resetDesk } from "./desk-sessions";

describe("independent desk sessions", () => {
  it("keeps simultaneous requests and their failures in their own desks", () => {
    let desks = createDeskSessions();
    desks = recordDeskActivity(desks, "left", 0, { type: "started", requestId: "iris", question: "Engineering assumptions?" });
    desks = recordDeskActivity(desks, "center", 0, { type: "started", requestId: "maya", question: "Approved date?" });
    desks = recordDeskActivity(desks, "left", 0, { type: "failed", requestId: "iris", error: "Unavailable" });
    expect(desks[0].session?.status).toBe("failed");
    expect(desks[1].session).toMatchObject({ status: "working", question: "Approved date?", requestId: "maya" });
    expect(desks[2].session).toBeNull();
  });
  it("replaces only the chosen desk and ignores its previous agent's late completion", () => {
    const running = recordDeskActivity(createDeskSessions(), "center", 0, { type: "started", requestId: "old", question: "Old question" });
    const reset = resetDesk(running, "center", "rusty-rod/sales/sales-02");
    expect(reset[0]).toBe(running[0]);
    expect(reset[2]).toBe(running[2]);
    expect(reset[1]).toMatchObject({ reader: "rusty-rod/sales/sales-02", revision: 1, session: null });
    expect(recordDeskActivity(reset, "center", 0, { type: "started", requestId: "late", question: "Stale callback" })).toEqual(reset);
  });
});
