import { describe, expect, it } from "vitest";
import { noteFromPreviousMessage, parseMemoryCommand } from "./chat-memory-commands";

describe("explicit conversational memory requests", () => {
  it.each(["Remember I prefer tea", "Please remember: I prefer tea", "Save I prefer tea to memory", "Add I prefer tea to my memory", "Can you please store I prefer tea in memory?"])("recognizes %s", (message) => {
    expect(parseMemoryCommand(message)).toEqual({ operation: "save", subject: "I prefer tea" });
  });
  it.each(["delete that from memory", "Please remove that from my memory", "Can you forget that?", "Forget that"])("recognizes %s", (message) => {
    expect(parseMemoryCommand(message)).toEqual({ operation: "retire", subject: "that" });
  });
  it.each(["Don't save this", "Never delete my memory", 'Explain "remember: tea"', "Do you remember me?", "Remember when we discussed tea?", "Remove the final paragraph"])("leaves %s read-only", (message) => {
    expect(parseMemoryCommand(message)).toBeUndefined();
  });
  it("does not use a question, command, or reference as a new fact", () => {
    for (const text of ["When is the pilot?", "Give me an update", "add that to memory", "delete that from memory"]) expect(noteFromPreviousMessage(text)).toBeUndefined();
    expect(noteFromPreviousMessage("My planning day is Tuesday.")).toBe("My planning day is Tuesday.");
  });
});
