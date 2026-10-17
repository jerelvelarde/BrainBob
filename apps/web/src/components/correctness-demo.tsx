"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Clapperboard, Download, FileSearch, Pause, Play, RotateCcw, X, ZoomIn, ZoomOut } from "lucide-react";
import { demoStepCount, demoStepTitles, demoView, exportDemoView, stepReader } from "@/lib/correctness-demo";
import { cinematicsAt } from "@/lib/scene-animation";
import { companyScope } from "@/lib/sample-company";
import { MemberSelect } from "./member-select";
import type { SceneHandle } from "./brain/brain-scene";

const BrainScene = dynamic(() => import("./brain/brain-scene"), { ssr: false });

export function CorrectnessDemo() {
  const [step, setStep] = useState(0);
  const [reader, setReader] = useState<string>(stepReader(0));
  const [playing, setPlaying] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [progress, setProgress] = useState(.62);
  const [seek, setSeek] = useState({ value: .62, revision: 0 });
  const [panel, setPanel] = useState(false);
  const [sourceId, setSourceId] = useState<string>();
  const camera = useRef<SceneHandle | null>(null);
  const evidenceButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const view = useMemo(() => demoView(step, reader), [step, reader]);
  const selectedSource = view.sources.find((source) => source.id === sourceId);
  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => { setReducedMotion(media.matches); if (media.matches) setPlaying(false); };
    update(); media.addEventListener("change", update); return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => { if (panel) closeButton.current?.focus(); }, [panel]);
  const onReady = useCallback((handle: SceneHandle) => { camera.current = handle; }, []);
  const onProgress = useCallback((value: number) => { setProgress(value); if (value >= 1) setPlaying(false); }, []);
  function go(index: number) {
    setStep(index); setReader(stepReader(index)); setSourceId(undefined);
    setPlaying(!reducedMotion); setSeek({ value: reducedMotion ? .62 : 0, revision: Date.now() });
  }
  function closePanel() { setPanel(false); evidenceButton.current?.focus(); }
  function exportView() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(exportDemoView(step, reader), null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `rusty-rod-step-${step + 1}-${reader.split("/").at(-1)}.json`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <main className="app-shell correctness-demo" data-dramatic={cinematicsAt(view.cue?.action, progress).darkness > .5 ? view.cue?.action : undefined}>
    <section className="scene-view" aria-label="Rusty Rod memory office"><BrainScene playing={playing} reducedMotion={reducedMotion} speed={1} cue={view.cue} seek={seek} onProgress={onProgress} cabinetLabels={view.labels}
      selectedScope={view.cue?.scope ?? "all"} selectedMemory="" onSelect={() => {}} onScope={() => setPanel(true)} onWorker={() => setPanel(true)} onReady={onReady} /></section>
    <header className="floating-header"><a className="brand" href="/" aria-label="BrainBob home"><span className="bob-mark" aria-hidden="true"><i /><i /><b /><em /></span>BrainBob</a><span className="connection-state">Rusty Rod · scripted demo</span></header>
    <div className="panel-launchers"><a className="rehearsal-link" href="/rehearsal" aria-label="Open animation playground"><Clapperboard size={18} /><span>Animations</span></a>
      <button ref={evidenceButton} aria-label="Scenario evidence" aria-expanded={panel} onClick={() => panel ? closePanel() : setPanel(true)}><FileSearch size={18} /><span>Evidence</span></button></div>
    <MemberSelect value={reader} onChange={(value) => { setReader(value); setSourceId(undefined); setPlaying(false); setSeek({ value: .62, revision: Date.now() }); }} />
    {panel ? <aside className="floating-panel inspector-panel demo-evidence" aria-label="Scenario evidence" onKeyDown={(event) => { if (event.key === "Escape") closePanel(); }}>
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
        {selectedSource ? <section className="demo-source" aria-label="Selected evidence"><small>{selectedSource.id} · {selectedSource.at}</small><blockquote>{selectedSource.text}</blockquote><p>{selectedSource.author} · {selectedSource.authority}</p></section> : null}
        <details><summary>Decision sources</summary>{view.sourceIds.length ? view.sourceIds.map((id) => <button className="revision-item" key={id} onClick={() => setSourceId(id)}>{id}</button>) : <p className="demo-mode-note">No decision sources available in this view.</p>}</details>
        <details><summary>Company and measurement status</summary><p>18 members · 3 teams · 22 memory scopes. Each view has organization, own team, and own individual access. Executive members have no automatic access to other teams.</p><p>The six BrainBobs depict worker roles, not the headcount.</p><p>Model attribution: none; all steps are scripted. Pipeline cost and maintained-memory improvement are not measured here.</p></details>
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
