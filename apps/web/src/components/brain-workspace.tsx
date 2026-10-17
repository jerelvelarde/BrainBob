"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Archive, ArrowDownToLine, ArrowLeft, ArrowRight, CircleHelp, Clapperboard, FolderClosed, GitBranch, History, Maximize2, MessageCircle, Pause, Play, Plus, RotateCcw, Search, ShieldCheck, X, ZoomIn, ZoomOut } from "lucide-react";
import { actionLabels, demoSteps, initialTrace, makeEvent, projectMemories, scopes, TRACE_KEY, traceSchema, type MemoryAction, type MemoryEvent, type MemoryScope } from "@/lib/memory";
import { cinematicsAt, clipPhase, cueFromMemory, sceneClips, scopeCharacters, type SceneAction, type SceneCue } from "@/lib/scene-animation";
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
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [timelineOpen, setTimelineOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [inspecting, setInspecting] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatLoaded, setChatLoaded] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [tourStep, setTourStep] = useState<number | null>(null);
  const [notice, setNotice] = useState("");
  const [storageError, setStorageError] = useState("");
  const [animationsOpen, setAnimationsOpen] = useState(false);
  const [animationScope, setAnimationScope] = useState<MemoryScope>("team");
  const [fixtureCue, setFixtureCue] = useState<SceneCue>();
  const [clipProgress, setClipProgress] = useState(0);
  const [clipSeek, setClipSeek] = useState<{ value: number; revision: number }>();
  const camera = useRef<SceneHandle | null>(null);
  const inspectorButton = useRef<HTMLButtonElement>(null);
  const chatButton = useRef<HTMLButtonElement>(null);
  const inspectorClose = useRef<HTMLButtonElement>(null);
  const chatClose = useRef<HTMLButtonElement>(null);
  const helpRef = useRef<HTMLDialogElement>(null);
  const animationButton = useRef<HTMLButtonElement>(null);
  const animationClose = useRef<HTMLButtonElement>(null);

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
    if (libraryOpen) inspectorClose.current?.focus();
  }, [libraryOpen]);
  useEffect(() => { if (chatOpen) chatClose.current?.focus(); }, [chatOpen]);
  useEffect(() => { if (animationsOpen) animationClose.current?.focus(); }, [animationsOpen]);
  useEffect(() => {
    if (helpOpen) helpRef.current?.showModal();
    else helpRef.current?.close();
  }, [helpOpen]);

  const appendAction = useCallback((action: MemoryAction, memoryId?: string): MemoryEvent | string => {
    if (cursorRef.current !== null) return "You're retracing a recorded moment. Return to live before changing a memory.";
    if (eventsRef.current.length >= 500) return "The preview history is full. Export your trace, then reset the scene.";
    try {
      const event = makeEvent(action, eventsRef.current, memoryId ?? selectedRef.current);
      setFixtureCue(undefined); setClipSeek(undefined);
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
    }, (tourStep === 0 ? 400 : (sceneClips[demoSteps[tourStep - 1].action].seconds + .3) * 1000) / speed);
    return () => clearTimeout(timer);
  }, [tourStep, playing, speed, cursor, appendAction]);

  useEffect(() => {
    if (cursor === null || !playing || fixtureCue) return;
    const timer = setTimeout(() => {
      if (cursor >= events.length) setPlaying(false);
      else setCursor(cursor + 1);
    }, ((events[cursor - 1] ? sceneClips[events[cursor - 1].action].seconds : 1) + .3) * 1000 / speed);
    return () => clearTimeout(timer);
  }, [cursor, playing, speed, events, fixtureCue]);

  const visibleCursor = cursor ?? events.length;
  const memories = useMemo(() => projectMemories(events, visibleCursor), [events, visibleCursor]);
  const active = memories.filter((m) => m.status === "active");
  const filtered = active.filter((m) => (scope === "all" || m.scope === scope) && `${m.title} ${m.content}`.toLowerCase().includes(query.toLowerCase()));
  const selectedMemory = memories.find((m) => m.id === selected);
  const memoryHistory = events.slice(0, visibleCursor).filter((e) => e.memoryId === selected);
  const currentEvent = events[visibleCursor - 1];
  const recordedCue = useMemo(() => cueFromMemory(currentEvent), [currentEvent]);
  const sceneCue = fixtureCue ?? recordedCue;

  const onCameraReady = useCallback((handle: SceneHandle) => { camera.current = handle; }, []);
  const chatAction = useCallback((action: MemoryAction) => appendAction(action), [appendAction]);

  function startTour() {
    setFixtureCue(undefined); setClipSeek(undefined); setAnimationsOpen(false);
    const seed = initialTrace();
    eventsRef.current = seed; setEvents(seed);
    cursorRef.current = null; setCursor(null); setSelected("launch"); setScope("all");
    setPlaying(true); setTourStep(0); setNotice("A day in the life of a memory. Let's follow the crew.");
  }
  function retrace(at: number) {
    setFixtureCue(undefined); setClipSeek({ value: .62, revision: Date.now() });
    const bounded = Math.max(0, Math.min(at, events.length));
    cursorRef.current = bounded; setCursor(bounded); setPlaying(false); setTourStep(null); setTimelineOpen(true);
  }
  function returnLive() { cursorRef.current = null; setCursor(null); setPlaying(!reducedMotion); }
  function reset() {
    setFixtureCue(undefined); setClipSeek(undefined);
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


  function closeInspector() { setLibraryOpen(false); inspectorButton.current?.focus(); }
  function closeChat() { setChatOpen(false); chatButton.current?.focus(); }
  function openInspector(memoryId?: string) {
    if (memoryId) { setSelected(memoryId); setInspecting(true); }
    else setInspecting(false);
    setLibraryOpen(true);
    setAnimationsOpen(false);
    if (window.matchMedia("(max-width: 760px)").matches) setChatOpen(false);
  }

  function previewAnimation(action: SceneAction, nextScope = animationScope) {
    setAnimationScope(nextScope);
    setFixtureCue({ id: crypto.randomUUID(), action, scope: nextScope, title: sceneClips[action].label, source: "fixture" });
    setClipSeek(undefined); setClipProgress(0); setTourStep(null); setPlaying(!reducedMotion);
    setNotice("");
  }

  function closeAnimations() { setAnimationsOpen(false); animationButton.current?.focus(); }

  return <main className="app-shell" data-dramatic={cinematicsAt(sceneCue?.action, clipProgress).darkness > .5 ? sceneCue?.action : undefined}>
    <section className="scene-view" aria-label="Brain visualization">
      <BrainScene playing={playing} speed={speed} reducedMotion={reducedMotion} event={currentEvent}
        cue={sceneCue} seek={clipSeek} onProgress={setClipProgress}
        selectedScope={scope} selectedMemory={selected} onSelect={openInspector} onScope={setScope}
        onWorker={setNotice} onReady={onCameraReady} />
    </section>

    <header className="floating-header">
      <a className="brand" href="/" aria-label="BrainBob home"><BobMark /><span>BrainBob</span></a>
      <button className="preview-label" onClick={() => setHelpOpen(true)}>Scene preview <CircleHelp size={13} /></button>
    </header>
    <div className="panel-launchers">
      <button ref={animationButton} className={animationsOpen ? "selected" : ""} aria-label="Event animations" aria-expanded={animationsOpen} aria-controls="animation-preview" onClick={() => {
        if (animationsOpen) closeAnimations();
        else { setAnimationsOpen(true); setLibraryOpen(false); setChatOpen(false); }
      }}><Clapperboard size={18} /><span>Events</span></button>
      <button ref={chatButton} aria-label="Chat" className={chatOpen ? "selected" : ""} aria-expanded={chatOpen} aria-controls="crew-chat" onClick={() => {
        if (chatOpen) closeChat();
        else { setChatLoaded(true); setChatOpen(true); setAnimationsOpen(false); if (window.matchMedia("(max-width: 760px)").matches) setLibraryOpen(false); }
      }}><MessageCircle size={18} /><span>Chat</span></button>
      <button ref={inspectorButton} aria-label="Memories" className={libraryOpen ? "selected" : ""} aria-expanded={libraryOpen} aria-controls="memory-inspector" onClick={() => libraryOpen ? closeInspector() : openInspector()}><FolderClosed size={18} /><span>Memories</span></button>
    </div>

    {animationsOpen ? <aside id="animation-preview" className="floating-panel animation-panel" aria-label="Event animation preview" onKeyDown={(e) => { if (e.key === "Escape") closeAnimations(); }}>
      <div className="panel-heading"><div><Clapperboard size={18} /><h2>Office rehearsals</h2></div><button ref={animationClose} className="icon-button" aria-label="Close event animations" onClick={closeAnimations}><X size={18} /></button></div>
      <div className="panel-scroll">
        <label className="animation-scope-label" htmlFor="animation-scope">Whose memory?</label>
        <select id="animation-scope" className="scope-select" value={animationScope} onChange={(e) => {
          const next = e.target.value as MemoryScope; setAnimationScope(next);
          if (fixtureCue) previewAnimation(fixtureCue.action, next);
        }}>{(["organization", "team", "individual"] as const).map((s) => <option key={s} value={s}>{scopeCharacters[s].name} · {scopeCharacters[s].role}</option>)}</select>
        <div className="animation-grid">{(Object.keys(sceneClips) as SceneAction[]).map((action, i) => <button key={action}
          aria-pressed={fixtureCue?.action === action} onClick={() => previewAnimation(action)}>
          <span className="animation-number" style={{ color: sceneClips[action].color }}>{String(i + 1).padStart(2, "0")}</span>{sceneClips[action].label}
        </button>)}</div>
        {fixtureCue ? <div className="animation-scrubber">
          <div><span>{sceneClips[fixtureCue.action].label}</span><button aria-label="Replay animation" onClick={() => previewAnimation(fixtureCue.action)}><RotateCcw size={14} />Replay</button></div>
          <input type="range" aria-label="Animation progress" min={0} max={100} step={1} value={Math.round(clipProgress * 100)} onChange={(e) => { setPlaying(false); setClipSeek({ value: Number(e.target.value) / 100, revision: Date.now() }); }} />
          <p>{reducedMotion ? "Reduced motion · still poses" : "Pause or scrub to inspect a moment."}</p>
        </div> : null}
      </div>
      <div className="animation-disclosure">Animation fixtures. No backend requests or memory changes.</div>
    </aside> : null}

    {libraryOpen ? <aside id="memory-inspector" className="floating-panel inspector-panel" aria-label="Memory inspector" onKeyDown={(e) => { if (e.key === "Escape") { e.stopPropagation(); closeInspector(); } }}>
      <div className="panel-heading">
        <div>{inspecting ? <button className="icon-button" aria-label="Back to memories" onClick={() => setInspecting(false)}><ArrowLeft size={18} /></button> : <FolderClosed size={18} />}
          <h2>{inspecting ? "Inspect memory" : "Memories"}</h2>{!inspecting ? <span className="count">{active.length}</span> : null}</div>
        <button ref={inspectorClose} className="icon-button" aria-label="Close memory inspector" onClick={closeInspector}><X size={18} /></button>
      </div>
      <div className="panel-scroll">
        {!inspecting ? <>
          <label className="search-box"><Search size={16} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search memories" aria-label="Search memories" /></label>
          <select className="scope-select" value={scope} onChange={(e) => setScope(e.target.value as MemoryScope | "all")} aria-label="Memory scope"><option value="all">All memories</option>{scopes.map((s) => <option key={s} value={s}>{scopeNames[s]}</option>)}</select>
          <div className="memory-list">{filtered.map((memory) => <button className="memory-card" key={memory.id} onClick={() => { setSelected(memory.id); setInspecting(true); }}><span className="scope-pill">{scopeNames[memory.scope]}</span><h3>{memory.title}</h3><p>{memory.content}</p></button>)}
            {!filtered.length ? <p className="empty-state">No memories here yet.</p> : null}</div>
          <button className="new-memory" disabled={!ready || cursor !== null || tourStep !== null} onClick={() => { appendAction("created"); setInspecting(true); }}><Plus size={16} />Remember something</button>
        </> : selectedMemory ? <>
          <div className="memory-meta"><span className="scope-pill">{scopeNames[selectedMemory.scope]}</span><span>v{selectedMemory.revision}{selectedMemory.status === "forgotten" ? " · Archived" : ""}</span></div>
          <h3 className="memory-title">{selectedMemory.title}</h3><p className="memory-value">{selectedMemory.content}</p>
          <details open><summary>Evidence</summary><blockquote>{selectedMemory.evidence}</blockquote></details>
          <details><summary>History · {memoryHistory.length}</summary><div className="revision-list">{memoryHistory.map((event) => {
            const Icon = actionIcons[event.action];
            return <button className="revision-item" key={event.id} aria-label={`Retrace event ${event.sequence}`} onClick={() => retrace(events.findIndex((e) => e.id === event.id) + 1)}>
              <Icon size={16} /><span><strong>{actionLabels[event.action]}</strong><small>{event.explanation}</small></span><History size={14} /></button>;
          })}</div></details>
          <div className="memory-operations">{([["retrieved", "Retrieve"], ["evaluated", "Check"], ["updated", "Update"], ["forgotten", "Archive"]] as [MemoryAction, string][]).map(([action, label]) => {
            const Icon = actionIcons[action];
            return <button key={action} disabled={!ready || cursor !== null || tourStep !== null || selectedMemory.status === "forgotten"} onClick={() => appendAction(action)}><Icon size={15} />{label}</button>;
          })}</div>
        </> : <p className="empty-state">This memory doesn’t exist at this point in the timeline.</p>}
      </div>
      <div className="panel-footer"><button onClick={exportTrace}><ArrowDownToLine size={14} />Export</button><button onClick={reset}><RotateCcw size={14} />Reset demo</button></div>
    </aside> : null}

    <section id="crew-chat" className="floating-panel chat-panel" aria-label="Crew chat" hidden={!chatOpen} onKeyDown={(e) => { if (e.key === "Escape") { e.stopPropagation(); closeChat(); } }}>
      <div className="panel-heading"><div><MessageCircle size={18} /><h2>The crew</h2></div><button ref={chatClose} className="icon-button" aria-label="Close crew chat" onClick={closeChat}><X size={18} /></button></div>
      {chatLoaded ? <SceneChat onAction={chatAction} /> : null}
    </section>

    <div className="camera-controls">
      <button className="icon-button" aria-label="Zoom in" onClick={() => camera.current?.zoom(1.15)}><ZoomIn size={18} /></button>
      <button className="icon-button" aria-label="Zoom out" onClick={() => camera.current?.zoom(1 / 1.15)}><ZoomOut size={18} /></button>
      <button className="icon-button" aria-label="Reset isometric camera" onClick={() => camera.current?.reset()}><Maximize2 size={18} /></button>
    </div>
    <div className="bottom-controls">
      {notice ? <div className="scene-notice" role="status">{notice}</div> : sceneCue ? <div className="clip-caption" role="status">
        <span>{sceneCue.source === "fixture" ? "ANIMATION PREVIEW" : cursor !== null ? "RECORDED PREVIEW" : "SCRIPTED EVENT"} · {scopeCharacters[sceneCue.scope].name}</span>
        <strong>{clipPhase(sceneCue.action, clipProgress)}</strong>
        {sceneCue.action === "forgotten" ? <small>*Only the selected record is retired. The chaos is theatrical.</small> : null}
        {sceneCue.action === "evaluated" ? <small>Choreography preview · no evaluation result claimed</small> : null}
      </div> : null}
      {timelineOpen ? <section className="timeline-panel" aria-label="Memory retracing">
        <div className="timeline-top"><span>{cursor === null ? "Memory trail" : "Retracing"} <small>{visibleCursor} / {events.length}</small></span><button className="icon-button" aria-label="Close timeline" onClick={() => setTimelineOpen(false)}><X size={16} /></button></div>
        <div className="timeline-row"><button className="icon-button" aria-label="Previous memory event" disabled={!visibleCursor} onClick={() => retrace(visibleCursor - 1)}><ArrowLeft size={16} /></button><input type="range" aria-label="Memory timeline" min={0} max={events.length} value={visibleCursor} onChange={(e) => retrace(Number(e.target.value))} /><button className="icon-button" aria-label="Next memory event" disabled={visibleCursor === events.length} onClick={() => retrace(visibleCursor + 1)}><ArrowRight size={16} /></button>
          <button className="live-button" onClick={returnLive}>{cursor === null ? "Live" : "Return to live"}</button></div>
      </section> : null}
      <nav className="scene-dock" aria-label="Scene controls">
        <button className="demo-button" disabled={!ready || tourStep !== null} onClick={startTour}><Play size={16} fill="currentColor" />{tourStep !== null ? "Running…" : "Run demo"}</button>
        <span className="dock-divider" />
        <button className="icon-button" aria-label={playing ? "Pause the scene" : "Play the scene"} onClick={() => { setClipSeek(undefined); setPlaying(!playing); }}>{playing ? <Pause size={17} /> : <Play size={17} />}</button>
        <button className={timelineOpen ? "selected" : ""} aria-expanded={timelineOpen} onClick={() => setTimelineOpen(!timelineOpen)}><History size={17} />{cursor === null ? "Retrace" : "Retracing"}</button>
        <select value={speed} aria-label="Playback speed" onChange={(e) => setSpeed(Number(e.target.value))}><option value={.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option></select>
      </nav>
    </div>
    {storageError ? <div className="storage-notice" role="status">{storageError}</div> : null}
    <dialog ref={helpRef} className="help-dialog" onCancel={() => setHelpOpen(false)} onClose={() => setHelpOpen(false)}>
      <div className="panel-heading"><h2>Welcome upstairs.</h2><button className="icon-button" aria-label="Close preview guide" onClick={() => setHelpOpen(false)}><X size={18} /></button></div>
      <p>Drag to orbit. Scroll to zoom. Click a cabinet to inspect its memories.</p><p>Run the demo, then retrace a memory’s history.</p>
      <p className="help-disclosure">Scripted preview, saved in this browser. Live inference and shared storage are not connected yet.</p>
    </dialog>
  </main>;
}
