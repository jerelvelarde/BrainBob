"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { CopilotChat, CopilotKitProvider } from "@copilotkit/react-core/v2";
import { BackendChatAgent, type ChatContext } from "@/lib/backend-chat-agent";
import type { BackendAnswer, BackendMemory } from "@/lib/brain-api";
import { memberForReader, memberId } from "@/lib/sample-company";
import { updateActiveSession, type ActiveSession, type SessionActivity } from "@/lib/active-session";
import { sessionPrompts } from "@/lib/session-prompts";
import { ConfigureSessionPrompts, SessionPromptCards, SessionSendButton, SessionWelcome, SessionWelcomeContext } from "./session-chat-welcome";
import { memoryToolRenderer, saveMemoryToolRenderer, retireMemoryToolRenderer, conversationToolRenderer } from "./session-memory-tool";
import { SessionAssistantMessage, SessionReceiptsContext } from "./session-chat-message";

const toolRenderers = [memoryToolRenderer, saveMemoryToolRenderer, retireMemoryToolRenderer, conversationToolRenderer];
const HiddenControl = () => null;

export default function SceneChat({ reader, readOnly, memories, onAnswer, onExploreMemory, onInspect, onSessionActivity, connected }: {
  reader: string; readOnly: boolean; memories: Record<string, BackendMemory>;
  onAnswer: (answer: BackendAnswer) => void; onExploreMemory: (session: ActiveSession) => void; onInspect: (id: string) => void;
  onSessionActivity: (event: SessionActivity) => void;
  connected: boolean;
}) {
  const [receipts, setReceipts] = useState<Record<string, ActiveSession>>({});
  const [activity, setActivity] = useState<Record<string, { event: SessionActivity; at: number }>>({});
  const [error, setError] = useState("");
  const memoryVersion = useMemo(() => Object.values(memories).map((memory) => `${memory.id}:${memory.status}:${memory.text}`).sort().join("\n"), [memories]);
  const context = useRef<ChatContext>({ mode: "ask", reader, author: memberId(reader), readOnly, memoryVersion, conversational: true });
  const callbacks = useRef({ onAnswer, onSessionActivity });
  useEffect(() => { callbacks.current = { onAnswer, onSessionActivity }; }, [onAnswer, onSessionActivity]);
  useEffect(() => { context.current = { mode: "ask", reader, author: memberId(reader), readOnly, memoryVersion, conversational: true }; }, [reader, readOnly, memoryVersion]);
  const [agent] = useState(() => new BackendChatAgent(() => context.current, (result, receipt) => {
    const started = updateActiveSession(null, { type: "started", requestId: receipt.requestId, question: receipt.question }, context.current.reader);
    const snapshot = updateActiveSession(started, { type: "answered", requestId: receipt.requestId, answer: result }, context.current.reader);
    if (snapshot) setReceipts((current) => ({ ...current, [receipt.messageId]: snapshot }));
    callbacks.current.onAnswer(result);
  }, setError, (event) => { setActivity((current) => ({ ...current, [event.requestId]: { event, at: Date.now() } })); callbacks.current.onSessionActivity(event); }));
  const [agents] = useState(() => ({ brainbob: agent }));
  const prompts = useMemo(() => sessionPrompts(Object.values(memories), reader), [memories, reader]);
  const welcome = useMemo(() => ({ name: memberForReader(reader)?.label.split(" ")[0] ?? "there", prompts, disabled: readOnly || !connected }), [reader, prompts, readOnly, connected]);
  const evidence = useMemo(() => ({ receipts, activity, onInspect, onExplore: onExploreMemory }), [receipts, activity, onInspect, onExploreMemory]);
  return <>
    {readOnly ? <p className="chat-context">Retracing · return to live to send messages.</p> : !connected ? <p className="chat-context" role="status">Reconnecting to your shared brain…</p> : null}
    {error ? <p className="backend-error" role="alert">{error}</p> : null}
    <CopilotKitProvider selfManagedAgents={agents} renderToolCalls={toolRenderers} agentId="brainbob" showDevConsole={false} enableInspector={false}>
      <SessionWelcomeContext.Provider value={welcome}>
        <SessionReceiptsContext.Provider value={evidence}>
          <ConfigureSessionPrompts prompts={prompts} enabled={!readOnly} />
          <CopilotChat className="scene-copilot session-copilot" agentId="brainbob" welcomeScreen={SessionWelcome} suggestionView={SessionPromptCards}
            messageView={{ assistantMessage: SessionAssistantMessage, userMessage: { messageRenderer: { className: "session-user-bubble" } } }}
            input={{ addMenuButton: HiddenControl, startTranscribeButton: HiddenControl, disclaimer: HiddenControl, autoFocus: false, textArea: { disabled: welcome.disabled, "aria-label": "Message Bob" }, sendButton: SessionSendButton }}
            labels={{ chatInputPlaceholder: "Message BrainBob…" }} />
        </SessionReceiptsContext.Provider>
      </SessionWelcomeContext.Provider>
    </CopilotKitProvider>
  </>;
}
