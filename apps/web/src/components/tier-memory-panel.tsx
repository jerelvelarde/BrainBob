"use client";

import { useEffect, useRef } from "react";
import { Archive, FolderOpen, LockKeyhole, X } from "lucide-react";
import { drawersForTier, memberForReader } from "@/lib/sample-company";
import type { MemoryScope } from "@/lib/memory";
import type { DemoRecord } from "@/lib/correctness-demo";

const titles = { individual: "Individual", team: "Team", organization: "Organization" };

export function TierMemoryPanel({ scope, reader, records, onClose, onSession, onEvidence }: {
  scope: MemoryScope; reader: string; records: DemoRecord[]; onClose: () => void;
  onSession: () => void; onEvidence: (sourceId: string) => void;
}) {
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => { close.current?.focus(); }, []);
  const drawers = drawersForTier(scope, reader);
  const available = drawers.filter((drawer) => drawer.accessible);
  const closed = drawers.filter((drawer) => !drawer.accessible);
  const ownRecords = records.filter((record) => record.status !== "retired" && available.some((drawer) => drawer.path === record.scope));
  const closedDrawers = closed.map((drawer) => <div className="tier-drawer" key={drawer.path}><LockKeyhole size={14} /><span>{drawer.label}</span><small>No access</small></div>);
  return <aside className="floating-panel inspector-panel demo-evidence" aria-label={`${titles[scope]} cabinet`} onKeyDown={(event) => { if (event.key === "Escape") onClose(); }}>
    <div className="panel-heading"><div><Archive size={18} /><h2>{titles[scope]} cabinet</h2></div><button ref={close} className="icon-button" aria-label="Close cabinet" onClick={onClose}><X size={18} /></button></div>
    <div className="panel-scroll">
      <p className="demo-mode-note">Viewing as {memberForReader(reader)?.label}. Each drawer holds one {scope === "individual" ? "person’s" : scope === "team" ? "team’s" : "organization’s"} memory.</p>
      <div className="tier-drawers">{available.map((drawer) => <div className="tier-drawer" data-access="open" key={drawer.path}><FolderOpen size={14} /><span>{drawer.label}</span><small>Your access</small></div>)}
        {scope === "individual" ? <details><summary>{closed.length} other people · closed</summary>{closedDrawers}</details> : closedDrawers}
      </div>
      <div className="demo-records">{ownRecords.map((record) => <button key={record.id} onClick={() => onEvidence(record.sourceId)}><span>{record.status} · v{record.revision}</span><strong>{record.text}</strong><small>Inspect source →</small></button>)}</div>
      <p className="demo-mode-note tier-note">You can read your individual, team, and organization memory. The session file selects what is relevant to this task from all three tiers.</p>
      {scope === "organization" ? <p className="demo-mode-note">Atlas Harbor is Rusty Rod’s client. That relationship grants no access to the client’s private drawer.</p> : null}
    </div>
    <div className="panel-footer"><button onClick={onSession}><FolderOpen size={14} />Open session file</button><span>Fixture access preview</span></div>
  </aside>;
}
