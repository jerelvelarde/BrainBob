import { AbstractAgent, EventType, type BaseEvent, type RunAgentInput } from "@copilotkit/react-core/v2";
import { Observable } from "rxjs";
import type { SessionFile } from "./session-memory";

/** The walkthrough can display its authored context; it never pretends to call an answer model. */
export class SessionDemoAgent extends AbstractAgent {
  constructor(private file: () => SessionFile) {
    super({ agentId: "brainbob", description: "Scripted session memory preview; no inference", threadId: "session-demo" });
  }
  run(input: RunAgentInput): Observable<BaseEvent> {
    return new Observable((observer) => {
      const file = this.file();
      const last = input.messages.filter((message) => message.role === "user").at(-1);
      const text = typeof last?.content === "string" ? last.content : "";
      const all = file.sections.flatMap((section) => section.records);
      const referenced = all.filter((record) => text.includes(`“${record.text}”`));
      const records = referenced.length ? referenced : all;
      const reply = `**Scripted memory preview** · ${file.member.name}\n\nHere’s the selected context from your session file:\n\n${records.map((record) => `- **${record.status === "active" ? "Current" : record.status}**: ${record.text} (source: ${record.sourceId})`).join("\n\n")}\n\nThis walkthrough shows saved context. Open the live workspace to ask the backend for a generated response.`;
      const messageId = crypto.randomUUID();
      observer.next({ type: EventType.RUN_STARTED, runId: input.runId, threadId: input.threadId });
      observer.next({ type: EventType.TEXT_MESSAGE_START, messageId, role: "assistant" });
      observer.next({ type: EventType.TEXT_MESSAGE_CONTENT, messageId, delta: reply });
      observer.next({ type: EventType.TEXT_MESSAGE_END, messageId });
      observer.next({ type: EventType.RUN_FINISHED, runId: input.runId, threadId: input.threadId });
      observer.complete();
    });
  }
}
