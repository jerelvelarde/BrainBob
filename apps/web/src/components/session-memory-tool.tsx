"use client";

import { useContext, useEffect, useState, type ComponentProps } from "react";
import { defineToolCallRenderer } from "@copilotkit/react-core/v2";
import { Brain, Check, ChevronRight, FileText, LoaderCircle } from "lucide-react";
import { z } from "zod";
import { MEMORY_TOOL_NAME } from "@/lib/backend-chat-agent";
import { SessionReceiptsContext } from "./session-chat-message";

const argsSchema = z.object({ requestId: z.string(), question: z.string(), startedAt: z.number() });
const resultSchema = z.object({ messageId: z.string().optional(), elapsedMs: z.number(), error: z.string().optional() });
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
    <summary><span>{running ? `Working${seconds ? ` for ${elapsed}` : "…"}` : failed ? "Couldn’t complete this request" : snapshot ? `Worked for ${elapsed}` : "Stopped"}</span><ChevronRight size={14} /></summary>
    <div className="memory-tool-body">
      <div className="memory-tool-step">{running ? <LoaderCircle size={15} className="memory-tool-spinner" /> : snapshot ? <Check size={15} /> : <Brain size={15} />}<strong>{running ? "Consulting your shared brain" : snapshot ? "Consulted your shared brain" : "Memory request interrupted"}</strong></div>
      <p>{snapshot ? `${snapshot.memories.length} memories returned · ${snapshot.citedIds.length} cited in this reply` : failed ? completed?.error ?? "The request failed. Try again when the service is available." : running ? "Finding relevant context and preparing your reply." : "No completed answer was returned."}</p>
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
