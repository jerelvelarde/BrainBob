"use client";

import { useEffect, useRef, type RefObject } from "react";
import { useFrame } from "@react-three/fiber";
import { RoundedBox } from "@react-three/drei";
import * as THREE from "three";
import { BrainBob } from "./brain-bob";
import { Label } from "./scene-label";
import { SessionFolder } from "./session-folder";
import { cinematicsAt, cueCabinetX, isMemoryOperation, memoryOperationAt, performanceForCue, sceneClips, scopeCharacters, type BobPerformance, type SceneCue, type SceneCinematics } from "@/lib/scene-animation";

type Clock = RefObject<{ time: number; progress: number }>;
type StageProps = { cue: SceneCue; playing: boolean; reducedMotion: boolean; speed: number;
  seek?: { value: number; revision: number }; onProgress: (progress: number) => void; cinematics: RefObject<SceneCinematics> };
const clamp = THREE.MathUtils.clamp;
const lerp = THREE.MathUtils.lerp;
const smooth = (a: number, b: number, p: number) => THREE.MathUtils.smoothstep(p, a, b);

function Paper({ color = "#fff9e6" }: { color?: string }) {
  return <group>
    <mesh castShadow><boxGeometry args={[.44, .56, .025]} /><meshStandardMaterial color={color} roughness={1} /></mesh>
    {[-.13, -.04, .05, .14].map((y, i) => <mesh key={y} position={[i === 0 ? -.06 : 0, y, .015]}>
      <planeGeometry args={[i === 0 ? .19 : .31, .022]} /><meshBasicMaterial color="#9788a7" side={THREE.DoubleSide} />
    </mesh>)}
  </group>;
}

function Performer({ index, cue, clock }: { index: number; cue: SceneCue; clock: Clock }) {
  const group = useRef<THREE.Group>(null);
  const performance = useRef<BobPerformance>({ time: 0, distance: 0, walking: false, pose: "idle", expression: "happy", paper: false });
  useFrame(() => {
    const sample = performanceForCue(cue, index, clock.current.progress);
    if (group.current) {
      group.current.position.set(sample.x, .05, sample.z);
      group.current.rotation.y = sample.angle;
    }
    Object.assign(performance.current, { time: clock.current.time, distance: sample.distance,
      walking: sample.moving, pose: sample.pose, expression: sample.expression, paper: sample.paper,
      reaction: index === 4 && cue.evaluation?.verdict ? cue.evaluation.verdict === "unconfirmed" ? "shake" : "nod" : undefined });
  }, -1);
  return <group ref={group}>
    <BrainBob performance={performance} inspector={index === 4} phase={index} />
    {cue.action === "evaluated" && index === 4 ? <Label text="EVALUATOR BOB" position={[0, 1.7, 0]} width={1.85} selected /> : null}
  </group>;
}

function TransferPaper({ cue, clock }: { cue: SceneCue; clock: Clock }) {
  const group = useRef<THREE.Group>(null);
  const x = cueCabinetX(cue);
  useFrame(() => {
    if (!group.current) return;
    const p = clock.current.progress;
    if (isMemoryOperation(cue.action)) {
      const { transfer } = memoryOperationAt(cue, p);
      group.current.visible = transfer.visible;
      group.current.position.set(...transfer.position);
      group.current.rotation.set(transfer.tilt, transfer.angle, -.18, "YXZ");
      group.current.scale.setScalar(.68);
      return;
    }
    group.current.visible = true;
    group.current.rotation.set(0, .4, 0);
    let px = x, py = 1.2, pz = -3.05;
    if (cue.action === "retrieved") {
      group.current.visible = p > .31;
      const move = smooth(.38, .88, p);
      px = lerp(x, cue.destination?.[0] ?? .6, move); pz = lerp(-3, cue.destination?.[1] ?? .9, move); py = lerp(1.3, 1.13, move) + Math.sin(move * Math.PI) * 1.1;
      group.current.rotation.x = -Math.PI / 2 * smooth(.78, .95, p);
    } else if (cue.action === "promoted") {
      py = lerp(1.1, 2.55, smooth(.24, .8, p));
    } else if (cue.action === "rejected") {
      const inwards = smooth(0, .4, p), outwards = smooth(.48, .95, p);
      px = lerp(-1.5, x, inwards) + outwards * 3;
      pz = lerp(2, -3.05, inwards) + outwards * 4;
      py = 1.2 + Math.sin(outwards * Math.PI) * 1.7;
      group.current.rotation.z = -outwards * Math.PI * 2;
    } else if (cue.action === "arrived") {
      const u = smooth(0, .8, p);
      px = lerp(6.5, -1.2, u); pz = lerp(4, .9, u); py = 1.2 + Math.sin(u * Math.PI) * 1.5;
    } else if (cue.action === "answered") {
      const u = smooth(.16, .82, p);
      px = lerp(3.8, .4, u); pz = lerp(-.8, 2.8, u); py = 1.6 + Math.sin(u * Math.PI) * .75;
    } else if (cue.action === "flagged") {
      px = x; py = 1.7;
    } else group.current.visible = false;
    group.current.position.set(px, py, pz);
    group.current.scale.setScalar(cue.action === "answered" ? 1.65 : 1.2);
  });
  return <group ref={group}>{cue.sessionLabel && ["retrieved", "answered"].includes(cue.action) ? <SessionFolder /> : <Paper color={cue.action === "flagged" ? "#f7bbbb" : cue.action === "promoted" ? "#ffe095" : undefined} />}
    {cue.action === "flagged" ? <Label text={cue.noticeLabel ?? "LOCKED · REVIEW"} position={[0, .55, 0]} width={1.8} /> : null}
    {cue.action === "rejected" ? <Label text="RETURN TO SENDER" position={[0, .5, 0]} width={1.8} /> : null}
    {cue.action === "answered" && !cue.sessionLabel ? <Label text="ANSWER + SOURCES" position={[0, .55, 0]} width={1.8} /> : null}
  </group>;
}

function AuditRecords({ cue, clock }: { cue: SceneCue; clock: Clock }) {
  const sheets = useRef<(THREE.Group | null)[]>([]);
  const lens = useRef<THREE.Group>(null);
  const checking = cue.evaluation?.phase === "check";
  const count = cue.records ? Math.min(cue.records.length, 6) : 6;
  const verdict = cue.evaluation?.verdict;
  const label = cue.evaluationLabel ?? (verdict === "helpful" ? "HELPFUL" : verdict === "harmful" ? "HARMFUL" : verdict === "unchanged" ? "NO FLIP" : verdict === "unconfirmed" ? "CONFIRM FAILED · KEPT" : "CHECKS CITED MEMORIES");
  useFrame(() => {
    const p = clock.current.progress;
    sheets.current.forEach((sheet, i) => {
      if (!sheet) return;
      const u = smooth(.12 + i * .045, .56 + i * .045, p);
      const x = cue.records?.[i] ? (cue.records[i].cabinetX ?? scopeCharacters[cue.records[i].scope].x) : [-3.8, -.5, 3.2][i % 3];
      sheet.position.set(checking ? 4.1 + (i % 3) * .33 : lerp(x, 4.1 + (i % 3) * .33, u), checking ? 1.5 : 1.45 + Math.sin(u * Math.PI) * 1.5 + (i > 2 ? .07 : 0), checking ? 2.2 + Math.floor(i / 3) * .45 : lerp(-3, 2.2 + Math.floor(i / 3) * .45, u));
      sheet.rotation.set(checking ? 0 : -u * Math.PI / 2, 0, .12 * Math.sin(i));
      sheet.visible = checking || p > .1 + i * .04;
    });
    if (lens.current) {
      lens.current.position.set(4.35 + Math.sin(clock.current.time * 1.6) * .4, 2.05, 2.2 + Math.cos(clock.current.time * 1.6) * .15);
      lens.current.rotation.z = -.4;
    }
  });
  return <group>
    {Array.from({ length: count }, (_, i) => <group key={i} ref={(g) => { sheets.current[i] = g; }}><Paper color={verdict === "harmful" ? "#f7bbbb" : verdict === "helpful" ? "#c9e3b8" : undefined} /></group>)}
    <group ref={lens}>
      <mesh><torusGeometry args={[.25, .045, 8, 28]} /><meshStandardMaterial color="#7962b2" /></mesh>
      <mesh position={[0, -.42, 0]}><cylinderGeometry args={[.035, .035, .4, 10]} /><meshStandardMaterial color="#7962b2" /></mesh>
      <mesh><circleGeometry args={[.22, 28]} /><meshBasicMaterial color="#bfdded" transparent opacity={.35} side={THREE.DoubleSide} /></mesh>
    </group>
    <Label text={label} position={checking ? [cueCabinetX(cue), 3.15, -2.7] : [3.8, 2.8, -1]} width={2.9} />
  </group>;
}

/** The selected paper reaches the slot before its strips fall out. */
function ShreddedRecord({ cue, clock }: { cue: SceneCue; clock: Clock }) {
  const strips = useRef<(THREE.Mesh | null)[]>([]);
  useFrame(() => {
    const { shredProgress } = memoryOperationAt(cue, clock.current.progress);
    strips.current.forEach((strip, i) => {
      if (!strip) return;
      const u = clamp((shredProgress - i * .025) / .7, 0, 1);
      strip.visible = u > 0 && u < 1;
      strip.position.set(5.8 + (i - 4.5) * .045, .65 - u * .55, 4 + u * .35);
      strip.rotation.set(u * 2, 0, (i - 4.5) * .08);
    });
  });
  return <group>{Array.from({ length: 10 }, (_, i) => <mesh key={i} ref={(mesh) => { strips.current[i] = mesh; }}>
    <boxGeometry args={[.025, .22, .012]} /><meshStandardMaterial color="#fff5da" side={THREE.DoubleSide} />
  </mesh>)}</group>;
}

function ScopeSpotlight({ cue, clock }: { cue: SceneCue; clock: Clock }) {
  const ring = useRef<THREE.Mesh>(null);
  const color = cue.evaluation?.verdict === "harmful" ? "#d66d74" : cue.evaluation?.verdict === "helpful" ? "#81b28c" : scopeCharacters[cue.scope].color;
  useFrame(() => {
    if (ring.current) ring.current.scale.setScalar(1 + Math.sin(clock.current.time * 2) * .035);
  });
  return <group position={[cueCabinetX(cue), .075, -3.5]}>
    <mesh ref={ring} rotation={[-Math.PI / 2, 0, 0]}><ringGeometry args={[.82, 1.02, 48]} /><meshBasicMaterial color={color} transparent opacity={.7} side={THREE.DoubleSide} /></mesh>
  </group>;
}

export function EventStage({ cue, playing, reducedMotion, speed, seek, onProgress, cinematics }: StageProps) {
  const duration = cue.seconds ?? sceneClips[cue.action].seconds;
  const operator = cue.action === "evaluated" ? 4 : cue.action === "retrieved" || cue.action === "answered" ? 1 : 0;
  const clock = useRef({ time: 0, progress: 0 });
  const lastReported = useRef(-1);
  useEffect(() => {
    if (seek) clock.current.time = clamp(seek.value, 0, 1) * duration;
  }, [seek, duration]);
  useEffect(() => {
    if (reducedMotion) clock.current.time = duration * .62;
  }, [reducedMotion, duration]);
  useEffect(() => () => { cinematics.current = cinematicsAt(undefined, 0); }, [cinematics]);
  useFrame((_, delta) => {
    if (playing && !reducedMotion) clock.current.time = Math.min(duration, clock.current.time + Math.min(delta, .1) * speed);
    clock.current.progress = clock.current.time / duration;
    Object.assign(cinematics.current, cinematicsAt(cue.action, clock.current.progress, reducedMotion));
    const tick = Math.floor(clock.current.progress * 50);
    if (tick !== lastReported.current) { onProgress(clock.current.progress); lastReported.current = tick; }
  }, -2);
  return <group>
    <ScopeSpotlight cue={cue} clock={clock} />
    <Performer index={operator} cue={cue} clock={clock} />
    <TransferPaper cue={cue} clock={clock} />
    {cue.action === "evaluated" ? <AuditRecords cue={cue} clock={clock} /> : null}
    {cue.action === "forgotten" ? <ShreddedRecord cue={cue} clock={clock} /> : null}
    {cue.action === "locked" || cue.action === "resolved" ? <group position={[cueCabinetX(cue), 2.7, -3.1]}>
      <mesh position={[0, .25, 0]}><torusGeometry args={[.2, .045, 8, 20, Math.PI]} /><meshStandardMaterial color="#7962b2" /></mesh>
      <RoundedBox args={[.5, .38, .12]} radius={.04}><meshStandardMaterial color={cue.action === "resolved" ? "#93bac3" : "#d7b268"} /></RoundedBox>
      <Label text={cue.action === "resolved" ? "OWNER KEPT IT" : "OWNER LOCKED"} position={[0, .7, 0]} width={1.9} />
    </group> : null}
    {cue.action === "flagged" ? <group position={[cueCabinetX(cue) + .45, 2.65, -3.7]}>
      <mesh position={[0, -.2, 0]}><cylinderGeometry args={[.025, .025, .8, 8]} /><meshStandardMaterial color="#725c66" /></mesh>
      <RoundedBox args={[.5, .3, .04]} radius={.03} position={[.23, .1, 0]}><meshBasicMaterial color="#cf6572" /></RoundedBox>
    </group> : null}
  </group>;
}
