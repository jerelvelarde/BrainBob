import { AbstractAgent, EventType, type BaseEvent, type RunAgentInput } from "@copilotkit/react-core/v2";
import { Observable } from "rxjs";
import { brainApi, scopeLabel, type BackendAnswer } from "./brain-api";
import type { SessionActivity } from "./active-session";
import { memberForReader, teamForReader } from "./sample-company";
import { chooseMemoryMessage, isMemoryReference, matchingMemories, noteFromPreviousMessage, parseMemoryCommand } from "./chat-memory-commands";

export type ChatMode = "ask" | "remember" | "feedback" | "review";
export type ChatContext = { mode: ChatMode; reader: string; author: string; taskId?: string; readOnly: boolean };
export type AnswerReceipt = { messageId: string; requestId: string; question: string };
export const MEMORY_TOOL_NAME = "consult_memory";
export const SAVE_MEMORY_TOOL_NAME = "save_memory";
export const RETIRE_MEMORY_TOOL_NAME = "retire_memory";

export class BackendChatAgent extends AbstractAgent {
  // Only successful Ask turns enter follow-up context. Evaluation gold and write commands never do.
  private turns: { question: string; answer: string }[] = [];
  private identity?: string;
  private previousMessage?: string;
  private recentMemoryIds?: string[];
  constructor(private context: () => ChatContext, private answered: (answer: BackendAnswer, receipt: AnswerReceipt) => void, private failed: (error: string) => void, private sessionActivity?: (event: SessionActivity) => void) {
    super({ agentId: "brainbob", description: "BrainBob shared memory on Crusoe", threadId: "brainbob-chat" });
  }
  run(input: RunAgentInput): Observable<BaseEvent> {
    return new Observable((observer) => {
      const abort = new AbortController();
      let asking = false;
      let retrieval: { id: string; startedAt: number } | undefined;
      const finishAsk = (event: SessionActivity) => { asking = false; this.sessionActivity?.(event); };
      this.failed("");
      observer.next({ type: EventType.RUN_STARTED, runId: input.runId, threadId: input.threadId });
      const run = async () => {
        const context = this.context();
        if (context.readOnly) throw new Error("Return to live before sending a request.");
        const identity = `${context.reader}:${context.author}`;
        const switchedIdentity = this.identity !== undefined && this.identity !== identity;
        if (this.identity !== identity) {
          this.turns = []; this.previousMessage = undefined; this.recentMemoryIds = undefined;
          this.identity = identity;
        }
        const last = input.messages.filter((message) => message.role === "user").at(-1);
        const text = typeof last?.content === "string" ? last.content.trim() : "";
        if (!text) throw new Error("Enter a message first.");
        const messageId = crypto.randomUUID();
        let reply: string;
        const command = context.mode === "ask" ? parseMemoryCommand(text) : undefined;
        const priorUser = input.messages.filter((message) => message.role === "user").at(-2);
        const previous = this.previousMessage ?? (!switchedIdentity && typeof priorUser?.content === "string" ? priorUser.content : undefined);
        if (context.mode === "ask") this.previousMessage = text;
        if (command?.operation === "save") {
          const personalMemory = isMemoryReference(command.subject) ? noteFromPreviousMessage(previous) : command.subject;
          this.recentMemoryIds = [];
          if (!personalMemory) {
            reply = "What would you like me to remember? Tell me the exact fact or preference, and I’ll save it to your personal memory.";
          } else {
          retrieval = { id: crypto.randomUUID(), startedAt: Date.now() };
          observer.next({ type: EventType.TOOL_CALL_START, toolCallId: retrieval.id, toolCallName: SAVE_MEMORY_TOOL_NAME, parentMessageId: crypto.randomUUID() });
          observer.next({ type: EventType.TOOL_CALL_ARGS, toolCallId: retrieval.id, delta: JSON.stringify({ requestId: input.runId, question: text, startedAt: retrieval.startedAt, operation: "save" }) });
          observer.next({ type: EventType.TOOL_CALL_END, toolCallId: retrieval.id });
          const saved = await brainApi.rememberPersonal(personalMemory, context.reader, context.author, abort.signal);
          if (abort.signal.aborted) return;
          const decisions = saved.memories.map((m) => "action" in m
            ? { memoryId: m.memory_id, action: m.action, text: m.text, reason: m.reason }
            : { memoryId: m.id, action: m.status === "tentative" ? "tentative" : "add", text: m.text, reason: m.reason });
          this.recentMemoryIds = decisions.filter((d) => d.action !== "reject" && d.memoryId).map((d) => d.memoryId!);
          this.previousMessage = personalMemory;
          const labels: Record<string, string> = { add: "Saved", supersede: "Updated", tentative: "Kept for review", reject: "Not saved" };
          reply = decisions.length ? decisions.map((d) => `${labels[d.action]}: ${d.text || d.reason}${d.action === "tentative" || d.action === "reject" ? ` (${d.reason})` : ""}`).join("\n\n") : "I checked that note, but no new memory was saved.";
          observer.next({ type: EventType.TOOL_CALL_RESULT, toolCallId: retrieval.id, messageId: crypto.randomUUID(), role: "tool", content: JSON.stringify({ elapsedMs: Date.now() - retrieval.startedAt, decisions, episodeId: saved.episode_id }) });
          }
        } else if (command?.operation === "retire") {
          retrieval = { id: crypto.randomUUID(), startedAt: Date.now() };
          observer.next({ type: EventType.TOOL_CALL_START, toolCallId: retrieval.id, toolCallName: RETIRE_MEMORY_TOOL_NAME, parentMessageId: crypto.randomUUID() });
          observer.next({ type: EventType.TOOL_CALL_ARGS, toolCallId: retrieval.id, delta: JSON.stringify({ requestId: input.runId, question: text, startedAt: retrieval.startedAt, operation: "retire" }) });
          observer.next({ type: EventType.TOOL_CALL_END, toolCallId: retrieval.id });
          // Re-read visible records before any mutation; references never bypass ACL
          // or follow a supersedes chain into a different, newly created memory.
          const memories = await brainApi.memories(context.author, abort.signal);
          if (abort.signal.aborted) return;
          const reference = isMemoryReference(command.subject);
          const recentIds = this.recentMemoryIds;
          const candidates = reference && recentIds !== undefined
            ? memories.filter((memory) => recentIds.includes(memory.id))
            : matchingMemories(reference ? noteFromPreviousMessage(previous) ?? "" : command.subject, memories);
          if (candidates.length !== 1 || (reference && (recentIds?.length ?? 0) > 1)) {
            reply = chooseMemoryMessage(candidates);
            observer.next({ type: EventType.TOOL_CALL_RESULT, toolCallId: retrieval.id, messageId: crypto.randomUUID(), role: "tool", content: JSON.stringify({ elapsedMs: Date.now() - retrieval.startedAt, clarification: reply }) });
          } else {
            const target = candidates[0];
            const retired = target.status === "retired" ? target : (await brainApi.retire(target.id, "Removed at the member’s request in chat", context.author, abort.signal)).memory;
            if (abort.signal.aborted) return;
            if (retired.id !== target.id || retired.status !== "retired") throw new Error("The backend did not confirm this memory was removed. Check its current status before retrying.");
            this.recentMemoryIds = [retired.id];
            const alreadyRemoved = target.status === "retired";
            reply = `${alreadyRemoved ? "Already removed from active memory" : "Removed from active memory"}: ${retired.text}\n\nIts history is kept for retracing.`;
            observer.next({ type: EventType.TOOL_CALL_RESULT, toolCallId: retrieval.id, messageId: crypto.randomUUID(), role: "tool", content: JSON.stringify({ elapsedMs: Date.now() - retrieval.startedAt, decisions: [{ memoryId: retired.id, action: alreadyRemoved ? "already_retired" : "retire", text: retired.text, reason: retired.reason }] }) });
          }
        } else {
        switch (context.mode) {
          case "ask": {
            this.recentMemoryIds = [];
            asking = true;
            this.sessionActivity?.({ type: "started", requestId: input.runId, question: text });
            retrieval = { id: crypto.randomUUID(), startedAt: Date.now() };
            // /ask performs retrieval and answering together. Expose that real request,
            // not a simulated chain of model reasoning or separately timed retrieval.
            observer.next({ type: EventType.TOOL_CALL_START, toolCallId: retrieval.id, toolCallName: MEMORY_TOOL_NAME, parentMessageId: crypto.randomUUID() });
            observer.next({ type: EventType.TOOL_CALL_ARGS, toolCallId: retrieval.id, delta: JSON.stringify({ requestId: input.runId, question: text, startedAt: retrieval.startedAt }) });
            observer.next({ type: EventType.TOOL_CALL_END, toolCallId: retrieval.id });
            const person = memberForReader(context.reader);
            const history = this.turns.slice(-4).map((turn) => `User: ${turn.question.slice(0, 2000)}\nAssistant: ${turn.answer.slice(0, 4000)}`).join("\n\n");
            const question = `Requester: ${person?.label ?? "this member"} (${teamForReader(context.reader)?.label ?? "their team"}, Rusty Rod). The requester is not necessarily the person asked about. Complete the requested work directly. When asked to draft a message, write the actual message in the requester's voice, starting with a greeting to its recipient. When asked for a plan or agenda, produce the plan or agenda itself. Use saved preferences where relevant. Ground factual claims in current accessible memory. Keep tentative information separate from approved facts and ask for missing details instead of inventing them. Use short paragraphs or a concise list when helpful; do not dump all retrieved context into the answer. Keep memory IDs and internal storage terminology out of the prose; put citation IDs only in the required final CITED line. Drafts are for review; do not claim to have sent messages or completed external actions.\n${history ? `\nPrevious conversation (reference only, not verified facts; current memory takes precedence):\n${history}\n` : ""}\nCurrent request: ${text}`;
            const answer = await brainApi.ask(question, context.reader, abort.signal);
            if (abort.signal.aborted) return;
            if (!answer.answer.trim()) throw new Error("The inference provider returned no answer. Check the Crusoe connection and retry.");
            this.recentMemoryIds = noteFromPreviousMessage(text) ? undefined : answer.memories.filter((memory) => answer.cited_ids.includes(memory.id)).map((memory) => memory.id);
            this.turns.push({ question: text, answer: answer.answer });
            this.turns = this.turns.slice(-4);
            finishAsk({ type: "answered", requestId: input.runId, answer });
            this.answered(answer, { messageId, requestId: input.runId, question: text });
            observer.next({ type: EventType.TOOL_CALL_RESULT, toolCallId: retrieval.id, messageId: crypto.randomUUID(), role: "tool", content: JSON.stringify({ messageId, elapsedMs: Date.now() - retrieval.startedAt }) });
            reply = answer.answer;
            break;
          }
          case "remember": {
            const saved = await brainApi.remember(text, context.reader, context.author, abort.signal);
            reply = saved.memories.length ? `Conversation processed for ${scopeLabel(context.reader)}:\n\n${saved.memories.map((m) => "action" in m ? `- ${m.action}: ${m.text || m.reason} (${m.reason})` : `- Stored: ${m.text}`).join("\n")}` : "The conversation was received; no new memories were stored.";
            break;
          }
          case "feedback": {
            if (!context.taskId) throw new Error("Ask a question first, then supply its correct answer in Usefulness mode.");
            const result = await brainApi.feedback(context.taskId, text, context.author, abort.signal);
            const ids = new Set(result.evidence.map((e) => e.memory_id));
            reply = ids.size ? `The cited-memory check recorded correctness flips for ${ids.size} ${ids.size === 1 ? "memory" : "memories"}. Review can now assess the accumulated evidence.` : "The cited-memory check finished with no new correctness-flip evidence.";
            break;
          }
          case "review": {
            const result = await brainApi.review(context.author, abort.signal);
            reply = result.decisions.length ? result.decisions.map((d) => `- ${d.action}: ${d.reason}`).join("\n") : "Review finished. No memories changed status.";
            break;
          }
        }
        }
        if (observer.closed) return;
        observer.next({ type: EventType.TEXT_MESSAGE_START, messageId, role: "assistant" });
        observer.next({ type: EventType.TEXT_MESSAGE_CONTENT, messageId, delta: reply });
        observer.next({ type: EventType.TEXT_MESSAGE_END, messageId });
        observer.next({ type: EventType.RUN_FINISHED, runId: input.runId, threadId: input.threadId });
        observer.complete();
      };
      void run().catch((err) => {
        if (observer.closed) return;
        const message = err instanceof Error ? err.message : "The backend request failed.";
        if (asking) finishAsk({ type: "failed", requestId: input.runId, error: message });
        if (retrieval) observer.next({ type: EventType.TOOL_CALL_RESULT, toolCallId: retrieval.id, messageId: crypto.randomUUID(), role: "tool", content: JSON.stringify({ error: message, elapsedMs: Date.now() - retrieval.startedAt }) });
        this.failed(message);
        observer.next({ type: EventType.RUN_ERROR, message }); observer.complete();
      });
      return () => { abort.abort(); if (asking) finishAsk({ type: "cancelled", requestId: input.runId }); };
    });
  }
}
