import { AbstractAgent, EventType, type BaseEvent, type RunAgentInput } from "@copilotkit/react-core/v2";
import { Observable } from "rxjs";
import { brainApi, scopeLabel, type BackendAnswer } from "./brain-api";
import type { SessionActivity } from "./active-session";

export type ChatMode = "ask" | "remember" | "feedback" | "review";
export type ChatContext = { mode: ChatMode; reader: string; author: string; taskId?: string; readOnly: boolean };

export class BackendChatAgent extends AbstractAgent {
  constructor(private context: () => ChatContext, private answered: (answer: BackendAnswer) => void, private failed: (error: string) => void, private sessionActivity?: (event: SessionActivity) => void) {
    super({ agentId: "brainbob", description: "BrainBob shared memory on Crusoe", threadId: "brainbob-chat" });
  }
  run(input: RunAgentInput): Observable<BaseEvent> {
    return new Observable((observer) => {
      const abort = new AbortController();
      let asking = false;
      const finishAsk = (event: SessionActivity) => { asking = false; this.sessionActivity?.(event); };
      this.failed("");
      observer.next({ type: EventType.RUN_STARTED, runId: input.runId, threadId: input.threadId });
      const run = async () => {
        const context = this.context();
        if (context.readOnly) throw new Error("Return to live before sending a request.");
        const last = input.messages.filter((message) => message.role === "user").at(-1);
        const text = typeof last?.content === "string" ? last.content.trim() : "";
        if (!text) throw new Error("Enter a message first.");
        let reply: string;
        switch (context.mode) {
          case "ask": {
            asking = true;
            this.sessionActivity?.({ type: "started", requestId: input.runId, question: text });
            const answer = await brainApi.ask(text, context.reader, abort.signal);
            if (abort.signal.aborted) return;
            finishAsk({ type: "answered", requestId: input.runId, answer });
            this.answered(answer);
            reply = answer.answer || "The backend returned an empty answer.";
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
        if (observer.closed) return;
        const messageId = crypto.randomUUID();
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
        this.failed(message);
        observer.next({ type: EventType.RUN_ERROR, message }); observer.complete();
      });
      return () => { abort.abort(); if (asking) finishAsk({ type: "cancelled", requestId: input.runId }); };
    });
  }
}
