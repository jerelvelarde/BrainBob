"use client";

import { useMemo } from "react";
import { Observable } from "rxjs";
import { AbstractAgent, CopilotChat, CopilotKitProvider, EventType, type BaseEvent, type RunAgentInput } from "@copilotkit/react-core/v2";
import "@copilotkit/react-core/v2/styles.css";
import type { MemoryAction, MemoryEvent } from "@/lib/memory";

class ScenePreviewAgent extends AbstractAgent {
  constructor(private perform: (action: MemoryAction) => MemoryEvent | string) {
    super({ agentId: "brainbob-preview", description: "Scripted scene controls. No model inference.", threadId: "scene-preview" });
  }
  run(input: RunAgentInput): Observable<BaseEvent> {
    return new Observable((observer) => {
      observer.next({ type: EventType.RUN_STARTED, runId: input.runId, threadId: input.threadId });
      const last = input.messages.filter((m) => m.role === "user").at(-1);
      const text = typeof last?.content === "string" ? last.content.toLowerCase() : "";
      const action: MemoryAction | undefined = /forget|archive/.test(text) ? "forgotten"
        : /update|correct|change/.test(text) ? "updated" : /check|audit|evaluat/.test(text) ? "evaluated"
        : /retrieve|recall|find/.test(text) ? "retrieved" : /create|remember|new memory/.test(text) ? "created" : undefined;
      let reply = "I'm the scene preview controller. Try “remember a new idea”, “retrieve this memory”, “check this memory”, “update this memory”, or “archive this memory”. These are scripted controls; NemoClaw and Crusoe inference are not connected yet.";
      if (action) {
        const result = this.perform(action);
        if (typeof result === "string") reply = result;
        else {
          observer.next({ type: EventType.CUSTOM, name: "brain.event", value: result });
          reply = `${result.explanation} Open the memory inspector to see the evidence and retrace this change. (Scripted preview.)`;
        }
      }
      const messageId = crypto.randomUUID();
      observer.next({ type: EventType.TEXT_MESSAGE_START, messageId, role: "assistant" });
      observer.next({ type: EventType.TEXT_MESSAGE_CONTENT, messageId, delta: reply });
      observer.next({ type: EventType.TEXT_MESSAGE_END, messageId });
      observer.next({ type: EventType.RUN_FINISHED, runId: input.runId, threadId: input.threadId });
      observer.complete();
    });
  }
}

export default function SceneChat({ onAction }: { onAction: (action: MemoryAction) => MemoryEvent | string }) {
  const agent = useMemo(() => new ScenePreviewAgent(onAction), [onAction]);
  const agents = useMemo(() => ({ "brainbob-preview": agent }), [agent]);
  return <CopilotKitProvider selfManagedAgents={agents} agentId="brainbob-preview" showDevConsole={false} enableInspector={false}>
    <CopilotChat className="scene-copilot" agentId="brainbob-preview" labels={{
      welcomeMessageText: "A penny for your thoughts?",
      chatInputPlaceholder: "Try ‘retrieve this memory’…",
      chatDisclaimerText: "Scripted scene controls · no model inference",
    }} />
  </CopilotKitProvider>;
}
