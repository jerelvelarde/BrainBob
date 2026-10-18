"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import { clipPhase, sceneClips, type SceneCue, type SceneAction } from "@/lib/scene-animation";
import type { MemoryScope } from "@/lib/memory";
import styles from "./page.module.css";

const BrainScene = dynamic(() => import("@/components/brain/brain-scene"), { ssr: false });
const noop = () => {};
const scenes: { id: string; action: SceneAction; name: string; event: string; description: string; seconds?: number; evaluation?: SceneCue["evaluation"] }[] = [
  { id: "create", action: "created", name: "Create", event: "memory.added", description: "Bob writes a new record, carries it to the right cabinet, and files it." },
  { id: "retrieve", action: "retrieved", name: "Retrieve", event: "memory.retrieved", description: "Bob finds a permitted record and brings its file back to the task desk." },
  { id: "update", action: "updated", name: "Update", event: "memory.added + supersedes", description: "Pull the old record, write the correction, and file the new version. The previous record stays in history." },
  { id: "retire", action: "forgotten", name: "Retire / delete", event: "memory.retired", description: "Papers fly into the shredder as cartoon fire fills the office. Only the selected memory is retired; its history remains." },
  { id: "session", action: "retrieved", name: "Session file", event: "session context returned", description: "A runner brings a tabbed file to Maya’s desk. A real session combines relevant, accessible individual, team, and organization context." },
  { id: "evaluator-enter", action: "evaluated", name: "Evaluator enters", event: "evaluation.started", description: "Evaluator Bob enters from the open side of the room. This preview makes no evaluation claim.", seconds: 7, evaluation: { phase: "start" } },
  { id: "evaluator-check", action: "evaluated", name: "Check a citation", event: "memory.checked", description: "A cited record travels to the evaluator. This sample shows an unchanged check: no correctness flip.", seconds: 6, evaluation: { phase: "check", verdict: "unchanged" } },
  { id: "evaluator-exit", action: "evaluated", name: "Evaluator leaves", event: "evaluation.finished", description: "The evaluator leaves after the checks. Evaluation visits the task’s cited memories, not every record in the office.", seconds: 5, evaluation: { phase: "finish" } },
  { id: "promote", action: "promoted", name: "Promote", event: "memory.promoted", description: "A golden record rises toward the trusted shelf. Promotion changes status, not the content of the claim." },
  { id: "flag", action: "flagged", name: "Flag", event: "memory.flagged", description: "A red flag marks a concern for the recorded owner. The locked memory stays present while it awaits review." },
  { id: "lock", action: "locked", name: "Lock", event: "memory.locked", description: "A padlock marks an owner-protected record. Harmful locked memories are flagged rather than automatically retired." },
  { id: "resolve", action: "resolved", name: "Owner keeps it", event: "memory.resolved · keep", description: "The owner keeps a flagged record. Other owner decisions may instead correct or retire it." },
  { id: "reject", action: "rejected", name: "Reject", event: "memory.rejected", description: "The incoming paper bounces back. Rejected candidates do not become new active memories." },
  { id: "arrive", action: "arrived", name: "Conversation", event: "episode.ingested", description: "A conversation sheet arrives. This cue represents recorded ingestion; backend event order is preserved in the live workspace." },
  { id: "answer", action: "answered", name: "Answer", event: "answer.produced", description: "Bob delivers the answer packet with its source records. The actual answer and citations appear in chat." },
];

export default function AnimationLibrary() {
  const [selected, setSelected] = useState("update");
  const [scope, setScope] = useState<MemoryScope>("team");
  const [revision, setRevision] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [seek, setSeek] = useState<{ value: number; revision: number }>();
  const [reducedMotion, setReducedMotion] = useState(false);
  const scene = scenes.find((item) => item.id === selected)!;
  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(media.matches);
    update(); media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  const cue = useMemo<SceneCue>(() => ({
    id: `preview-${selected}-${scope}-${revision}`, action: scene.action, scope,
    title: scene.name, source: "fixture", seconds: scene.seconds, evaluation: scene.evaluation,
    records: scene.evaluation ? [{ id: "preview-cited-record", scope }] : undefined,
    ...(selected === "session" ? { destination: [-3.6, .9] as [number, number], noticeLabel: "Gathering Maya’s session file" } : {}),
  }), [selected, scope, revision, scene]);
  const onProgress = useCallback((value: number) => setProgress(value), []);
  function choose(id: string) { setSelected(id); setPlaying(false); setProgress(0); setSeek(undefined); setRevision((r) => r + 1); }
  function play() { setSeek(undefined); setProgress(0); setRevision((r) => r + 1); setPlaying(true); }
  const seconds = scene.seconds ?? sceneClips[scene.action].seconds;
  return <main className={styles.library}>
    <header className={styles.header}><a href="/">← BrainBob</a><span>Animation library</span><strong>Isolated preview · no memory changes</strong></header>
    <div className={styles.content}>
      <section className={styles.stage} aria-label="Animation preview">
        <div className={styles.heading}><span>MEMORY IN MOTION</span><h1>{scene.name}</h1></div>
        <BrainScene playing={playing} reducedMotion={reducedMotion} speed={1} cue={cue} seek={seek} onProgress={onProgress}
          selectedScope={scope} selectedMemory="" onSelect={noop} onScope={setScope} onWorker={noop} onReady={noop} />
        <div className={styles.caption}><strong>{selected === "session" ? "A file for Maya’s session" : clipPhase(scene.action, progress)}</strong><span>{scene.description}</span></div>
      </section>
      <aside className={styles.controls}>
        <p className={styles.kicker}>Same renderer. Every operation.</p>
        <div className={styles.scenes}>{scenes.map((item) => <button key={item.id} onClick={() => choose(item.id)} aria-pressed={selected === item.id}>{item.name}</button>)}</div>
        <label className={styles.scope}>Cabinet<select value={scope} onChange={(e) => { setScope(e.target.value as MemoryScope); setRevision((r) => r + 1); setPlaying(false); setSeek(undefined); }}><option value="individual">Individual · Maya</option><option value="team">Team · Sales</option><option value="organization">Organization · Rusty Rod</option></select></label>
        <div className={styles.transport}><button onClick={play}>Play from start</button><button onClick={() => setPlaying((p) => !p)}>{playing ? "Pause" : "Resume"}</button></div>
        <label className={styles.scrub}>Scene position · {Math.round(progress * seconds)} / {seconds}s<input type="range" aria-label="Scene position" min="0" max="100" value={Math.round(progress * 100)} onChange={(e) => { setPlaying(false); setSeek({ value: Number(e.target.value) / 100, revision: Date.now() }); }} /></label>
        <code>{scene.event}</code>
        <p className={styles.note}>Preview cues only. No API calls, stored records, task grades, or authorization decisions are created here.{reducedMotion ? " Reduced motion is enabled; use the scrubber to inspect each pose." : ""}</p>
      </aside>
    </div>
  </main>;
}
