import type { BackendMemory } from "./brain-api";

export type MemoryCommand = { operation: "save" | "retire"; subject: string };

// Only a direct request can mutate memory. Questions about memory, quotations,
// negations and arbitrary model output never select an operation.
export function parseMemoryCommand(message: string): MemoryCommand | undefined {
  const politeQuestion = /^(?:can|could|would|will) you\s+/i.test(message.trim());
  const text = message.trim().replace(/^(?:can|could|would|will) you\s+/i, "").replace(/^please\s+/i, "").replace(/[,\s]+please[.!?]*$/i, "");
  if (!politeQuestion && text.endsWith("?") && !/^remember\s*:/i.test(text)) return;
  const clean = text.replace(/[.!?]+$/, "").trim();
  const remember = /^remember(?:\s*:\s*|\s+)(.*)$/i.exec(politeQuestion ? text.replace(/\?$/, "") : text);
  if (remember) return { operation: "save", subject: remember[1].trim() };
  const save = /^(?:add|save|store)\s+(.+?)\s+(?:to|in|into)\s+(?:(?:my|your|our)\s+)?memory$/i.exec(clean)
    ?? /^(?:add|save|store)\s+(?:a\s+)?(?:new\s+)?memory\s*:\s*(.*)$/i.exec(clean);
  if (save) return { operation: "save", subject: save[1].trim() };
  const retire = /^(?:delete|remove)\s+(.+?)\s+from\s+(?:(?:my|your|our)\s+)?memory$/i.exec(clean)
    ?? /^(?:delete|remove)\s+(?:the\s+)?memory\s*:?\s+(.+)$/i.exec(clean)
    ?? /^forget\s+(.+?)(?:\s+from\s+(?:my\s+)?memory)?$/i.exec(clean);
  if (retire) return { operation: "retire", subject: retire[1].trim() };
}

export function isMemoryReference(subject: string) {
  return /^(?:this|that|it|the above|what I (?:just )?said|(?:this|that|the last|the previous) (?:fact|note|preference|memory|message))$/i.test(subject.replace(/[.!?]+$/, "").trim());
}

export function noteFromPreviousMessage(message?: string) {
  if (!message) return;
  const command = parseMemoryCommand(message);
  if (command) return command.operation === "save" && command.subject && !isMemoryReference(command.subject) ? command.subject : undefined;
  // "Add that" refers to the user's statement, never an unrelated generated
  // answer. If the prior message is a request/question, ask for the exact note.
  if (/[?]\s*$/.test(message) || /^(?:who|what|when|where|why|how|can|could|would|will|do|does|is|are|tell|show|give|draft|write|summari[sz]e|explain|delete|remove|forget|remember|add|save|store|please)\b/i.test(message)) return;
  return message;
}

const normalize = (text: string) => text.toLowerCase().replace(/[“”"'‘’`]/g, "").replace(/[^\p{L}\p{N}\s-]/gu, " ").replace(/\s+/g, " ").trim();

export function matchingMemories(subject: string, memories: BackendMemory[]) {
  const term = normalize(subject.replace(/^(?:memory|record)\s+(?:id\s+)?/i, ""));
  if (/^(?:all|everything|all memories|all my memories|my memories|every memory)$/.test(term)) return [];
  const byId = memories.filter((memory) => normalize(memory.id) === term);
  if (byId.length) return byId;
  const active = memories.filter((memory) => memory.status !== "retired");
  const exact = active.filter((memory) => normalize(memory.text) === term);
  if (exact.length) return exact;
  // Conservative text matching: no semantic guess and no broad one-word wipe.
  return term.length >= 8 ? active.filter((memory) => normalize(memory.text).includes(term)) : [];
}

export function chooseMemoryMessage(memories: BackendMemory[]) {
  return memories.length
    ? `Which memory should I remove?\n\n${memories.slice(0, 5).map((memory) => `- ${memory.id}: ${memory.text}`).join("\n")}\n\nReply with “delete memory” and its ID. Nothing has been removed.`
    : "Which memory should I remove? Quote its text or say “delete memory” followed by its ID. Nothing has been removed.";
}
