"use client";

import { useEffect, useRef } from "react";
import { Download, FolderOpen, X } from "lucide-react";
import { companyScope, memberForReader, teamForReader } from "@/lib/sample-company";
import { sessionStatus, type ActiveSession } from "@/lib/active-session";

export function LiveSessionPanel({ reader, session, onClose, onChat, onInspect }: {
  reader: string; session: ActiveSession | null; onClose: () => void; onChat: () => void; onInspect: (id: string) => void;
}) {
  const close = useRef<HTMLButtonElement>(null);
  const member = memberForReader(reader);
  useEffect(() => { close.current?.focus(); }, []);
  function download() {
    if (!session || session.status !== "answered") return;
    const url = URL.createObjectURL(new Blob([JSON.stringify({ reader, ...session, provenance: "Records returned by /ask; not a full model prompt or source archive." }, null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `${member?.id}-${session.taskId}-session.json`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <aside className="floating-panel inspector-panel session-evidence session-file-panel" aria-label="Active session file" onKeyDown={(event) => { if (event.key === "Escape") onClose(); }}>
    <div className="panel-heading"><div><FolderOpen size={18} /><h2>Session file</h2></div><button ref={close} className="icon-button" aria-label="Close session file" onClick={onClose}><X size={18} /></button></div>
    <div className="panel-scroll">
      <div className="session-cover"><small>{teamForReader(reader)?.label} · Rusty Rod</small><h3>{member?.label}</h3><p>{session?.question ?? "Your Bob is ready at the desk."}</p><span role="status">{sessionStatus(session)}{session?.status === "answered" ? ` · ${session.memories.length} memories` : ""}</span></div>
      {!session ? <><p className="empty-state">Ask a question to fill this file with the memory returned for your session.</p><button className="session-history" onClick={onChat}>Ask the shared brain →</button></> : null}
      {session?.status === "working" ? <p className="empty-state">Bob is working on your question. The file will fill when the backend returns its selected records.</p> : null}
      {session?.status === "failed" ? <p className="backend-error" role="alert">{session.error}</p> : null}
      {session?.status === "cancelled" ? <p className="empty-state">This request was stopped. No completed memory file was returned.</p> : null}
      {session?.status === "answered" ? <>
        <p className="session-note">Frozen from this answer’s backend response. New memory changes do not rewrite this file.</p>
        {(["individual", "team", "organization"] as const).map((tier) => {
          const records = session.memories.filter((memory) => companyScope(memory.scope)?.scope === tier);
          return <details key={tier} open><summary>{tier === "individual" ? "Individual" : tier === "team" ? "Team" : "Organization"} · {records.length}</summary><div className="session-records">{records.length ? records.map((memory) => <article key={memory.id}>
            <small>{companyScope(memory.scope)?.label} · {memory.status}{session.citedIds.includes(memory.id) ? " · cited" : ""}</small>
            {memory.status === "tentative" ? <strong className="session-uncertainty">Tentative · not an approved fact</strong> : null}
            <p>{memory.text}</p><button onClick={() => onInspect(memory.id)}>Source and history · {memory.id}</button>
          </article>) : <p className="session-note">No memory returned from this tier.</p>}</div></details>;
        })}
        <details><summary>Answer</summary><p className="session-answer">{session.answer || "The backend returned an empty answer."}</p></details>
        <details><summary>About this file</summary><p className="session-note">Task: {session.taskId}. These are the records returned by /ask, not the full model prompt or source text. Source and history opens the record’s current inspector. This file belongs to the current chat, independently of event retrace.</p></details>
      </> : null}
    </div>
    <div className="panel-footer"><button onClick={download} disabled={session?.status !== "answered"}><Download size={14} />Download file</button><span>Current chat</span></div>
  </aside>;
}
