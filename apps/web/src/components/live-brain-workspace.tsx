"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FolderClosed, FolderOpen, History, Maximize2, MessageCircle, Pause, Play, SkipForward, X, ZoomIn, ZoomOut } from "lucide-react";
import { canRead, sceneScope, scopeLabel, type BackendAnswer, type StoredEvent } from "@/lib/brain-api";
import { memberForReader, memberId, teamForReader } from "@/lib/sample-company";
import { sessionStatus, type ActiveSession, type SessionActivity } from "@/lib/active-session";
import { createDeskSessions, initialDeskId, recordDeskActivity, resetDesk, type DeskId, type LocalDeskSession } from "@/lib/desk-sessions";
import type { DeskSession } from "./brain/session-worker";
import { MemberSelect } from "./member-select";
import { cuesForEvent, eventDescription, eventMemoryIds, memoriesAt, type BackendState } from "@/lib/backend-state";
import { cinematicsAt, type SceneCue } from "@/lib/scene-animation";
import { useBrainBackend } from "@/lib/use-brain-backend";
import { LiveMemoryPanel } from "./live-memory-panel";
import { LiveSessionPanel } from "./live-session-panel";
import { SessionChatDialog } from "./session-chat-dialog";
import { SessionBrainPanel } from "./session-brain-panel";
import { MemoryCabinetBrowser } from "./memory-cabinet-browser";
import { deskDestinations, sessionFileCues } from "@/lib/session-scene";
import type { MemoryScope } from "@/lib/memory";
import type { SceneHandle } from "./brain/brain-scene";

const BrainScene = dynamic(() => import("./brain/brain-scene"), { ssr: false });
const SceneChat = dynamic(() => import("./scene-chat"), { ssr: false, loading: () => <p className="chat-loading">Opening chat…</p> });

export function LiveBrainWorkspace() {
  const [desks, setDesks] = useState(createDeskSessions);
  const [selection, setSelection] = useState({ id: initialDeskId, token: 0, chat: false, file: false });
  const openDesk = useCallback((id: DeskId, file = false) => setSelection((current) => ({ id, token: current.token + 1, chat: true, file })), []);
  const activity = useCallback((id: DeskId, revision: number, event: SessionActivity) => setDesks((current) => recordDeskActivity(current, id, revision, event)), []);
  const sceneSessions = useMemo(() => desks.map((desk) => ({ label: memberForReader(desk.reader)?.label.split(" ")[0] ?? "Bob", status: sessionStatus(desk.session), working: desk.session?.status === "working", selected: desk.id === selection.id, onOpen: () => openDesk(desk.id), onFile: () => openDesk(desk.id, true) })), [desks, selection.id, openDesk]);
  return desks.map((desk) => <MemberWorkspace key={`${desk.id}:${desk.revision}`} desk={desk} active={desk.id === selection.id} sessions={sceneSessions}
    openRequest={selection.chat && desk.id === selection.id ? { token: selection.token, file: selection.file } : undefined}
    onReaderChange={(reader) => { setDesks((current) => resetDesk(current, desk.id, reader)); setSelection((current) => ({ ...current, token: current.token + 1, chat: true, file: false })); }}
    onNewSession={() => { setDesks((current) => resetDesk(current, desk.id)); openDesk(desk.id); }} onActivity={activity} />);
}

// Each desk keeps its own agent and identity-bound state. Only the selected desk renders a canvas.
function MemberWorkspace({ desk, active, sessions, openRequest, onReaderChange, onNewSession, onActivity }: {
  desk: LocalDeskSession; active: boolean; sessions: DeskSession[]; openRequest?: { token: number; file: boolean };
  onReaderChange: (reader: string) => void; onNewSession: () => void; onActivity: (id: DeskId, revision: number, event: SessionActivity) => void;
}) {
  const { reader, session } = desk;
  const startChat = active && Boolean(openRequest);
  const activeRef = useRef(active);
  const readerRef = useRef(reader);
  const [panel, setPanel] = useState<"chat" | "memory" | null>(startChat ? "chat" : null);
  const [chatInspection, setChatInspection] = useState<"session" | "memory" | null>(null);
  const [chatLoaded, setChatLoaded] = useState(startChat);
  const [selected, setSelected] = useState<string>();
  const [queue, setQueue] = useState<SceneCue[]>([]);
  const [playing, setPlaying] = useState(true);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [progress, setProgress] = useState(0);
  const [cursor, setCursor] = useState<number | null>(null);
  const cursorRef = useRef(cursor);
  const [retraceCue, setRetraceCue] = useState<SceneCue>();
  const [seek, setSeek] = useState<{ value: number; revision: number }>();
  const [timelineOpen, setTimelineOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const [chatSnapshot, setChatSnapshot] = useState<ActiveSession | null>(null);
  const [cabinetTier, setCabinetTier] = useState<MemoryScope | null>(null);
  const sessionFileLoaded = useRef(false);
  const [citations, setCitations] = useState<string[]>([]);
  const chatButton = useRef<HTMLButtonElement>(null), memoryButton = useRef<HTMLButtonElement>(null);
  const sessionButton = useRef<HTMLButtonElement>(null);
  const camera = useRef<SceneHandle | null>(null);
  useEffect(() => { activeRef.current = active; if (!active) setQueue([]); }, [active]);
  useEffect(() => {
    if (active && openRequest) { setChatSnapshot(null); setChatLoaded(true); setChatInspection(openRequest.file ? "session" : null); setPanel("chat"); }
  }, [active, openRequest?.token, openRequest?.file]);
  const onLive = useCallback((event: StoredEvent, state: BackendState) => {
    if (!activeRef.current || cursorRef.current !== null) return;
    const cues = cuesForEvent(event, state, readerRef.current);
    if (cues.length) setQueue((current) => [...current, ...cues]);
  }, []);
  const backend = useBrainBackend(memberId(reader), onLive, active);
  useEffect(() => {
    if (!active || panel !== "chat" || !backend.contextLoaded || sessionFileLoaded.current) return;
    sessionFileLoaded.current = true;
    const cues = sessionFileCues(Object.values(backend.state.memories), reader, `${desk.id}-${desk.revision}`, desk.id);
    if (!reducedMotion) setQueue((current) => [...current, ...cues]);
  }, [active, panel, backend.contextLoaded, backend.state.memories, reader, desk.id, desk.revision, reducedMotion]);
  // The records and activity feed update immediately even when animation is disabled.
  useEffect(() => { if (reducedMotion && queue.length) setQueue([]); }, [reducedMotion, queue.length]);
  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => { setReducedMotion(media.matches); if (media.matches) setPlaying(false); };
    update(); media.addEventListener("change", update); return () => media.removeEventListener("change", update);
  }, []);
  const displayed = useMemo(() => cursor === null ? backend.state.memories : memoriesAt(backend.state.events, cursor), [backend.state, cursor]);
  const visibleMemories = useMemo(() => Object.values(displayed).filter((m) => canRead(m.scope, reader)), [displayed, reader]);
  const visibleEvents = useMemo(() => backend.state.events.filter((e) => eventMemoryIds(e, backend.state.events).some((id) => backend.state.memories[id] && canRead(backend.state.memories[id].scope, reader))), [backend.state, reader]);
  const cue = cursor !== null ? retraceCue : queue[0];
  useEffect(() => { setProgress(0); }, [cue?.id]);
  const onProgress = useCallback((value: number) => {
    setProgress(value);
    if (value >= 1 && cursorRef.current === null) { setQueue((current) => current.slice(1)); setSeek(undefined); }
  }, []);
  const onReady = useCallback((handle: SceneHandle) => { camera.current = handle; }, []);
  const inspect = useCallback((id?: string) => { setSelected(id); setPanel("memory"); }, []);
  const onAnswer = useCallback((answer: BackendAnswer) => { setCitations(answer.cited_ids); }, []);
  const onSessionActivity = useCallback((event: SessionActivity) => onActivity(desk.id, desk.revision, event), [onActivity, desk.id, desk.revision]);
  function closePanel() { const previous = panel; setPanel(null); (previous === "chat" ? chatButton : memoryButton).current?.focus(); }
  function openChat(file = false) { setChatSnapshot(null); setChatLoaded(true); setChatInspection(file ? "session" : null); setPanel("chat"); }
  function inspectInChat(id: string) { setSelected(id); setChatInspection("memory"); }
  function openCabinet(scope: MemoryScope) { setCabinetTier(scope); if (panel === "chat") setChatInspection(null); else { setSelected(undefined); setPanel("memory"); } }
  function retrace(seq: number) {
    const event = backend.state.events.find((e) => e.seq === seq);
    if (!event) { setNotice("This event is not in the loaded log yet."); return; }
    cursorRef.current = seq; setCursor(seq); setQueue([]); setPlaying(false); setTimelineOpen(true);
    setRetraceCue(cuesForEvent(event, backend.state, reader)[0]); setSeek({ value: .62, revision: Date.now() });
    setNotice(eventDescription(event));
  }
  function live() { cursorRef.current = null; setCursor(null); setRetraceCue(undefined); setQueue([]); setSeek(undefined); setNotice(""); setPlaying(!reducedMotion); }
  function changeReader(value: string) { readerRef.current = value; onReaderChange(value); setSelected(undefined); setCitations([]); live(); }
  const shownEvent = cursor === null ? undefined : backend.state.events.find((e) => e.seq === cursor);
  const inspection = chatInspection === "session" ? <LiveSessionPanel key={(chatSnapshot ?? session)?.taskId ?? "saved"} reader={reader} session={chatSnapshot ?? session} memories={visibleMemories} onClose={() => setChatInspection(null)} onInspect={inspectInChat} />
    : chatInspection === "memory" ? <LiveMemoryPanel actor={memberId(reader)} memories={visibleMemories} selected={selected} events={backend.state.events.filter((e) => cursor === null || e.seq <= cursor)} readOnly={cursor !== null} citedIds={citations} onSelect={setSelected} onClose={() => setChatInspection(null)} onRetrace={(seq) => { closePanel(); retrace(seq); }} /> : null;
  const scene = active ? <BrainScene playing={playing} speed={1} reducedMotion={reducedMotion} cue={cue ? { ...cue, destination: deskDestinations[desk.id] } : undefined} seek={seek} onProgress={onProgress} reader={reader}
    sessions={sessions} memories={visibleMemories} selectedScope={cue?.scope ?? cabinetTier ?? "all"} selectedMemory={selected ?? ""}
    flaggedScopes={[...new Set(visibleMemories.filter((m) => m.flagged).flatMap((m) => { const scope = sceneScope(m.scope); return scope ? [scope] : []; }))]}
    onSelect={() => {}} onScope={openCabinet} onWorker={() => { if (panel === "chat") setChatInspection("session"); else inspect(); }} onReady={onReady} /> : null;

  return <main className="app-shell desk-workspace" hidden={!active} data-dramatic={cinematicsAt(cue?.action, progress).darkness > .5 ? cue?.action : undefined}>
    {active && panel !== "chat" ? <section className="scene-view" aria-label="Brain visualization">{scene}</section> : null}
    <header className="floating-header"><a className="brand" href="/" aria-label="BrainBob home"><span className="bob-mark" aria-hidden="true"><i /><i /><b /><em /></span><span>BrainBob</span></a>
      <span className={`connection-state ${backend.connection}`} role="status">{backend.connection === "live" ? "Connected" : backend.connection === "syncing" ? "Loading history…" : backend.connection === "offline" ? "Backend offline" : "Connecting…"}</span>
    </header>
    <div className="panel-launchers">
      <button ref={sessionButton} aria-label="Open active session file" aria-expanded={panel === "chat" && chatInspection === "session"} onClick={() => openChat(true)}><FolderOpen size={18} /><span>Session</span></button>
      <button ref={chatButton} aria-label="Chat" aria-haspopup="dialog" aria-expanded={panel === "chat"} className={panel === "chat" ? "selected" : ""} onClick={() => openChat()}><MessageCircle size={18} /><span>Chat</span></button>
      <button ref={memoryButton} aria-label="Memories" aria-expanded={panel === "memory"} className={panel === "memory" ? "selected" : ""} onClick={() => panel === "memory" ? closePanel() : inspect()}><FolderClosed size={18} /><span>Memories</span></button>
    </div>
    <MemberSelect value={reader} onChange={changeReader} onNewSession={onNewSession} autoFocus={active && desk.revision > 0 && !startChat}
      sessions={sessions.map((item) => ({ label: item.label, selected: item.selected, onOpen: item.onOpen }))} />
    <SessionChatDialog open={active && panel === "chat"} reader={reader} onClose={closePanel} returnFocus={chatButton} fileOpen={chatInspection !== null} onCloseInspection={() => setChatInspection(null)}
      onFile={() => { setChatSnapshot(null); setChatInspection(chatInspection ? null : "session"); }}
      inspection={inspection}
      brain={(onClose) => <SessionBrainPanel scene={panel === "chat" ? scene : null} cue={cue} progress={progress} queueLength={queue.length} playing={playing} reducedMotion={reducedMotion}
        connected={backend.connection === "live"} loaded={backend.contextLoaded} reader={reader} memories={visibleMemories} events={visibleEvents} tier={cabinetTier}
        onTier={setCabinetTier} onInspect={inspectInChat} onPause={() => setPlaying(!playing)} onSkip={() => { setQueue((current) => current.slice(1)); setSeek(undefined); }}
        onFile={() => { setChatSnapshot(null); setChatInspection("session"); }} onClose={onClose} inspection={inspection} />}>
      {chatLoaded ? <SceneChat key={reader} reader={reader} connected={backend.connection === "live"} readOnly={cursor !== null} memories={backend.state.memories} onAnswer={onAnswer} onInspect={inspectInChat} onExploreMemory={(snapshot) => { setChatSnapshot(snapshot); setChatInspection("session"); }} onSessionActivity={onSessionActivity} /> : null}
    </SessionChatDialog>
    {panel === "memory" ? selected ? <LiveMemoryPanel key={reader} actor={memberId(reader)} memories={visibleMemories} selected={selected} events={backend.state.events.filter((e) => cursor === null || e.seq <= cursor)} readOnly={cursor !== null} citedIds={citations} onSelect={setSelected} onClose={closePanel} onRetrace={retrace} />
      : <aside className="floating-panel inspector-panel" aria-label="Memory cabinets"><div className="panel-heading"><h2>Memory cabinets</h2><button className="icon-button" aria-label="Close cabinets" onClick={closePanel}><X size={18} /></button></div><div className="panel-scroll"><MemoryCabinetBrowser reader={reader} memories={visibleMemories} tier={cabinetTier} onTier={setCabinetTier} onInspect={setSelected} /></div></aside> : null}
    <div className="camera-controls"><button className="icon-button" aria-label="Zoom in" onClick={() => camera.current?.zoom(1.15)}><ZoomIn size={18} /></button><button className="icon-button" aria-label="Zoom out" onClick={() => camera.current?.zoom(1 / 1.15)}><ZoomOut size={18} /></button><button className="icon-button" aria-label="Reset isometric camera" onClick={() => camera.current?.reset()}><Maximize2 size={18} /></button></div>
    <div className="bottom-controls">
      {backend.error ? <p className="scene-notice" role="alert">{backend.error}</p> : null}
      {cue ? <div className="clip-caption" role="status"><span>{cursor !== null ? "RECORDED EVENT" : "BACKEND EVENT"} · {teamForReader(reader)?.label} · {scopeLabel(reader)}</span><strong>{cue.title}</strong>{queue.length > 1 && cursor === null ? <small>{queue.length - 1} scenes queued</small> : null}{cue.evaluation ? <small>Usefulness check · not a factual correctness verdict</small> : null}</div> : notice ? <div className="scene-notice" role="status">{notice}</div> : null}
      {timelineOpen ? <div className="timeline-panel"><div className="timeline-top"><span>{cursor === null ? "Event history" : `Retracing #${cursor}`}</span><button className="live-button" onClick={live}>Return to live</button></div>
        <select className="event-select" aria-label="Recorded event" value={cursor ?? ""} onChange={(e) => { if (e.target.value) retrace(Number(e.target.value)); }}><option value="">Choose a recorded event</option>{visibleEvents.map((e) => <option value={e.seq} key={e.seq}>#{e.seq} · {eventDescription(e)}</option>)}</select>
        {shownEvent ? <small>{new Date(shownEvent.ts * 1000).toLocaleString()}</small> : null}
      </div> : null}
      <div className="scene-dock" aria-label="Scene controls"><button className="icon-button" aria-label={playing ? "Pause the scene" : "Play the scene"} disabled={reducedMotion} onClick={() => { setSeek(undefined); setPlaying(!playing); }}>{playing ? <Pause size={17} /> : <Play size={17} />}</button>
        <button onClick={() => setTimelineOpen(!timelineOpen)} aria-expanded={timelineOpen}><History size={17} />Retrace</button>
        {queue.length > 0 && cursor === null ? <button aria-label="Skip current animation" onClick={() => { setQueue((current) => current.slice(1)); setSeek(undefined); }}><SkipForward size={17} />Next</button> : null}
        {citations.length ? <button onClick={() => inspect(citations[0])}>{citations.length} cited</button> : null}
      </div>
    </div>
  </main>;
}
