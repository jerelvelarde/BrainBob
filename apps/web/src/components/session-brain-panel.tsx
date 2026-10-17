"use client";

import { useState, type ReactNode } from "react";
import { Check, FolderOpen, Pause, Play, SkipForward, X } from "lucide-react";
import { clipPhase, sceneClips, type SceneCue } from "@/lib/scene-animation";
import { eventDescription, eventMemoryIds } from "@/lib/backend-state";
import type { BackendMemory, StoredEvent } from "@/lib/brain-api";
import type { MemoryScope } from "@/lib/memory";
import { MemoryCabinetBrowser } from "./memory-cabinet-browser";

export function SessionBrainPanel({ scene, cue, progress, queueLength, playing, reducedMotion, connected, loaded, reader, memories, events, tier,
  onTier, onInspect, onPause, onSkip, onFile, onClose, inspection }: {
  scene: ReactNode; cue?: SceneCue; progress: number; queueLength: number; playing: boolean; reducedMotion: boolean;
  connected: boolean; loaded: boolean; reader: string; memories: BackendMemory[]; events: StoredEvent[]; tier: MemoryScope | null;
  onTier: (tier: MemoryScope | null) => void; onInspect: (id: string) => void; onPause: () => void; onSkip: () => void;
  onFile: () => void; onClose?: () => void; inspection?: ReactNode;
}) {
  const [view, setView] = useState<"cabinets" | "activity">("cabinets");
  const label = cue ? cue.source === "session" ? "Session file" : sceneClips[cue.action].label : "Ready";
  return <section className="session-brain-panel" aria-label="Behind the scenes" data-inspecting={Boolean(inspection)}>
    <header className="brain-panel-header"><div><span className={`brain-live-dot ${connected ? "is-live" : ""}`} /><strong>Behind the scenes</strong></div>
      <button aria-label="Open session memory" title="Session memory" onClick={onFile}><FolderOpen size={17} /></button>
      {onClose ? <button className="brain-panel-close" aria-label="Close brain panel" onClick={onClose}><X size={17} /></button> : null}
    </header>
    <div className="session-brain-stage">{scene}</div>
    <div className="brain-activity-current">
      <div className="brain-activity-top"><span>{label}</span><div>
        <button aria-label={playing ? "Pause memory animation" : "Play memory animation"} disabled={reducedMotion} onClick={onPause}>{playing ? <Pause size={13} /> : <Play size={13} />}</button>
        {cue ? <button aria-label="Skip memory animation" onClick={onSkip}><SkipForward size={14} /></button> : null}
      </div></div>
      <p role="status">{cue ? cue.title : !connected ? "Waiting for the brain to connect" : loaded ? "Your context is ready. Ask away." : "Loading your session file…"}</p>
      {cue ? <><small>{reducedMotion ? "Motion reduced · event recorded" : !playing ? "Animation paused" : cue.evaluationLabel ? "Checking source evidence" : cue.noticeLabel ?? clipPhase(cue.action, progress)}{queueLength > 1 ? ` · ${queueLength - 1} queued` : ""}</small><div className="brain-event-progress" aria-hidden="true"><i style={{ transform: `scaleX(${progress})` }} /></div></> : <small>Click a cabinet to explore its memories</small>}
    </div>
    {inspection ? <div className="session-brain-inspection session-chat-inspection">{inspection}</div> : <>
      <div className="brain-panel-tabs" aria-label="Brain panel view"><button aria-pressed={view === "cabinets" || tier !== null} onClick={() => { setView("cabinets"); onTier(null); }}>Cabinets</button><button aria-pressed={view === "activity" && tier === null} onClick={() => { setView("activity"); onTier(null); }}>Activity</button></div>
      <div className="brain-panel-scroll">{view === "cabinets" || tier !== null ? <MemoryCabinetBrowser reader={reader} memories={memories} tier={tier} onTier={onTier} onInspect={onInspect} />
        : <div className="brain-event-list"><p className="brain-history-note">Recorded events · newest first</p>{events.slice(-30).reverse().map((event) => {
          const id = eventMemoryIds(event, events)[0];
          return <button key={event.seq} disabled={!id} onClick={() => id && onInspect(id)}><Check size={13} /><span>{eventDescription(event)}<small>{new Date(event.ts * 1000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</small></span></button>;
        })}{!events.length ? <p className="cabinet-empty">Memory activity will appear here.</p> : null}</div>}</div>
    </>}
  </section>;
}
