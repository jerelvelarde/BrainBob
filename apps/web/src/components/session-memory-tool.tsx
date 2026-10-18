"use client";

import { useContext, useEffect, useState, type ComponentProps } from "react";
import { defineToolCallRenderer } from "@copilotkit/react-core/v2";
import { Brain, Check, ChevronRight, FileText, LoaderCircle } from "lucide-react";
import { z } from "zod";
import { MEMORY_TOOL_NAME, SAVE_MEMORY_TOOL_NAME, CORRECT_MEMORY_TOOL_NAME, RETIRE_MEMORY_TOOL_NAME, CONVERSATION_TOOL_NAME } from "@/lib/backend-chat-agent";
import { SessionReceiptsContext } from "./session-chat-message";

const argsSchema = z.object({ requestId: z.string(), question: z.string(), startedAt: z.number(), operation: z.enum(["save", "correct", "retire", "plan"]).optional() });
const resultSchema = z.object({ messageId: z.string().optional(), elapsedMs: z.number(), error: z.string().optional(), clarification: z.string().optional(), summary: z.string().optional(), model: z.string().optional(), decisions: z.array(z.object({ memoryId: z.string().nullable(), action: z.string(), text: z.string(), reason: z.string() })).optional() });
function parseResult(result?: string) {
  if (!result) return undefined;
  try { const parsed = resultSchema.safeParse(JSON.parse(result)); return parsed.success ? parsed.data : undefined; }
  catch { return undefined; }
}

function MemoryTool({ args, result }: { args: Partial<z.infer<typeof argsSchema>>; result?: string }) {
  const { receipts, activity, onExplore, onInspect } = useContext(SessionReceiptsContext);
  const progress = args.requestId ? activity[args.requestId] : undefined;
  const completed = parseResult(result);
  const snapshot = completed?.messageId ? receipts[completed.messageId] : undefined;
  const correcting = args.operation === "correct";
  const saving = args.operation === "save";
  const retiring = args.operation === "retire";
  const planning = args.operation === "plan";
  const checked = completed?.decisions;
  const running = !completed && (!progress || progress.event.type === "started");
  const failed = Boolean(completed?.error) || progress?.event.type === "failed";
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [running]);
  const seconds = Math.max(0, Math.round((completed?.elapsedMs ?? ((running ? now : progress?.at ?? now) - (args.startedAt ?? now))) / 1000));
  const elapsed = seconds >= 60 ? `${Math.floor(seconds / 60)}m ${seconds % 60}s` : `${seconds}s`;
  return <details className="memory-tool">
    <summary><span>{running ? `Working${seconds ? ` for ${elapsed}` : "…"}` : failed ? "Couldn’t complete this request" : completed?.clarification ? "Choose a memory" : completed?.summary ? "Understood your request" : snapshot || checked ? `Worked for ${elapsed}` : "Stopped"}</span><ChevronRight size={14} /></summary>
    <div className="memory-tool-body">
      <div className="memory-tool-step">{running ? <LoaderCircle size={15} className="memory-tool-spinner" /> : snapshot || checked || completed?.summary ? <Check size={15} /> : <Brain size={15} />}<strong>{running ? planning ? "Understanding your message" : correcting ? "Updating the existing memory" : saving ? "Checking your memory update" : retiring ? "Removing from active memory" : "Consulting your shared brain" : completed?.summary ?? (completed?.clarification ? "Nothing removed" : checked ? retiring ? "Memory removed" : "Memory check complete" : snapshot ? "Consulted your shared brain" : "Memory request interrupted")}</strong></div>
      <p>{snapshot ? `${snapshot.memories.length} memories returned · ${snapshot.citedIds.length} cited in this reply` : failed ? completed?.error ?? "The request failed. Try again when the service is available." : completed?.summary ? `Model: ${completed.model ?? "Nemotron"}` : completed?.clarification ? "Tell me which record you mean using its text or ID." : running ? planning ? "Reading the conversation and choosing the next step." : correcting ? "Replacing the requested detail while keeping the original scope and history." : saving ? "Extracting your note and comparing it with saved facts." : retiring ? "Finding the matching record and checking permission to remove it." : "Finding relevant context and preparing your reply." : checked ? retiring ? "Removed from active use. Source and history remain available." : "The backend checked the note against existing memories and permissions." : "No completed answer was returned."}</p>
      {checked ? <div className="tool-source-list">{checked.map((decision, index) => decision.memoryId ? <button key={`${decision.memoryId}-${index}`} onClick={() => onInspect(decision.memoryId!)}><FileText size={13} /><span>{decision.text} · {decision.action === "retire" || decision.action === "already_retired" ? "Removed" : decision.action === "supersede" ? "Updated" : decision.action === "add" ? "Saved" : decision.action === "tentative" ? "Needs review" : "Not saved"}</span></button> : <p key={index}>{decision.reason}</p>)}</div> : null}
      {snapshot ? <>
        <div className="tool-source-list">{snapshot.memories.filter((memory) => snapshot.citedIds.includes(memory.id)).slice(0, 3).map((memory) => <button key={memory.id} onClick={() => onInspect(memory.id)}><FileText size={13} /><span>{memory.text}</span></button>)}</div>
        <button className="tool-explore" onClick={() => onExplore(snapshot)}>Explore memory <ChevronRight size={13} /></button>
      </> : null}
    </div>
  </details>;
}

export const memoryToolRenderer = defineToolCallRenderer({ name: MEMORY_TOOL_NAME, agentId: "brainbob", args: argsSchema,
  render: (props: ComponentProps<typeof MemoryTool>) => <MemoryTool {...props} />,
});
export const saveMemoryToolRenderer = defineToolCallRenderer({ name: SAVE_MEMORY_TOOL_NAME, agentId: "brainbob", args: argsSchema,
  render: (props: ComponentProps<typeof MemoryTool>) => <MemoryTool {...props} />,
});
export const correctMemoryToolRenderer = defineToolCallRenderer({ name: CORRECT_MEMORY_TOOL_NAME, agentId: "brainbob", args: argsSchema,
  render: (props: ComponentProps<typeof MemoryTool>) => <MemoryTool {...props} />,
});
export const retireMemoryToolRenderer = defineToolCallRenderer({ name: RETIRE_MEMORY_TOOL_NAME, agentId: "brainbob", args: argsSchema,
  render: (props: ComponentProps<typeof MemoryTool>) => <MemoryTool {...props} />,
});
export const conversationToolRenderer = defineToolCallRenderer({ name: CONVERSATION_TOOL_NAME, agentId: "brainbob", args: argsSchema,
  render: (props: ComponentProps<typeof MemoryTool>) => <MemoryTool {...props} />,
});
