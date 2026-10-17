"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, Archive, ArrowDownToLine, ArrowLeft, ArrowRight, ArrowUpRight, BookOpen, Check, ChevronDown, CircleHelp, FileText, FolderClosed, GitBranch, History, Layers3, Maximize2, MessageCircle, Pause, Play, Plus, RotateCcw, Search, ShieldCheck, Sparkles, X, ZoomIn, ZoomOut } from "lucide-react";
import { actionLabels, demoSteps, initialTrace, makeEvent, projectMemories, scopes, TRACE_KEY, traceSchema, type MemoryAction, type MemoryEvent, type MemoryScope } from "@/lib/memory";
import type { SceneHandle } from "./brain/brain-scene";

const BrainScene = dynamic(() => import("./brain/brain-scene"), { ssr: false, loading: () => <div className="scene-loading"><div className="loading-bob">▦</div><span>Opening the memory floor…</span></div> });
const SceneChat = dynamic(() => import("./scene-chat"), { ssr: false, loading: () => <div className="chat-loading">Getting the conversation ready…</div> });

const actionIcons = { created: Plus, retrieved: FolderClosed, evaluated: ShieldCheck, updated: GitBranch, forgotten: Archive };
const scopeNames = { all: "All memories", individual: "Individual", team: "Team", organization: "Organization" };

function BobMark({ small = false }: { small?: boolean }) {
  return <span className={`bob-mark ${small ? "small" : ""}`} aria-hidden="true"><i /><i /><b /><em /></span>;
}

export function BrainWorkspace() {
  const [events, setEvents] = useState<MemoryEvent[]>(initialTrace);
  const eventsRef = useRef(events);
  const [ready, setReady] = useState(false);
  const [cursor, setCursor] = useState<number | null>(null);
  const cursorRef = useRef(cursor);
  const [selected, setSelected] = useState("launch");
  const selectedRef = useRef(selected);
  const [scope, setScope] = useState<MemoryScope | "all">("all");
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [tab, setTab] = useState<"memories" | "activity">("memories");
  const [query, setQuery] = useState("");
  const [inspecting, setInspecting] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [tourStep, setTourStep] = useState<number | null>(null);
  const [notice, setNotice] = useState("");
  const [storageError, setStorageError] = useState("");
  const camera = useRef<SceneHandle | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const helpRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(TRACE_KEY);
      if (saved) {
        const parsed = traceSchema.safeParse(JSON.parse(saved));
        if (parsed.success && parsed.data.events.length && parsed.data.events.every((e, i, list) => i === 0 || e.sequence > list[i - 1].sequence)) {
          eventsRef.current = parsed.data.events;
          setEvents(parsed.data.events);
        } else setStorageError("Saved preview history was invalid. Started a fresh scene.");
      }
    } catch { setStorageError("Browser storage is unavailable. This preview will last until you reload."); }
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => { setReducedMotion(media.matches); if (media.matches) setPlaying(false); };
    update();
    media.addEventListener("change", update);
    setReady(true);
    return () => media.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (!ready) return;
    try { localStorage.setItem(TRACE_KEY, JSON.stringify({ version: 1, events })); }
    catch { setStorageError("Couldn’t save preview history. Export it before leaving this page."); }
  }, [events, ready]);

  useEffect(() => { cursorRef.current = cursor; }, [cursor]);
  useEffect(() => { selectedRef.current = selected; }, [selected]);
  useEffect(() => { if (!notice) return; const timer = setTimeout(() => setNotice(""), 4800); return () => clearTimeout(timer); }, [notice]);
  useEffect(() => {
    if (inspecting) dialogRef.current?.showModal();
    else dialogRef.current?.close();
  }, [inspecting]);
  useEffect(() => {
    if (helpOpen) helpRef.current?.showModal();
    else helpRef.current?.close();
  }, [helpOpen]);

  const appendAction = useCallback((action: MemoryAction, memoryId?: string): MemoryEvent | string => {
    if (cursorRef.current !== null) return "You're retracing a recorded moment. Return to live before changing a memory.";
    if (eventsRef.current.length >= 500) return "The preview history is full. Export your trace, then reset the scene.";
    try {
      const event = makeEvent(action, eventsRef.current, memoryId ?? selectedRef.current);
      const next = [...eventsRef.current, event];
      eventsRef.current = next;
      setEvents(next);
      setSelected(event.memoryId);
      setNotice(event.explanation);
      return event;
    } catch (error) {
      const message = error instanceof Error ? error.message : "The scene action couldn't complete.";
      setNotice(message);
      return message;
    }
  }, []);

  useEffect(() => {
    if (tourStep === null || !playing || cursor !== null) return;
    const timer = setTimeout(() => {
      const step = demoSteps[tourStep];
      if (step) { appendAction(step.action, step.memoryId); setNotice(step.caption); }
      if (tourStep >= demoSteps.length - 1) { setTourStep(null); setNotice("That's the loop. Click a memory and retrace how it changed."); }
      else setTourStep(tourStep + 1);
    }, 2600 / speed);
    return () => clearTimeout(timer);
  }, [tourStep, playing, speed, cursor, appendAction]);

  useEffect(() => {
    if (cursor === null || !playing) return;
    const timer = setTimeout(() => {
      if (cursor >= events.length) setPlaying(false);
      else setCursor(cursor + 1);
    }, 1500 / speed);
    return () => clearTimeout(timer);
  }, [cursor, playing, speed, events.length]);

  const visibleCursor = cursor ?? events.length;
  const memories = useMemo(() => projectMemories(events, visibleCursor), [events, visibleCursor]);
  const active = memories.filter((m) => m.status === "active");
  const filtered = active.filter((m) => (scope === "all" || m.scope === scope) && `${m.title} ${m.content}`.toLowerCase().includes(query.toLowerCase()));
  const selectedMemory = memories.find((m) => m.id === selected);
  const memoryHistory = events.slice(0, visibleCursor).filter((e) => e.memoryId === selected);
  const currentEvent = events[visibleCursor - 1];
  const lastAction = currentEvent?.action;
  const onCameraReady = useCallback((handle: SceneHandle) => { camera.current = handle; }, []);
  const chatAction = useCallback((action: MemoryAction) => appendAction(action), [appendAction]);

  function startTour() {
    const seed = initialTrace();
    eventsRef.current = seed; setEvents(seed);
    cursorRef.current = null; setCursor(null); setSelected("launch"); setScope("all");
    setPlaying(true); setTourStep(0); setNotice("A day in the life of a memory. Let's follow the crew.");
  }
  function retrace(at: number) {
    const bounded = Math.max(0, Math.min(at, events.length));
    cursorRef.current = bounded; setCursor(bounded); setPlaying(false); setTourStep(null);
  }
  function returnLive() { cursorRef.current = null; setCursor(null); setPlaying(!reducedMotion); }
  function reset() {
    const seed = initialTrace(); eventsRef.current = seed; setEvents(seed);
    cursorRef.current = null; setCursor(null); setSelected("launch"); setTourStep(null);
    setScope("all"); setQuery(""); setNotice("Fresh filing cabinets. Same excellent crew.");
  }
  function exportTrace() {
    const blob = new Blob([JSON.stringify({ version: 1, events }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a"); link.href = url; link.download = "brainbob-memory-trace.json"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <main className="app-shell">
    <header className="topbar">
      <a className="brand" href="/" aria-label="BrainBob home"><BobMark /><span>Brain<span className="brand-light">Bob</span><sup>✳</sup></span></a>
      <nav className="main-nav" aria-label="Workspace navigation"><span className="nav-active"><Layers3 size={16} />The brain</span><button onClick={() => { setTab("activity"); setInspecting(false); }}><History size={16} />Memory trail</button></nav>
      <div className="topbar-right"><span className="preview-badge"><span />Scene preview</span><button className="icon-button help-button" aria-label="About this preview" onClick={() => setHelpOpen(true)}><CircleHelp size={19} /></button><span className="profile">JV</span></div>
    </header>

    <section className="workspace-intro">
      <div><div className="eyebrow"><span className="eyebrow-line" />A SHARED BRAIN, A LITTLE LESS CHAOS</div><h1>Great minds <span>remember together.</span></h1><p>A tiny crew. A living memory. Nothing important left behind.</p></div>
      <button className="primary-button" onClick={startTour} disabled={!ready || tourStep !== null}><Play size={15} fill="currentColor" />{tourStep !== null ? "The crew is on it…" : "Watch the memory loop"}<ArrowUpRight size={16} /></button>
    </section>

    <div className="workspace-grid">
      <section className="brain-stage" aria-label="Brain visualization">
        <div className="stage-topline"><div className="floor-tag"><span className="floor-dot" />THE MEMORY FLOOR <span className="floor-number">/ SCRIPTED PREVIEW</span></div><span className="crew-status"><span className={playing ? "status-dot" : "status-dot paused"} />6 Bobs {playing ? "on the clock" : "on a break"}</span></div>
        <div className="scene-view"><BrainScene playing={playing} speed={speed} reducedMotion={reducedMotion} event={currentEvent} selectedScope={scope} selectedMemory={selected} onSelect={setSelected} onScope={setScope} onWorker={setNotice} onReady={onCameraReady} /></div>
        <div className="scene-note"><span className="note-asterisk">✳</span><span>Busy upstairs.<br /><strong>Better together.</strong></span></div>
        <div className="scene-camera"><button className="icon-button" aria-label="Zoom in" onClick={() => camera.current?.zoom(1.15)}><ZoomIn size={17} /></button><button className="icon-button" aria-label="Zoom out" onClick={() => camera.current?.zoom(1 / 1.15)}><ZoomOut size={17} /></button><span /><button className="icon-button" aria-label="Reset isometric camera" onClick={() => camera.current?.reset()}><Maximize2 size={17} /></button></div>
        <div className="scene-hint"><span>↔</span> Drag to look around <i /> Scroll to zoom <i /> Click to explore</div>
        <div className="scene-live" aria-live="polite">{notice || (tourStep !== null ? "Follow the paper. Every memory has a story." : cursor !== null ? `Retracing moment ${visibleCursor} of ${events.length}. Your live memories are unchanged.` : "The crew is ready. Give a memory somewhere to go.")}</div>
        <div className="replay-bar">
          <div className="replay-controls"><button className="play-toggle" aria-label={playing ? "Pause the scene" : "Play the scene"} onClick={() => setPlaying(!playing)}>{playing ? <Pause size={16} fill="currentColor" /> : <Play size={16} fill="currentColor" />}</button><button className="icon-button" aria-label="Previous memory event" onClick={() => retrace(visibleCursor - 1)} disabled={visibleCursor === 0}><ArrowLeft size={15} /></button><button className="icon-button" aria-label="Next memory event" onClick={() => retrace(visibleCursor + 1)} disabled={visibleCursor === events.length}><ArrowRight size={15} /></button><select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} aria-label="Playback speed"><option value={.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option></select></div>
          <div className="timeline-track"><div className="timeline-label"><span>{cursor === null ? "A LITTLE HISTORY" : "RETRACING MEMORY"}</span><span>{visibleCursor.toString().padStart(2, "0")} / {events.length.toString().padStart(2, "0")}</span></div><input type="range" min={0} max={events.length} value={visibleCursor} onChange={(e) => retrace(Number(e.target.value))} aria-label="Memory timeline" /></div>
          <button className={`live-button ${cursor === null ? "is-live" : ""}`} onClick={returnLive}><span />{cursor === null ? "LIVE" : "RETURN TO LIVE"}</button>
        </div>
      </section>

      <aside className="memory-panel">
        <div className="panel-heading"><div><span className="eyebrow">A PLACE FOR EVERY THOUGHT</span><h2>The filing cabinet<span>↘</span></h2></div><span className="memory-count">{active.length}</span></div>
        <div className="panel-tabs"><button className={tab === "memories" ? "active" : ""} onClick={() => setTab("memories")}><FolderClosed size={15} />Memories</button><button className={tab === "activity" ? "active" : ""} onClick={() => setTab("activity")}><Activity size={15} />Activity<span>{visibleCursor}</span></button></div>
        {tab === "memories" ? <>
          <label className="search-box"><Search size={15} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find a thought…" aria-label="Search memories" /><kbd>⌕</kbd></label>
          <div className="scope-row"><span>SHOWING</span><label><select value={scope} onChange={(e) => setScope(e.target.value as MemoryScope | "all")} aria-label="Memory scope"><option value="all">All memories</option>{scopes.map((s) => <option value={s} key={s}>{scopeNames[s]}</option>)}</select><ChevronDown size={14} /></label></div>
          <div className="memory-list">{filtered.length ? filtered.map((memory) => <button key={memory.id} className={`memory-card ${memory.id === selected ? "selected" : ""}`} onClick={() => { setSelected(memory.id); setInspecting(true); }}>
            <div className="card-top"><span className={`scope-pill ${memory.scope}`}><span />{scopeNames[memory.scope]}</span><ArrowUpRight size={15} /></div>
            <h3>{memory.title}</h3><p>{memory.content}</p><div className="card-bottom"><span><FileText size={12} />Revision {memory.revision}</span><span><Check size={12} />Source attached</span></div>
          </button>) : <div className="empty-memories"><FolderClosed size={28} /><p>{visibleCursor === 0 ? "Before the first thought." : "No thoughts in this drawer."}</p><span>{query ? "Try another search." : "Try another scope, or remember something new."}</span></div>}</div>
        </> : <div className="activity-list">{events.slice(0, visibleCursor).toReversed().map((event) => {
          const Icon = actionIcons[event.action];
          return <button key={event.id} className="activity-item" onClick={() => { setSelected(event.memoryId); setInspecting(true); }}><span className={`activity-icon ${event.action}`}><Icon size={16} /></span><span><strong>{actionLabels[event.action]} <small>#{event.sequence.toString().padStart(2, "0")}</small></strong><b>{event.title}</b><em>{event.actor} · Scripted preview</em></span><ArrowUpRight size={13} /></button>;
        })}{!visibleCursor ? <div className="empty-memories"><History size={28} /><p>The story starts here.</p><span>Move forward to see the first memory.</span></div> : null}</div>}
        <div className="panel-bottom"><div className="crew-card"><div className="mini-bob"><BobMark small /></div><div><strong>A little wiser, every day.</strong><p>Good memory is a team sport.</p></div><Sparkles size={17} /></div><button className="chat-button" onClick={() => setChatOpen(!chatOpen)}><MessageCircle size={16} />Talk to the crew<ArrowUpRight size={16} /></button></div>
      </aside>
    </div>

    <section className="memory-actions" aria-label="Preview memory actions"><div className="actions-label"><span className="status-dot" /><strong>Put the crew to work</strong><span>Try a memory operation</span></div><div className="action-buttons">{([ ["created", "Remember"], ["retrieved", "Retrieve"], ["evaluated", "Evaluate"], ["updated", "Update"], ["forgotten", "Forget"] ] as [MemoryAction, string][]).map(([action, label]) => {
      const Icon = actionIcons[action];
      return <button key={action} onClick={() => appendAction(action)} disabled={!ready || cursor !== null || tourStep !== null} className={lastAction === action ? "last-action" : ""}><Icon size={15} />{label}</button>;
    })}</div></section>

    <footer className="workspace-footer"><span><span className="footer-flower">✳</span>Shared Brain first. Self-improvement through better memory.</span><div><button onClick={exportTrace}><ArrowDownToLine size={13} />Export trace</button><button onClick={reset}><RotateCcw size={13} />Reset scene</button><span className="footer-preview">SCRIPTED PREVIEW · SAVED IN THIS BROWSER</span></div></footer>
    {storageError ? <div className="storage-notice" role="status">{storageError}</div> : null}

    <dialog ref={dialogRef} onCancel={() => setInspecting(false)} onClose={() => setInspecting(false)} className="memory-dialog">
      <div className="dialog-top"><span className="eyebrow">EVERY MEMORY HAS A PAPER TRAIL</span><button className="icon-button" aria-label="Close memory inspector" onClick={() => setInspecting(false)}><X size={20} /></button></div>
      {selectedMemory ? <><div className={`scope-pill ${selectedMemory.scope}`}><span />{scopeNames[selectedMemory.scope]} · {selectedMemory.status === "forgotten" ? "Archived" : "Active"}</div><h2>{selectedMemory.title}</h2><div className="memory-value"><span>REVISION {selectedMemory.revision}</span><p>{selectedMemory.content}</p></div><h3><BookOpen size={15} />The evidence</h3><blockquote>{selectedMemory.evidence}</blockquote><h3><History size={15} />How we got here</h3><div className="revision-list">{memoryHistory.map((event) => {
        const Icon = actionIcons[event.action];
        return <div className="revision-item" key={event.id}><span className={`activity-icon ${event.action}`}><Icon size={15} /></span><div><strong>{actionLabels[event.action]}<small>#{event.sequence}</small></strong><p>{event.explanation}</p>{event.after ? <div className="revision-content">{event.after.content}</div> : null}<span className="revision-actor">{event.actor} · Scripted evidence</span></div><button className="icon-button" aria-label={`Retrace event ${event.sequence}`} onClick={() => { retrace(events.findIndex((e) => e.id === event.id) + 1); setInspecting(false); }}><History size={16} /></button></div>;
      })}</div></> : <div className="empty-memories"><p>This memory hasn't been created at this point in the story.</p><button className="primary-button" onClick={() => { returnLive(); setInspecting(false); }}>Return to live</button></div>}
      <div className="inspector-note"><ShieldCheck size={15} />Recorded evidence and decisions. No hidden model reasoning.</div>
    </dialog>

    <dialog ref={helpRef} onCancel={() => setHelpOpen(false)} onClose={() => setHelpOpen(false)} className="help-dialog"><div className="dialog-top"><BobMark /><button className="icon-button" aria-label="Close preview guide" onClick={() => setHelpOpen(false)}><X size={20} /></button></div><h2>Welcome upstairs.</h2><p>This is the first interactive BrainBob visualization: six SpongeBob workers in an isometric memory office.</p><ul><li>Drag the room to orbit. Scroll or use the camera buttons to zoom.</li><li>Click a cabinet to filter memories; click a memory to inspect its evidence.</li><li>Run the memory loop, then scrub the timeline to retrace its changes.</li><li>Use the CopilotKit chat to trigger scripted memory operations.</li></ul><div className="help-disclosure"><strong>What is connected?</strong><p>The scene, memory projection, browser persistence, and CopilotKit preview controller work locally. NemoClaw, NVIDIA Switchyard, SQL storage, and Crusoe inference are the next integration step. This preview makes no model calls and does not measure memory accuracy.</p></div></dialog>

    {chatOpen ? <section className="chat-drawer" aria-label="CopilotKit scene controls"><div className="chat-drawer-heading"><div><span className="eyebrow">COPILOTKIT / AG-UI</span><h2>Talk to the crew.</h2></div><button className="icon-button" aria-label="Close crew chat" onClick={() => setChatOpen(false)}><X size={20} /></button></div><p className="chat-disclosure">Scripted scene controls. Try “remember a new idea”.</p><SceneChat onAction={chatAction} /></section> : null}
  </main>;
}
