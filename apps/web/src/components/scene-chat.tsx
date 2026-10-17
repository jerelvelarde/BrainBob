"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { CopilotChat, CopilotKitProvider } from "@copilotkit/react-core/v2";
import { BackendChatAgent, type ChatContext, type ChatMode } from "@/lib/backend-chat-agent";
import { scopeLabel, type BackendAnswer, type BackendMemory } from "@/lib/brain-api";
import { memberForReader, memberId } from "@/lib/sample-company";
import type { SessionActivity } from "@/lib/active-session";
import type { SessionFile } from "@/lib/session-memory";
import { sessionPrompts } from "@/lib/session-prompts";
import { SessionDemoAgent } from "@/lib/session-demo-agent";
import { ConfigureSessionPrompts, SessionPromptCards, SessionSendButton, SessionWelcome, SessionWelcomeContext } from "./session-chat-welcome";

const modes = { ask: "Ask", remember: "Remember", feedback: "Usefulness", review: "Review" };
const placeholders = { ask: "Ask the shared brain…", remember: "Paste a conversation to remember…", feedback: "Give the correct answer to your last question…", review: "Send ‘review’ to assess accumulated evidence…" };
const HiddenControl = () => null;

export default function SceneChat({ reader, readOnly, memories, onAnswer, onInspect, onSessionActivity, previewFile }: {
  reader: string; readOnly: boolean; memories: Record<string, BackendMemory>;
  onAnswer: (answer: BackendAnswer) => void; onInspect: (id: string) => void;
  onSessionActivity: (event: SessionActivity) => void;
  previewFile?: SessionFile;
}) {
  const [mode, setMode] = useState<ChatMode>("ask");
  const [answer, setAnswer] = useState<BackendAnswer>();
  const [error, setError] = useState("");
  const context = useRef<ChatContext>({ mode, reader, author: memberId(reader), readOnly });
  const preview = useRef(previewFile);
  useEffect(() => { preview.current = previewFile; }, [previewFile]);
  const callbacks = useRef({ onAnswer, onSessionActivity });
  useEffect(() => { callbacks.current = { onAnswer, onSessionActivity }; }, [onAnswer, onSessionActivity]);
  useEffect(() => { context.current = { mode, reader, author: memberId(reader), readOnly, taskId: answer?.task_id }; }, [mode, reader, readOnly, answer]);
  const [agent] = useState(() => previewFile ? new SessionDemoAgent(() => preview.current!) : new BackendChatAgent(() => context.current, (result) => { setAnswer(result); callbacks.current.onAnswer(result); }, setError, (event) => callbacks.current.onSessionActivity(event)));
  const [agents] = useState(() => ({ brainbob: agent }));
  const prompts = useMemo(() => sessionPrompts(previewFile ? previewFile.sections.flatMap((section) => section.records) : Object.values(memories), reader), [previewFile, memories, reader]);
  const welcome = useMemo(() => ({ name: memberForReader(reader)?.label.split(" ")[0] ?? "there", prompts, disabled: readOnly }), [reader, prompts, readOnly]);
  return <>
    {!previewFile ? <div className="chat-modes" aria-label="Chat operation">{(Object.keys(modes) as ChatMode[]).map((value) => <button key={value} aria-pressed={mode === value} disabled={readOnly} onClick={() => { setMode(value); setError(""); }}>{modes[value]}</button>)}</div> : null}
    {mode === "feedback" ? <p className="chat-context">{answer ? "Leave-one-out usefulness check on the cited memories. A helpful memory is not necessarily factual. The correct answer is feedback, not memory." : "Ask a question first to create a task to check."}</p> : null}
    {mode === "remember" ? <p className="chat-context">Store in {scopeLabel(reader)}.</p> : null}
    {readOnly ? <p className="chat-context">Retracing · return to live to send requests.</p> : null}
    {error ? <p className="backend-error" role="alert">{error}</p> : null}
    <CopilotKitProvider selfManagedAgents={agents} agentId="brainbob" showDevConsole={false} enableInspector={false}>
      <SessionWelcomeContext.Provider value={welcome}>
        <ConfigureSessionPrompts prompts={prompts} enabled={mode === "ask" && !readOnly} />
        <CopilotChat className="scene-copilot session-copilot" agentId="brainbob" welcomeScreen={SessionWelcome} suggestionView={SessionPromptCards}
          input={{ addMenuButton: HiddenControl, startTranscribeButton: HiddenControl, autoFocus: false, textArea: { disabled: readOnly, "aria-label": "Message Bob" }, sendButton: SessionSendButton }}
          labels={{ chatInputPlaceholder: mode === "ask" ? `What are we working on, ${welcome.name}?` : placeholders[mode], chatDisclaimerText: previewFile ? "Scripted memory preview · no inference" : "Your memory, your team, your shared brain." }} />
      </SessionWelcomeContext.Provider>
    </CopilotKitProvider>
    {answer ? <div className="answer-citations"><small>Sources for your last answer</small>{answer.cited_ids.length ? answer.cited_ids.map((id) => <button key={id} onClick={() => onInspect(id)}>{(memories[id]?.text ?? answer.memories.find((m) => m.id === id)?.text ?? id).slice(0, 90)}</button>) : <span>No memories cited.</span>}</div> : null}
  </>;
}
