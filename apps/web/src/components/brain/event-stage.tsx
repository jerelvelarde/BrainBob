"use client";

import { useEffect, useMemo, useRef, type RefObject } from "react";
import { useFrame } from "@react-three/fiber";
import { RoundedBox } from "@react-three/drei";
import * as THREE from "three";
import { BrainBob } from "./brain-bob";
import { Label } from "./scene-label";
import { sceneClips, scopeCharacters, workerPerformance, type BobPerformance, type SceneCue } from "@/lib/scene-animation";

type Clock = RefObject<{ time: number; progress: number }>;
type StageProps = { cue: SceneCue; playing: boolean; reducedMotion: boolean; speed: number;
  seek?: { value: number; revision: number }; onProgress: (progress: number) => void };
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
    const sample = workerPerformance(cue.action, cue.scope, index, clock.current.progress);
    if (group.current) {
      group.current.position.set(sample.x, .05, sample.z);
      group.current.rotation.y = sample.angle;
    }
    Object.assign(performance.current, { time: clock.current.time, distance: sample.distance,
      walking: sample.moving, pose: sample.pose, expression: sample.expression, paper: sample.paper });
  }, -1);
  return <group ref={group}>
    <BrainBob performance={performance} inspector={index === 4} phase={index} />
    {cue.action === "evaluated" && index === 4 ? <Label text="EVALUATOR BOB" position={[0, 1.7, 0]} width={1.85} selected /> : null}
    {cue.action === "evaluated" && index === 2 ? <Label text="He’s here!" position={[0, 1.55, 0]} width={1.15} /> : null}
    {cue.action === "forgotten" && index === 1 ? <Label text="SHRED EVERYTHING!*" position={[0, 1.65, 0]} width={2.1} /> : null}
  </group>;
}

function TransferPaper({ cue, clock }: { cue: SceneCue; clock: Clock }) {
  const group = useRef<THREE.Group>(null);
  const x = scopeCharacters[cue.scope].x;
  useFrame(() => {
    if (!group.current) return;
    const p = clock.current.progress;
    group.current.visible = true;
    group.current.rotation.set(0, .4, 0);
    let px = x, py = 1.2, pz = -3.05;
    if (cue.action === "retrieved") {
      group.current.visible = p > .31;
      const move = smooth(.38, .88, p);
      px = lerp(x, .6, move); pz = lerp(-3, .9, move); py = lerp(1.3, 1.13, move) + Math.sin(move * Math.PI) * 1.1;
      group.current.rotation.x = -Math.PI / 2 * smooth(.78, .95, p);
    } else if (cue.action === "created" || cue.action === "updated") {
      const rewrite = cue.action === "updated";
      const out = rewrite ? smooth(0, .32, p) : 1;
      const back = smooth(rewrite ? .58 : .24, .91, p);
      px = back > 0 ? lerp(-2.85, x, back) : lerp(x, -2.85, out);
      pz = back > 0 ? lerp(.9, -3.55, back) : lerp(-3.1, .9, out);
      py = 1.14 + Math.sin((back > 0 ? back : out) * Math.PI) * .55;
      group.current.rotation.set(-Math.PI / 2 * (1 - back), .2, 0);
      group.current.visible = p < .98;
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
  return <group ref={group}><Paper color={cue.action === "flagged" ? "#f7bbbb" : cue.action === "promoted" ? "#ffe095" : undefined} />
    {cue.action === "flagged" ? <Label text="LOCKED · REVIEW" position={[0, .55, 0]} width={1.8} /> : null}
    {cue.action === "rejected" ? <Label text="RETURN TO SENDER" position={[0, .5, 0]} width={1.8} /> : null}
    {cue.action === "answered" ? <Label text="ANSWER + SOURCES" position={[0, .55, 0]} width={1.8} /> : null}
  </group>;
}

function AuditRecords({ clock }: { clock: Clock }) {
  const sheets = useRef<(THREE.Group | null)[]>([]);
  const lens = useRef<THREE.Group>(null);
  useFrame(() => {
    const p = clock.current.progress;
    sheets.current.forEach((sheet, i) => {
      if (!sheet) return;
      const u = smooth(.12 + i * .045, .56 + i * .045, p);
      const x = [-3.8, -.5, 3.2][i % 3];
      sheet.position.set(lerp(x, 3.2 + (i % 3) * .33, u), 1.45 + Math.sin(u * Math.PI) * 1.5 + (i > 2 ? .07 : 0), lerp(-3, -.35 + Math.floor(i / 3) * .45, u));
      sheet.rotation.set(-u * Math.PI / 2, 0, .12 * Math.sin(i));
      sheet.visible = p > .1 + i * .04;
    });
    if (lens.current) {
      lens.current.position.set(3.55 + Math.sin(clock.current.time * 1.6) * .55, 2.05, -.15 + Math.cos(clock.current.time * 1.6) * .15);
      lens.current.rotation.z = -.4;
    }
  });
  return <group>
    {Array.from({ length: 6 }, (_, i) => <group key={i} ref={(g) => { sheets.current[i] = g; }}><Paper /></group>)}
    <group ref={lens}>
      <mesh><torusGeometry args={[.25, .045, 8, 28]} /><meshStandardMaterial color="#7962b2" /></mesh>
      <mesh position={[0, -.42, 0]}><cylinderGeometry args={[.035, .035, .4, 10]} /><meshStandardMaterial color="#7962b2" /></mesh>
      <mesh><circleGeometry args={[.22, 28]} /><meshBasicMaterial color="#bfdded" transparent opacity={.35} side={THREE.DoubleSide} /></mesh>
    </group>
    <Label text="WITH MEMORY / WITHOUT" position={[3.8, 2.8, -1]} width={2.9} />
  </group>;
}

// Rounded flame tongues: broad orange bases, yellow cores, no flashing lights.
function makeFlameGeometry() {
  const shape = new THREE.Shape();
  shape.moveTo(0, 0);
  shape.bezierCurveTo(-.65, .1, -.65, .55, -.3, 1);
  shape.bezierCurveTo(-.38, .55, .1, .7, .02, 1.65);
  shape.bezierCurveTo(.65, 1.05, .16, .7, .42, .55);
  shape.bezierCurveTo(.7, .2, .35, 0, 0, 0);
  return new THREE.ShapeGeometry(shape, 10);
}

const fireSpots = [
  [-5.8, .1, -3], [-3.8, .3, -3.7], [-.5, .3, -3.7], [3.2, .3, -3.7], [5.5, .1, -3],
  [-5.8, .1, .4], [-3.6, 1.12, .8], [.2, 1.12, .6], [3.8, 1.12, -1],
  [-5.5, .1, 3.5], [-2.7, .1, 3.4], [.2, .1, 3.6], [3.5, .1, 3.4], [5.7, .9, 3.8],
] as const;

function OfficeChaos({ clock }: { clock: Clock }) {
  const flames = useRef<(THREE.Group | null)[]>([]);
  const papers = useRef<(THREE.Group | null)[]>([]);
  const strips = useRef<(THREE.Mesh | null)[]>([]);
  const glow = useRef<THREE.PointLight>(null);
  const geometry = useMemo(makeFlameGeometry, []);
  useEffect(() => () => geometry.dispose(), [geometry]);
  useFrame(() => {
    const p = clock.current.progress, t = clock.current.time;
    const envelope = smooth(.04, .23, p) * (1 - smooth(.83, 1, p));
    flames.current.forEach((flame, i) => {
      if (!flame) return;
      const pulse = 1 + .12 * Math.sin(t * 3.6 + i * 1.7);
      flame.scale.set(envelope * (.85 + (i % 3) * .2), envelope * pulse * (1 + (i % 4) * .2), 1);
      flame.rotation.z = Math.sin(t * 2.6 + i) * .07;
    });
    papers.current.forEach((paper, i) => {
      if (!paper) return;
      const start = .08 + i * .025;
      const u = clamp((p - start) / .46, 0, 1);
      const fromX = [-3.8, -.5, 3.2][i % 3];
      paper.visible = u > 0 && u < 1;
      // Every tossed sheet ends in the slot before strips leave the shredder.
      paper.position.set(lerp(fromX, 5.8, u), lerp(1.6, .9, u) + Math.sin(u * Math.PI) * (2.8 + i % 3), lerp(-3.1, 3.8, u));
      paper.rotation.set(u * 5, u * 3, u * 9 + i);
    });
    strips.current.forEach((strip, i) => {
      if (!strip) return;
      const u = ((t * .7 + i * .073) % 1);
      strip.visible = p > .52 && p < .96;
      strip.position.set(5.8 + Math.sin(i * 2.4) * u * .9, .65 - u * .55, 3.85 + u * (.4 + (i % 4) * .16));
      strip.rotation.set(u * 3 + i, 0, u * 4 + i);
    });
    if (glow.current) glow.current.intensity = envelope * 12;
  });
  return <group>
    <pointLight ref={glow} color="#ff9f3c" position={[0, 3.5, 0]} distance={16} intensity={0} />
    {fireSpots.map((spot, i) => <group key={i} position={[...spot]} rotation={[0, .65, 0]}>
      <group ref={(g) => { flames.current[i] = g; }}>
        <mesh geometry={geometry}><meshBasicMaterial color="#f27827" side={THREE.DoubleSide} toneMapped={false} /></mesh>
        <mesh geometry={geometry} position={[.02, .02, .025]} scale={[.62, .72, 1]}><meshBasicMaterial color="#ffcb34" side={THREE.DoubleSide} toneMapped={false} /></mesh>
        <mesh geometry={geometry} position={[.03, .02, .04]} scale={[.3, .4, 1]}><meshBasicMaterial color="#fff09c" side={THREE.DoubleSide} toneMapped={false} /></mesh>
      </group>
    </group>)}
    {Array.from({ length: 16 }, (_, i) => <group key={i} ref={(g) => { papers.current[i] = g; }}><Paper /></group>)}
    {Array.from({ length: 32 }, (_, i) => <mesh key={i} ref={(g) => { strips.current[i] = g; }}>
      <boxGeometry args={[.035, .3 + i % 3 * .06, .012]} /><meshStandardMaterial color={i % 2 ? "#fff4d9" : "#e8d8b9"} side={THREE.DoubleSide} />
    </mesh>)}
  </group>;
}

function ScopeSpotlight({ cue, clock }: { cue: SceneCue; clock: Clock }) {
  const ring = useRef<THREE.Mesh>(null);
  const color = scopeCharacters[cue.scope].color;
  useFrame(() => {
    if (ring.current) ring.current.scale.setScalar(1 + Math.sin(clock.current.time * 2) * .035);
  });
  return <group position={[scopeCharacters[cue.scope].x, .075, -3.5]}>
    <mesh ref={ring} rotation={[-Math.PI / 2, 0, 0]}><ringGeometry args={[.82, 1.02, 48]} /><meshBasicMaterial color={color} transparent opacity={.7} side={THREE.DoubleSide} /></mesh>
  </group>;
}

export function EventStage({ cue, playing, reducedMotion, speed, seek, onProgress }: StageProps) {
  const duration = sceneClips[cue.action].seconds;
  const clock = useRef({ time: 0, progress: 0 });
  const lastReported = useRef(-1);
  useEffect(() => {
    if (seek) clock.current.time = clamp(seek.value, 0, 1) * duration;
  }, [seek, duration]);
  useEffect(() => {
    if (reducedMotion) clock.current.time = duration * .62;
  }, [reducedMotion, duration]);
  useFrame((_, delta) => {
    if (playing && !reducedMotion) clock.current.time = Math.min(duration, clock.current.time + Math.min(delta, .1) * speed);
    clock.current.progress = clock.current.time / duration;
    const tick = Math.floor(clock.current.progress * 50);
    if (tick !== lastReported.current) { onProgress(clock.current.progress); lastReported.current = tick; }
  }, -2);
  return <group>
    <ScopeSpotlight cue={cue} clock={clock} />
    {Array.from({ length: 6 }, (_, index) => <Performer key={index} index={index} cue={cue} clock={clock} />)}
    <TransferPaper cue={cue} clock={clock} />
    {cue.action === "evaluated" ? <AuditRecords clock={clock} /> : null}
    {cue.action === "forgotten" ? <OfficeChaos clock={clock} /> : null}
    {cue.action === "flagged" ? <group position={[scopeCharacters[cue.scope].x + .45, 2.65, -3.7]}>
      <mesh position={[0, -.2, 0]}><cylinderGeometry args={[.025, .025, .8, 8]} /><meshStandardMaterial color="#725c66" /></mesh>
      <RoundedBox args={[.5, .3, .04]} radius={.03} position={[.23, .1, 0]}><meshBasicMaterial color="#cf6572" /></RoundedBox>
    </group> : null}
  </group>;
}
