"use client";

import { createContext, useContext, type ComponentProps } from "react";
import { CopilotChatAssistantMessage } from "@copilotkit/react-core/v2";
import { Brain, FileText } from "lucide-react";
import type { ActiveSession, SessionActivity } from "@/lib/active-session";

export const SessionReceiptsContext = createContext<{
  receipts: Record<string, ActiveSession>;
  activity: Record<string, { event: SessionActivity; at: number }>;
  onInspect: (id: string) => void;
  onExplore: (session: ActiveSession) => void;
}>({ receipts: {}, activity: {}, onInspect: () => {}, onExplore: () => {} });

/** Keep evidence attached to the reply that used it, even after follow-up questions. */
export const SessionAssistantMessage = Object.assign(function SessionAssistantMessage(props: ComponentProps<typeof CopilotChatAssistantMessage>) {
  const { receipts, onExplore, onInspect } = useContext(SessionReceiptsContext);
  const receipt = receipts[props.message.id];
  const sources = receipt?.memories.filter((memory) => receipt.citedIds.includes(memory.id)) ?? [];
  return <><CopilotChatAssistantMessage {...props} toolbarVisible={Boolean(props.message.content)} additionalToolbarItems={receipt ?
    <button className="reply-memory" onClick={() => onExplore(receipt)} aria-label={`Explore memory for: ${receipt.question}`}>
      <Brain size={14} /><span>{receipt.citedIds.length ? `${receipt.citedIds.length} ${receipt.citedIds.length === 1 ? "memory" : "memories"} used` : "Memory details"}</span>
    </button> : null} />
    {sources.length ? <div className="inline-memory-sources" aria-label="Sources for this reply">{sources.slice(0, 3).map((memory, index) =>
      <button key={memory.id} onClick={() => onInspect(memory.id)} title={memory.text}><FileText size={12} /><span>{index + 1}. {memory.text}</span></button>
    )}</div> : null}
  </>;
}, CopilotChatAssistantMessage);
