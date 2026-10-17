"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Clapperboard, Download, FileSearch, FolderOpen, MessageCircle, Pause, Play, RotateCcw, X, ZoomIn, ZoomOut } from "lucide-react";
import { demoStepCount, demoStepTitles, demoView, exportDemoView, stepReader } from "@/lib/correctness-demo";
import { cinematicsAt } from "@/lib/scene-animation";
import { companyScope, memberName } from "@/lib/sample-company";
import { createDeskSessions, initialDeskId, resetDesk, type DeskId } from "@/lib/desk-sessions";
import { MemberSelect } from "./member-select";
import { TierMemoryPanel } from "./tier-memory-panel";
import type { MemoryScope } from "@/lib/memory";
import { SessionFilePanel } from "./session-file-panel";
import { SessionChatDialog } from "./session-chat-dialog";
import type { SceneHandle } from "./brain/brain-scene";

const BrainScene = dynamic(() => import("./brain/brain-scene"), { ssr: false });
const SceneChat = dynamic(() => import("./scene-chat"), { ssr: false });
const previewMemories = {};
const noop = () => {};

export function CorrectnessDemo() {
  const [step, setStep] = useState(0);
  const [desks, setDesks] = useState(createDeskSessions);
  const [activeDesk, setActiveDesk] = useState<DeskId>(initialDeskId);
  const reader = desks.find((desk) => desk.id === activeDesk)!.reader;
  const [playing, setPlaying] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [progress, setProgress] = useState(.62);
  const [seek, setSeek] = useState({ value: .62, revision: 0 });
  const [panel, setPanel] = useState<"evidence" | "session" | "cabinet" | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [loadedDesks, setLoadedDesks] = useState<DeskId[]>([]);
  const [chatFileOpen, setChatFileOpen] = useState(false);
  const [cabinetScope, setCabinetScope] = useState<MemoryScope>("team");
  const [sourceId, setSourceId] = useState<string>();
  const camera = useRef<SceneHandle | null>(null);
  const evidenceButton = useRef<HTMLButtonElement>(null);
  const sessionButton = useRef<HTMLButtonElement>(null);
  const chatButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const views = useMemo(() => desks.map((desk) => demoView(step, desk.reader)), [step, desks]);
  const view = views[desks.findIndex((desk) => desk.id === activeDesk)];
  const selectedSource = view.sources.find((source) => source.id === sourceId);
  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => { setReducedMotion(media.matches); if (media.matches) setPlaying(false); };
    update(); media.addEventListener("change", update); return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => { if (panel === "evidence") closeButton.current?.focus(); }, [panel]);
  const onReady = useCallback((handle: SceneHandle) => { camera.current = handle; }, []);
  const onProgress = useCallback((value: number) => { setProgress(value); if (value >= 1) setPlaying(false); }, []);
  function go(index: number) {
    setStep(index); setSourceId(undefined);
    const suggested = stepReader(index), existing = desks.find((desk) => desk.reader === suggested);
    if (existing) setActiveDesk(existing.id);
    else setDesks((current) => resetDesk(current, activeDesk, suggested));
    setPlaying(!reducedMotion); setSeek({ value: reducedMotion ? .62 : 0, revision: Date.now() });
  }
  function closePanel() { setPanel(null); (panel === "evidence" ? evidenceButton : sessionButton).current?.focus(); }
  function openChat(file = false, id = activeDesk) { setActiveDesk(id); setPanel(null); setSourceId(undefined); setPlaying(false); setLoadedDesks((current) => current.includes(id) ? current : [...current, id]); setChatFileOpen(file); setChatOpen(true); }
  function exportView() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(exportDemoView(step, reader), null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `rusty-rod-step-${step + 1}-${reader.split("/").at(-1)}.json`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <main className="app-shell correctness-demo" data-dramatic={cinematicsAt(view.cue?.action, progress).darkness > .5 ? view.cue?.action : undefined}>
    <section className="scene-view" aria-label="Rusty Rod memory office"><BrainScene playing={playing} reducedMotion={reducedMotion} speed={1} cue={view.cue} seek={seek} onProgress={onProgress} reader={reader}
      sessions={desks.map((desk, index) => ({ label: views[index].sessionFile.member.name.split(" ")[0], status: "Demo session", working: playing, selected: desk.id === activeDesk, onOpen: () => openChat(false, desk.id), onFile: () => openChat(true, desk.id) }))}
      selectedScope={panel === "cabinet" ? cabinetScope : view.cue?.scope ?? "all"} selectedMemory="" onSelect={() => {}} onScope={(scope) => { setCabinetScope(scope); setPanel("cabinet"); }} onWorker={() => setPanel("session")} onReady={onReady} /></section>
    <header className="floating-header"><a className="brand" href="/" aria-label="BrainBob home"><span className="bob-mark" aria-hidden="true"><i /><i /><b /><em /></span>BrainBob</a><span className="connection-state">Rusty Rod · scripted demo</span></header>
    <div className="panel-launchers"><a className="rehearsal-link" href="/rehearsal" aria-label="Open animation playground"><Clapperboard size={18} /><span>Animations</span></a>
      <button ref={chatButton} aria-label="Open personalized chat" aria-haspopup="dialog" onClick={() => openChat()}><MessageCircle size={18} /><span>Chat</span></button>
      <button ref={sessionButton} aria-label="Open session file" aria-expanded={panel === "session"} onClick={() => panel === "session" ? closePanel() : setPanel("session")}><FolderOpen size={18} /><span>Session file</span></button>
      <button ref={evidenceButton} aria-label="Scenario evidence" aria-expanded={panel === "evidence"} onClick={() => panel === "evidence" ? closePanel() : setPanel("evidence")}><FileSearch size={18} /><span>Evidence</span></button></div>
    <MemberSelect value={reader} onChange={(value) => { setDesks((current) => resetDesk(current, activeDesk, value)); setPanel(null); setSourceId(undefined); setPlaying(false); setSeek({ value: .62, revision: Date.now() }); }} onNewSession={() => { setDesks((current) => resetDesk(current, activeDesk)); openChat(); }}
      sessions={desks.map((desk, index) => ({ label: views[index].sessionFile.member.name, selected: desk.id === activeDesk, onOpen: () => openChat(false, desk.id) }))} />
    {desks.map((desk, index) => <SessionChatDialog key={desk.id} open={chatOpen && desk.id === activeDesk} reader={desk.reader} onClose={() => setChatOpen(false)} returnFocus={chatButton} preview fileOpen={chatFileOpen} onFile={() => setChatFileOpen(!chatFileOpen)}
      inspection={chatFileOpen && desk.id === activeDesk ? <SessionFilePanel key={views[index].sessionFile.id} file={views[index].sessionFile} onClose={() => setChatFileOpen(false)} onTier={(scope) => { setChatOpen(false); setCabinetScope(scope); setPanel("cabinet"); }} onHistory={() => { setChatOpen(false); setPanel("evidence"); }} /> : null}>
      {loadedDesks.includes(desk.id) ? <SceneChat key={`${views[index].sessionFile.id}:${desk.revision}`} reader={desk.reader} readOnly={false} memories={previewMemories} previewFile={views[index].sessionFile} onAnswer={noop} onInspect={noop} onSessionActivity={noop} /> : null}
    </SessionChatDialog>)}
    {panel === "cabinet" ? <TierMemoryPanel key={`${cabinetScope}-${reader}`} scope={cabinetScope} reader={reader} records={view.records} onClose={closePanel} onSession={() => setPanel("session")} onEvidence={(id) => { setSourceId(id); setPanel("evidence"); }} /> : null}
    {panel === "session" ? <SessionFilePanel key={view.sessionFile.id} file={view.sessionFile} onTier={(scope) => { setCabinetScope(scope); setPanel("cabinet"); }} onClose={closePanel} onHistory={() => setPanel("evidence")} /> : null}
    {panel === "evidence" ? <aside className="floating-panel inspector-panel demo-evidence" aria-label="Scenario evidence" onKeyDown={(event) => { if (event.key === "Escape") closePanel(); }}>
      <div className="panel-heading"><div><FileSearch size={18} /><h2>Memory correctness</h2></div><button ref={closeButton} className="icon-button" aria-label="Close scenario evidence" onClick={closePanel}><X size={18} /></button></div>
      <div className="panel-scroll">
        <p className="demo-mode-note">Scripted fixture · no inference. Member filtering previews the policy; server access enforcement is still required.</p>
        <div className="demo-commitment"><small>Approved Atlas commitment</small><strong>{view.currentCommitment}</strong></div>
        <div className="demo-signals"><div><small>Evidence correctness</small><p>{view.decision}</p></div><div><small>Leave-one-out usefulness</small><p>Not run · helpful does not mean factual</p></div></div>
        {view.answer ? <section className="demo-answer"><small>{view.answer.agent} · scripted answer</small><p>{view.answer.text}</p><div>{view.answer.citedIds.map((id) => <button key={id} onClick={() => setSourceId(view.records.find((record) => record.id === id)?.sourceId)}>{id}</button>)}</div></section> : null}
        {view.audit ? <details open><summary>Recent-conversation sample</summary><p className="demo-mode-note">Seed {view.audit.seed} · {view.audit.selectedIds.length} of latest {view.audit.eligibleIds.length} eligible conversations. Demonstration seed, not a benchmark score.</p><p>Approval evidence covered: <strong>{view.audit.decisiveEvidenceCovered ? "Yes" : "No"}</strong></p><p>{view.audit.judgment}</p><details><summary>Selected IDs and cutoff</summary><p className="demo-mode-note">{view.audit.cutoff}</p><code className="demo-ids">{view.audit.selectedIds.join("\n")}</code></details></details> : null}
        <details open><summary>Records in this member’s view</summary><div className="demo-records">{view.records.map((record) => <button key={record.id} onClick={() => setSourceId(record.sourceId)}>
          <span>{record.status} · {companyScope(record.scope)?.label} · v{record.revision}</span><strong>{record.text}</strong><small>{record.id}{record.supersedes ? ` ← ${record.supersedes}` : ""}</small>
        </button>)}</div></details>
        {selectedSource ? <section className="demo-source" aria-label="Selected evidence"><small>{selectedSource.id} · {selectedSource.at}</small><blockquote>{selectedSource.text}</blockquote><p>{memberName(selectedSource.author)} · {selectedSource.authority}</p></section> : null}
        <details><summary>Decision sources</summary>{view.sourceIds.length ? view.sourceIds.map((id) => <button className="revision-item" key={id} onClick={() => setSourceId(id)}>{id}</button>) : <p className="demo-mode-note">No decision sources available in this view.</p>}</details>
        <details><summary>Company and measurement status</summary><p>Rusty Rod serves Atlas Harbor, a fictional logistics client. Three cabinets represent Individual, Team, and Organization. Their drawers separate people, teams, and organizations. Each file combines relevant individual, team, and organization context from the 22 internal scopes.</p><p>The client relationship grants no access to private client data. Executive members have no automatic access to other teams. The six BrainBobs depict worker roles, not headcount.</p><p>Model attribution: none; all steps are scripted. Pipeline cost and maintained-memory improvement are not measured here.</p></details>
      </div><div className="panel-footer"><button onClick={exportView}><Download size={14} />Export this view</button><span>Fixture evidence only</span></div>
    </aside> : null}
    <div className="camera-controls"><button className="icon-button" aria-label="Zoom in" onClick={() => camera.current?.zoom(1.15)}><ZoomIn size={18} /></button><button className="icon-button" aria-label="Zoom out" onClick={() => camera.current?.zoom(1 / 1.15)}><ZoomOut size={18} /></button></div>
    <div className="bottom-controls demo-controls"><div className="clip-caption" role="status"><span>SCRIPTED SCENARIO · {step + 1} / {demoStepCount}</span><strong>{view.title}</strong><small>{view.detail}</small></div>
      <nav className="scene-dock" aria-label="Correctness walkthrough"><button aria-label="Previous scenario step" disabled={step === 0} onClick={() => go(step - 1)}><ArrowLeft size={17} /></button>
        <select aria-label="Scenario step" value={step} onChange={(event) => go(Number(event.target.value))}>{demoStepTitles.map((title, index) => <option key={title} value={index}>{index + 1}. {title}</option>)}</select>
        <button aria-label={playing ? "Pause animation" : "Replay animation"} disabled={reducedMotion || !view.cue} onClick={() => { if (playing) setPlaying(false); else { setSeek({ value: 0, revision: Date.now() }); setPlaying(true); } }}>{playing ? <Pause size={16} /> : <RotateCcw size={16} />}</button>
        <button className="demo-button" aria-label={step === demoStepCount - 1 ? "Restart scenario" : "Next scenario step"} onClick={() => go(step === demoStepCount - 1 ? 0 : step + 1)}>{step === demoStepCount - 1 ? <Play size={16} /> : <ArrowRight size={17} />}<span>{step === demoStepCount - 1 ? "Restart" : "Next"}</span></button>
      </nav>
    </div>
  </main>;
}
