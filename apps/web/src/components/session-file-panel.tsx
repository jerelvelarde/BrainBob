"use client";

import { useEffect, useRef, useState } from "react";
import { Download, FolderOpen, X } from "lucide-react";
import { memberName } from "@/lib/sample-company";
import type { MemoryScope } from "@/lib/memory";
import { sessionFileMarkdown, type SessionFile } from "@/lib/session-memory";

export function SessionFilePanel({ file, onClose, onHistory, onTier }: { file: SessionFile; onClose: () => void; onHistory: () => void; onTier: (scope: MemoryScope) => void }) {
  const close = useRef<HTMLButtonElement>(null);
  const [sourceId, setSourceId] = useState<string>();
  const source = file.sources.find((item) => item.id === sourceId);
  useEffect(() => { close.current?.focus(); }, []);
  function download() {
    const url = URL.createObjectURL(new Blob([sessionFileMarkdown(file)], { type: "text/markdown;charset=utf-8" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = file.filename; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <aside className="floating-panel inspector-panel demo-evidence session-file-panel" aria-label="Agent session file" onKeyDown={(event) => { if (event.key === "Escape") onClose(); }}>
    <div className="panel-heading"><div><FolderOpen size={18} /><h2>Session file</h2></div><button ref={close} className="icon-button" aria-label="Close session file" onClick={onClose}><X size={18} /></button></div>
    <div className="panel-scroll">
      <div className="session-cover"><small>{file.team} · {file.client}</small><h3>{file.member.name}</h3><p>{file.task.title}</p><span>{file.recordCount} memories · step {file.snapshot + 1}</span></div>
      <p className="demo-mode-note">A task-specific file: your context, your team’s guidance, and shared company knowledge. Scripted selection; live permissions remain a backend requirement.</p>
      {file.missingEvidenceCount ? <p className="session-uncertainty">Incomplete evidence: {file.missingEvidenceCount} relevant records could not be included. Do not assume this file is complete.</p> : null}
      <div className="session-tabs">{file.sections.map((section) => <button key={section.scope} data-scope={section.scope} aria-label={`Inspect ${section.scope} cabinet`} onClick={() => onTier(section.scope)}>{section.scope} <b>{section.records.length}</b></button>)}</div>
      {file.sections.map((section) => <details key={section.scope} open><summary>{section.scope === "individual" ? "Individual" : section.scope === "team" ? "Team" : "Organization"} · {section.label}</summary>
        <div className="session-records">{section.records.length ? section.records.map((record) => <article key={record.id}>
          {record.status !== "active" ? <strong className="session-uncertainty">{record.status === "tentative" ? "Tentative · not a commitment" : "Unresolved · do not assume"}</strong> : null}
          <p>{record.text}</p><button onClick={() => setSourceId(record.sourceId)}>Source · v{record.revision}</button>
        </article>) : <p className="demo-mode-note">No relevant memory in this scope.</p>}</div>
      </details>)}
      {source ? <section className="demo-source" aria-label="Session source"><small>{source.id} · {source.at}</small><blockquote>{source.text}</blockquote><p>{memberName(source.author)} · {source.authority}</p></section> : null}
      <p className="demo-mode-note">Retired revisions and unrelated memories stay in history. Only accessible sources travel with this file.</p><button className="session-history" onClick={onHistory}>Inspect evidence and revision history →</button>
    </div>
    <div className="panel-footer"><button onClick={download}><Download size={14} />Download session .md</button><span>Scripted fixture</span></div>
  </aside>;
}
