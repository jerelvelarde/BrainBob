"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, Brain, Download, X } from "lucide-react";
import { canReadScope, companyScope } from "@/lib/sample-company";
import type { ActiveSession } from "@/lib/active-session";
import type { BackendMemory } from "@/lib/brain-api";

export function LiveSessionPanel({ reader, session, memories, onClose, onInspect }: {
  reader: string; session: ActiveSession | null; memories: BackendMemory[];
  onClose: () => void; onInspect: (id: string) => void;
}) {
  const close = useRef<HTMLButtonElement>(null);
  const [view, setView] = useState<"reply" | "saved">("reply");
  const answered = session?.status === "answered";
  const cited = answered ? session.memories.filter((memory) => session.citedIds.includes(memory.id)) : [];
  const saved = memories.filter((memory) => canReadScope(memory.scope, reader) && memory.status !== "retired");
  const showingReply = answered && view === "reply";
  const records = showingReply ? cited : saved;
  useEffect(() => { close.current?.focus(); }, []);
  function download() {
    if (!answered) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify({ reader, ...session, provenance: "Records returned by /ask; not a full model prompt or source archive." }, null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `${session.taskId}-memory.json`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <aside className="floating-panel inspector-panel session-evidence session-file-panel" aria-label="Memory explorer">
    <div className="panel-heading"><div><Brain size={18} /><h2>Memory</h2></div><button ref={close} className="icon-button" aria-label="Close memory" onClick={onClose}><X size={18} /></button></div>
    <div className="panel-scroll">
      <p className="memory-intro">{showingReply ? "The context behind this reply." : "The context BrainBob can draw on for you."}</p>
      {answered ? <div className="memory-view-switch" aria-label="Memory view">
        <button aria-pressed={showingReply} onClick={() => setView("reply")}>Used in reply <span>{cited.length}</span></button>
        <button aria-pressed={!showingReply} onClick={() => setView("saved")}>Saved <span>{saved.length}</span></button>
      </div> : null}
      {showingReply ? <blockquote className="memory-question">{session.question}</blockquote> : null}
      {!records.length ? <p className="empty-state">{showingReply ? "This reply did not cite any saved memories." : "No saved memories yet."}</p> : null}
      {(["individual", "team", "organization"] as const).map((tier) => {
        const group = records.filter((memory) => companyScope(memory.scope)?.scope === tier);
        if (!group.length) return null;
        return <section className="memory-source-group" key={tier}>
          <h3>{tier === "individual" ? "About you" : tier === "team" ? "Your team" : "Your organization"}<span>{group.length}</span></h3>
          {group.map((memory) => <button className="memory-source-card" key={memory.id} onClick={() => onInspect(memory.id)}>
            <span className="memory-source-label">{companyScope(memory.scope)?.label}<ArrowUpRight size={14} /></span>
            {memory.flagged ? <span className="session-uncertainty">Flagged for review</span> : ["tentative", "unresolved"].includes(memory.status) ? <span className="session-uncertainty">Not yet confirmed</span> : null}
            <span className="memory-source-text">{memory.text}</span>
            <span className="memory-source-link">Source & history</span>
          </button>)}
        </section>;
      })}
      {showingReply ? <p className="memory-snapshot-note">Saved with this reply. Source & history shows the record’s latest details.</p> : null}
    </div>
    {answered ? <div className="panel-footer"><button onClick={download}><Download size={14} />Download snapshot</button></div> : null}
  </aside>;
}
