"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowLeft, FolderClosed, X } from "lucide-react";
import { brainApi, scopeLabel, type BackendMemory, type Episode, type MemoryHistory, type StoredEvent } from "@/lib/brain-api";
import { eventDescription } from "@/lib/backend-state";

export function LiveMemoryPanel({ actor, memories, selected, events, readOnly, citedIds, onSelect, onClose, onRetrace }: {
  actor: string;
  memories: BackendMemory[]; selected?: string; events: StoredEvent[]; readOnly: boolean;
  citedIds: string[];
  onSelect: (id?: string) => void; onClose: () => void; onRetrace: (seq: number) => void;
}) {
  const [query, setQuery] = useState("");
  const [archived, setArchived] = useState(false);
  const memory = memories.find((m) => m.id === selected);
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => { close.current?.focus(); }, []);
  return <aside className="floating-panel inspector-panel" aria-label="Memory inspector" onKeyDown={(e) => { if (e.key === "Escape") onClose(); }}>
    <div className="panel-heading"><div>{selected ? <button className="icon-button" aria-label="Back to memories" onClick={() => onSelect(undefined)}><ArrowLeft size={18} /></button> : <FolderClosed size={18} />}<h2>{memory ? "Inspect memory" : "Shared memories"}</h2></div><button ref={close} className="icon-button" aria-label="Close memory inspector" onClick={onClose}><X size={18} /></button></div>
    <div className="panel-scroll">
      {memory ? <MemoryDetail key={memory.id} initialActor={actor} memory={memory} events={events} readOnly={readOnly} onSelect={onSelect} onRetrace={onRetrace} /> : <>
        <label className="search-box"><input aria-label="Search memories" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search memories" /></label>
        <label className="archive-toggle"><input type="checkbox" checked={archived} onChange={(e) => setArchived(e.target.checked)} />Include retired memories</label>
        <div className="memory-list">{memories.filter((m) => (archived || m.status !== "retired") && m.text.toLowerCase().includes(query.toLowerCase())).map((m) => <button key={m.id} className={`memory-card ${citedIds.includes(m.id) ? "cited" : ""}`} onClick={() => onSelect(m.id)}>
          <span className="scope-pill">{scopeLabel(m.scope)}</span><span className={`memory-status ${m.flagged ? "flagged" : ""}`}>{m.flagged ? "Flagged · locked" : m.status}</span><h3>{m.text}</h3><p>{m.author}</p>
        </button>)}</div>
        {!memories.length ? <p className="empty-state">No memories available for this reader yet. Use Remember in chat to file a conversation.</p> : null}
      </>}
    </div>
  </aside>;
}

function MemoryDetail({ initialActor, memory, events, readOnly, onSelect, onRetrace }: { initialActor: string; memory: BackendMemory; events: StoredEvent[]; readOnly: boolean; onSelect: (id?: string) => void; onRetrace: (seq: number) => void }) {
  const [episode, setEpisode] = useState<Episode>();
  const [history, setHistory] = useState<MemoryHistory>();
  const [sourceError, setSourceError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState("");
  const [busy, setBusy] = useState(false);
  const actor = initialActor;
  const [text, setText] = useState(memory.text);
  const [reason, setReason] = useState("");
  const latestSeq = events.at(-1)?.seq;
  useEffect(() => {
    const abort = new AbortController();
    void brainApi.episode(memory.origin, initialActor, abort.signal).then(setEpisode).catch((err) => { if (!abort.signal.aborted) setSourceError(err.message); });
    return () => abort.abort();
  }, [memory.origin, initialActor]);
  useEffect(() => {
    const abort = new AbortController();
    void brainApi.history(memory.id, initialActor, abort.signal).then((value) => { setHistory(value); setHistoryError(""); }).catch((err) => { if (!abort.signal.aborted) setHistoryError(err.message); });
    return () => abort.abort();
  }, [memory.id, initialActor, latestSeq]);
  const owner = memory.owner === actor.trim();
  const locked = memory.status === "locked";
  const disabled = readOnly || busy || memory.status === "retired" || !actor.trim() || (locked && !owner);
  const retirement = events.findLast((e) => e.type === "memory.retired" && e.memory_id === memory.id);
  async function change(action: "correct" | "retire" | "lock" | "keep") {
    if (disabled) return;
    setBusy(true); setError(""); setReceipt("");
    try {
      const result = action === "lock" ? await brainApi.lock(memory.id, actor.trim())
        : locked ? await brainApi.resolve(memory.id, actor.trim(), action, action === "correct" ? text.trim() : undefined)
        : action === "correct" ? await brainApi.correct(memory.id, text.trim(), actor.trim())
        : await brainApi.retire(memory.id, reason.trim(), actor.trim());
      setReceipt(action === "correct" ? "Correction saved as a new memory." : action === "retire" ? "Retired. The record remains in history." : action === "lock" ? "Owner lock saved." : "Owner decision saved; flag cleared.");
      if (result.memory.id !== memory.id) onSelect(result.memory.id);
    } catch (err) { setError(err instanceof Error ? err.message : "The change could not be saved."); }
    finally { setBusy(false); }
  }
  return <>
    <div className="memory-meta"><span>{scopeLabel(memory.scope)}</span><span className={memory.flagged ? "memory-status flagged" : ""}>{memory.flagged ? "Flagged · locked" : memory.status}</span></div>
    <h3 className="memory-title">{memory.text}</h3>
    <p className="memory-author">By {memory.author}{memory.owner ? ` · Owner: ${memory.owner}` : ""}</p>
    <p className="memory-author">Authority: {memory.authority}{memory.model ? ` · Model: ${memory.model}` : ""}</p>
    {memory.status === "tentative" ? <p className="memory-value">Tentative · not an approved commitment.</p> : null}
    {memory.reason ? <p className="memory-value">{memory.reason}</p> : null}
    {retirement?.type === "memory.retired" && retirement.confirmed === true ? <p className="confirmed-retirement">Fresh retirement confirmation passed.</p> : null}
    <details open><summary>Original conversation</summary>{episode ? <><blockquote>{episode.text}</blockquote><p className="memory-author">{episode.date} · {episode.source}</p></> : <p className="empty-state">{sourceError || "Loading source…"}</p>}</details>
    <details><summary>Full correction chain and status history</summary>{historyError ? <p className="backend-error">{historyError}</p> : null}
      {history?.chain.map((m) => <button className="revision-item" key={m.id} onClick={() => onSelect(m.id)}><span><strong>{m.text}</strong><small>{m.id} · {m.status}{m.supersedes ? ` · supersedes ${m.supersedes}` : ""}</small></span></button>)}
      {history?.events.filter((e): e is StoredEvent => e.type !== "replay.done").map((event) => <button className="revision-item" key={event.seq} onClick={() => onRetrace(event.seq)}><span><strong>{eventDescription(event)}</strong><small>{new Date(event.ts * 1000).toLocaleString()}</small></span></button>)}
    </details>
    <details><summary>Manage memory</summary>
      <label className="memory-field">Acting as (demo)<input value={actor} readOnly /></label>
      <p className="empty-state">Demo identity only. Read access does not establish authority to approve or change a record.</p>
      {locked && !owner ? <p className="empty-state">Only {memory.owner} can resolve this locked record.</p> : null}
      <label className="memory-field">Correction<textarea value={text} onChange={(e) => setText(e.target.value)} /></label>
      <div className="memory-operations"><button disabled={disabled || !text.trim() || text.trim() === memory.text} onClick={() => void change("correct")}>Save correction</button><button disabled={disabled} onClick={() => void change(locked ? "keep" : "lock")}>{locked ? "Keep and clear flag" : "Lock as owner"}</button></div>
      <label className="memory-field">Retirement reason<input value={reason} onChange={(e) => setReason(e.target.value)} /></label>
      <div className="memory-operations"><button disabled={disabled || (!locked && !reason.trim())} onClick={() => void change("retire")}>Retire memory</button></div>
      {readOnly ? <p className="empty-state">Return to live to make changes.</p> : null}
    </details>
    {busy ? <p role="status">Saving…</p> : null}{receipt ? <p className="operation-receipt" role="status">{receipt}</p> : null}{error ? <p className="backend-error" role="alert">{error}</p> : null}
  </>;
}
