"use client";

import { useEffect, useRef, useState } from "react";
import { CopilotChat, CopilotKitProvider } from "@copilotkit/react-core/v2";
import { BackendChatAgent, type ChatContext, type ChatMode } from "@/lib/backend-chat-agent";
import { scopeLabel, type BackendAnswer, type BackendMemory } from "@/lib/brain-api";

const modes = { ask: "Ask", remember: "Remember", feedback: "Check", review: "Review" };
const placeholders = { ask: "Ask the shared brain…", remember: "Paste a conversation to remember…", feedback: "Give the correct answer to your last question…", review: "Send ‘review’ to assess accumulated evidence…" };
const HiddenControl = () => null;

export default function SceneChat({ reader, readOnly, memories, onAnswer, onInspect }: {
  reader: string; readOnly: boolean; memories: Record<string, BackendMemory>;
  onAnswer: (answer: BackendAnswer) => void; onInspect: (id: string) => void;
}) {
  const [mode, setMode] = useState<ChatMode>("ask");
  const [answer, setAnswer] = useState<BackendAnswer>();
  const [error, setError] = useState("");
  const context = useRef<ChatContext>({ mode, reader, author: scopeLabel(reader), readOnly });
  const callbacks = useRef({ onAnswer });
  useEffect(() => { callbacks.current = { onAnswer }; }, [onAnswer]);
  useEffect(() => { context.current = { mode, reader, author: scopeLabel(reader), readOnly, taskId: answer?.task_id }; }, [mode, reader, readOnly, answer]);
  const [agent] = useState(() => new BackendChatAgent(() => context.current, (result) => { setAnswer(result); callbacks.current.onAnswer(result); }, setError));
  const [agents] = useState(() => ({ brainbob: agent }));
  return <>
    <div className="chat-modes" aria-label="Chat operation">{(Object.keys(modes) as ChatMode[]).map((value) => <button key={value} aria-pressed={mode === value} disabled={readOnly} onClick={() => { setMode(value); setError(""); }}>{modes[value]}</button>)}</div>
    {mode === "feedback" ? <p className="chat-context">{answer ? "Check the cited memories using the correct answer to your last question. Feedback is not stored as memory." : "Ask a question first to create a task to check."}</p> : null}
    {mode === "remember" ? <p className="chat-context">Store in {scopeLabel(reader)}.</p> : null}
    {readOnly ? <p className="chat-context">Retracing · return to live to send requests.</p> : null}
    {error ? <p className="backend-error" role="alert">{error}</p> : null}
    <CopilotKitProvider selfManagedAgents={agents} agentId="brainbob" showDevConsole={false} enableInspector={false}>
      <CopilotChat className="scene-copilot" agentId="brainbob" input={{ addMenuButton: HiddenControl, startTranscribeButton: HiddenControl, textArea: { disabled: readOnly }, sendButton: { disabled: readOnly } }} labels={{ welcomeMessageText: "What should we remember?", chatInputPlaceholder: placeholders[mode], chatDisclaimerText: "Shared memory · backend responses" }} />
    </CopilotKitProvider>
    {answer ? <div className="answer-citations"><small>Sources for your last answer</small>{answer.cited_ids.length ? answer.cited_ids.map((id) => <button key={id} onClick={() => onInspect(id)}>{(memories[id]?.text ?? answer.memories.find((m) => m.id === id)?.text ?? id).slice(0, 90)}</button>) : <span>No memories cited.</span>}</div> : null}
  </>;
}
