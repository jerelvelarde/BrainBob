"use client";

import { Component, memo, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, RoundedBox } from "@react-three/drei";
import * as THREE from "three";
import { Label } from "./scene-label";
import { EventStage } from "./event-stage";
import { scopeCharacters, type SceneCue } from "@/lib/scene-animation";
import { BrainBob } from "./brain-bob";
import type { MemoryEvent, MemoryScope } from "@/lib/memory";

export type SceneHandle = { reset: () => void; zoom: (factor: number) => void };
type SceneProps = {
  playing: boolean; reducedMotion: boolean; speed: number; event?: MemoryEvent;
  cue?: SceneCue; seek?: { value: number; revision: number }; onProgress: (progress: number) => void;
  selectedScope: MemoryScope | "all"; selectedMemory: string;
  onSelect: (memoryId: string) => void; onScope: (scope: MemoryScope) => void;
  onWorker: (name: string) => void; onReady: (handle: SceneHandle) => void;
};
const palette = { floor: "#e8d7b9", green: "#b99a76", trim: "#6e5b49", wall: "#e7b6ae", fold: "#c98f91", dark: "#43392f" };
const banks: { scope: MemoryScope; color: string; x: number; memory: string; label: string }[] = [
  { scope: "individual", color: "#93bac3", x: -3.8, memory: "coffee", label: "JOHN" },
  { scope: "team", color: "#d7b268", x: -.5, memory: "launch", label: "SALES TEAM" },
  { scope: "organization", color: "#c4ac7d", x: 3.2, memory: "sources", label: "KRUSTY KRAB" },
];
const routes: [number, number][][] = [
  [[-5.2, 3.4], [-5.2, -2.4], [1.65, -2.4], [1.65, 3.4]],
  [[5.3, 3.4], [1.8, 3.4], [1.8, -2.4], [5.3, -2.4]],
  [[-1.7, -.7], [-1.7, 3.5], [2.1, 3.5], [2.1, -.7]],
  [[-5.8, 3.1], [-5.8, -.7], [-5.1, -.7], [-5.1, 3.1]],
  [[-.6, -2.4], [2.1, -2.4], [2.1, -.5], [-.6, -.5]],
  [[5.5, 2.7], [5.5, -2.4], [-1.6, -2.4], [-1.6, 2.7]],
];


function Box({ position, size, color, radius = .04, rotation = [0, 0, 0] }: {
  position: [number, number, number]; size: [number, number, number]; color: string;
  radius?: number; rotation?: [number, number, number];
}) {
  return <RoundedBox args={size} radius={Math.min(radius, Math.min(...size) * .48)} smoothness={2} position={position} rotation={rotation} castShadow receiveShadow>
    <meshStandardMaterial color={color} roughness={.78} />
  </RoundedBox>;
}

function Fold({ points }: { points: [number, number, number][] }) {
  const geometry = useMemo(() => new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(...p))), 32, .055, 6, false), [points]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return <mesh geometry={geometry}><meshStandardMaterial color={palette.fold} roughness={1} /></mesh>;
}

const Room = memo(function Room() {
  const folds = useMemo(() => Array.from({ length: 8 }, (_, i) => {
    const x = -6 + i * 1.7;
    return [[x, .5, -4.77], [x + .32, 1.1, -4.72], [x - .2, 1.7, -4.72], [x + .4, 2.45, -4.72], [x + .15, 3.3, -4.73]] as [number, number, number][];
  }), []);
  const sideFolds = useMemo(() => Array.from({ length: 5 }, (_, i) => {
    const z = -4 + i * 1.65;
    return [[-6.78, .6, z], [-6.76, 1.2, z + .3], [-6.76, 1.9, z - .15], [-6.76, 2.7, z + .4], [-6.76, 3.4, z]] as [number, number, number][];
  }), []);
  return <group>
    <Box position={[0, -.28, 0]} size={[14.3, .55, 10.3]} color="#bca27e" radius={.16} />
    <Box position={[0, -.035, 0]} size={[14, .13, 10]} color={palette.floor} />
    {Array.from({ length: 14 }, (_, x) => Array.from({ length: 10 }, (_, z) => (x + z) % 2 === 0 ? <mesh key={`${x}-${z}`} rotation={[-Math.PI / 2, 0, 0]} position={[x - 6.5, .035, z - 4.5]} receiveShadow>
      <planeGeometry args={[.99, .99]} /><meshStandardMaterial color="#dfc9a6" roughness={1} />
    </mesh> : null))}
    <Box position={[0, 1.85, -5]} size={[14, 3.7, .42]} color={palette.wall} radius={.15} />
    <Box position={[-7, 1.85, 0]} size={[.42, 3.7, 10]} color={palette.wall} radius={.15} />
    <Box position={[0, .14, -4.73]} size={[13.8, .23, .18]} color="#bd9290" />
    <Box position={[-6.73, .14, 0]} size={[.18, .23, 9.8]} color="#bd9290" />
    {Array.from({ length: 14 }, (_, i) => <mesh key={`cap-${i}`} position={[i - 6.5, 3.6 + Math.sin(i * 2) * .12, -5]} scale={[.85, .46, .45]} castShadow><sphereGeometry args={[.8, 12, 8]} /><meshStandardMaterial color={palette.wall} roughness={1} /></mesh>)}
    {Array.from({ length: 9 }, (_, i) => <mesh key={`side-${i}`} position={[-7, 3.6 + Math.sin(i * 2) * .12, i - 4]} scale={[.45, .46, .85]} castShadow><sphereGeometry args={[.8, 12, 8]} /><meshStandardMaterial color={palette.wall} roughness={1} /></mesh>)}
    {folds.map((points, i) => <Fold key={`fold-${i}`} points={points} />)}
    {sideFolds.map((points, i) => <Fold key={`sf-${i}`} points={points} />)}
    <Box position={[-6.4, 1.65, -1]} size={[.06, 1.15, 1.65]} color="#bd9290" />
    <Box position={[-6.35, 1.65, -1]} size={[.06, .95, 1.45]} color="#f4e4c8" />

    <Box position={[.2, .07, 2.7]} size={[4, .025, 2]} color="#dbb980" radius={.15} />
    {[-5.8, 5.7].map((x) => <Plant key={x} position={[x, 0, -3.7]} />)}
    <Box position={[5.8, .4, 3.8]} size={[.85, .8, .65]} color="#c3a279" />
    <Box position={[5.8, .82, 3.8]} size={[.9, .08, .7]} color="#9a7c5b" />
    <Box position={[5.8, .87, 3.8]} size={[.62, .025, .09]} color="#483b52" />
    <Label position={[5.8, 1.13, 3.8]} text="SHREDDER" width={1} />
  </group>;
});

function Plant({ position }: { position: [number, number, number] }) {
  return <group position={position}>
    <mesh position={[0, .3, 0]} castShadow><cylinderGeometry args={[.29, .21, .5, 12]} /><meshStandardMaterial color="#ca8b69" /></mesh>
    {Array.from({ length: 5 }, (_, i) => <mesh key={i} position={[Math.sin(i * 2) * .17, .8 + i * .06, Math.cos(i * 2) * .17]} rotation={[.2 * Math.sin(i), i, .4 * Math.cos(i)]} scale={[.16, .45, .1]} castShadow><sphereGeometry args={[1, 10, 8]} /><meshStandardMaterial color={i % 2 ? "#65936e" : "#467a62"} /></mesh>)}
  </group>;
}

function Cabinet({ bank, selected, active, onClick }: { bank: typeof banks[number]; selected: boolean; active: boolean; onClick: () => void }) {
  return <group position={[bank.x, 0, -3.85]} onClick={(e) => { e.stopPropagation(); onClick(); }}
    onPointerOver={() => { document.body.style.cursor = "pointer"; }} onPointerOut={() => { document.body.style.cursor = "auto"; }}>
    {[-.49, .49].map((x) => <Box key={x} position={[x, .13, 0]} size={[.12, .25, .68]} color={palette.trim} />)}
    <Box position={[0, 1.22, 0]} size={[1.35, 2.15, .8]} color={bank.color} radius={.06} />
    {[.5, 1.15, 1.8].map((y, i) => <group key={y} position={[0, 0, active && i === 1 ? .2 : 0]}>
      <Box position={[0, y, .428]} size={[1.15, .56, .05]} color={selected ? "#f4d88b" : bank.color} radius={.025} />
      <Box position={[0, y + .1, .465]} size={[.28, .12, .018]} color="#f0e6c9" radius={.01} />
      <Box position={[0, y - .1, .48]} size={[.33, .05, .04]} color="#79664e" radius={.015} />
    </group>)}
    <Box position={[0, 2.33, 0]} size={[1.45, .1, .86]} color={palette.trim} />
    {active ? <mesh position={[0, 2.55, 0]}><sphereGeometry args={[.09, 12, 10]} /><meshBasicMaterial color="#f4cf49" /></mesh> : null}
    <Label position={[0, 2.75, 0]} text={`${bank.label} · ${scopeCharacters[bank.scope].role.toUpperCase()}`} width={2.6} selected={selected} onClick={onClick} />
  </group>;
}

const Desk = memo(function Desk({ position, rotation = 0, audit = false }: { position: [number, number, number]; rotation?: number; audit?: boolean }) {
  return <group position={position} rotation={[0, rotation, 0]}>
    <Box position={[0, 1, 0]} size={[2.1, .14, 1.2]} color="#a17d56" radius={.04} />
    <Box position={[0, .89, 0]} size={[1.95, .12, 1.08]} color="#765c42" />
    {[-.85, .85].flatMap((x) => [-.43, .43].map((z) => <Box key={`${x}-${z}`} position={[x, .47, z]} size={[.11, .91, .11]} color="#6c5844" />))}
    <Box position={[-.23, 1.4, -.22]} size={[.62, .49, .42]} color="#d5cbb9" radius={.06} />
    <Box position={[-.23, 1.4, .003]} size={[.48, .34, .025]} color="#5f8b9d" radius={.02} />
    <Box position={[-.23, 1.19, -.1]} size={[.28, .1, .3]} color="#bbae98" />
    <Box position={[-.23, 1.1, .3]} size={[.64, .045, .22]} color="#d5cbb9" />
    {[0, 1, 2, 3].map((i) => <Box key={i} position={[.65, 1.1 + i * .027, .06]} size={[.4, .025, .46]} color={i % 2 ? "#efedd6" : "#dedac4"} rotation={[0, i % 2 * .1, 0]} radius={.005} />)}
    <mesh position={[-.8, 1.19, .2]} castShadow><cylinderGeometry args={[.07, .065, .16, 10]} /><meshStandardMaterial color={audit ? "#e5b958" : "#e9d9c0"} /></mesh>
    <group position={[0, 0, 1]}>
      <Box position={[0, .55, 0]} size={[.55, .1, .55]} color="#9f8164" />
      <Box position={[0, .86, .22]} size={[.55, .5, .08]} color="#9f8164" />
      <mesh position={[0, .27, 0]}><cylinderGeometry args={[.045, .045, .5, 8]} /><meshStandardMaterial color="#695744" /></mesh>
      <Box position={[0, .07, 0]} size={[.7, .07, .1]} color="#695744" />
      <Box position={[0, .07, 0]} size={[.1, .07, .7]} color="#695744" />
    </group>
    {audit ? <Label position={[0, 1.95, -.1]} text="EVIDENCE DESK" width={1.65} /> : null}
  </group>;
});

function Walker({ index, playing, speed, reducedMotion, event, onClick }: {
  index: number; playing: boolean; speed: number; reducedMotion: boolean; event?: MemoryEvent; onClick: () => void;
}) {
  const group = useRef<THREE.Group>(null);
  const travel = useRef(index * 1.8);
  const oriented = useRef(false);
  const route = routes[index];
  const lengths = useMemo(() => route.map((start, i) => {
    const end = route[(i + 1) % route.length];
    return Math.hypot(end[0] - start[0], end[1] - start[1]);
  }), [route]);
  const total = lengths.reduce((sum, length) => sum + length, 0);
  useFrame((_, delta) => {
    if (!group.current) return;
    if (playing && !reducedMotion) travel.current += Math.min(delta, .05) * speed * .85;
    let along = travel.current % total;
    let segment = 0;
    while (segment < lengths.length - 1 && along >= lengths[segment]) {
      along -= lengths[segment]; segment++;
    }
    const start = route[segment];
    const end = route[(segment + 1) % route.length];
    const progress = along / lengths[segment];
    group.current.position.set(THREE.MathUtils.lerp(start[0], end[0], progress), .05, THREE.MathUtils.lerp(start[1], end[1], progress));
    const angle = Math.atan2(end[0] - start[0], end[1] - start[1]);
    const turn = Math.atan2(Math.sin(angle - group.current.rotation.y), Math.cos(angle - group.current.rotation.y));
    if (!oriented.current) {
      group.current.rotation.y = angle;
      oriented.current = true;
    } else if (playing && !reducedMotion) {
      group.current.rotation.y = THREE.MathUtils.damp(group.current.rotation.y, group.current.rotation.y + turn, 9, Math.min(delta, .05));
    }
  });
  const active = event && ((["Inspector BrainBob", "Inspector Bob"].includes(event.actor) && index === 4) || (["Curator BrainBob", "Curator Bob"].includes(event.actor) && index === 0) || (["Runner BrainBob", "Runner Bob"].includes(event.actor) && index === 1));
  return <group ref={group} position={[route[0][0], .05, route[0][1]]} onClick={(e) => { e.stopPropagation(); onClick(); }}>
    <BrainBob walking={playing && !reducedMotion} carrying={index === 0 || index === 1} inspector={index === 4} phase={index} distance={travel} />
    {active ? <Label position={[0, 1.85, 0]} width={1.35} text={event.action === "evaluated" ? "Checks out!" : event.action === "updated" ? "New info!" : event.action === "forgotten" ? "Let it go." : "On it!"} /> : null}
  </group>;
}

function CameraRig({ onReady }: Pick<SceneProps, "onReady">) {
  const controls = useRef<React.ComponentRef<typeof OrbitControls>>(null);
  const { camera, invalidate, size } = useThree();
  useEffect(() => {
    const fitZoom = Math.max(20, Math.min(size.width / 21, size.height / 13));
    camera.zoom = fitZoom;
    camera.updateProjectionMatrix();
    camera.lookAt(0, .9, 0);
    camera.updateMatrixWorld();
    controls.current?.target.set(0, .9, 0);
    controls.current?.update();
    invalidate();
    onReady({
      reset: () => { camera.position.set(16, 14, 19); camera.zoom = fitZoom; camera.updateProjectionMatrix(); controls.current?.target.set(0, .9, 0); controls.current?.update(); invalidate(); },
      zoom: (factor) => { camera.zoom = THREE.MathUtils.clamp(camera.zoom * factor, 18, 85); camera.updateProjectionMatrix(); invalidate(); },
    });
  }, [camera, invalidate, onReady, size]);
  return <OrbitControls ref={controls} target={[0, .9, 0]} enablePan={false} minZoom={18} maxZoom={85} minPolarAngle={.4} maxPolarAngle={1.15} minAzimuthAngle={-.3} maxAzimuthAngle={1.45} enableDamping dampingFactor={.08} />;
}

class SceneBoundary extends Component<{ children: React.ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <div className="scene-fallback"><span>THE MEMORY FLOOR</span><h2>The crew is taking a screen break.</h2><p>3D couldn’t start in this browser. Your memory records and retrace controls still work.</p></div> : this.props.children; }
}

export default function BrainScene(props: SceneProps) {
  const [supported, setSupported] = useState(true);
  useEffect(() => {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl2");
    setSupported(Boolean(gl));
    gl?.getExtension("WEBGL_lose_context")?.loseContext();
  }, []);
  if (!supported) return <div className="scene-fallback"><h2>Your memories are in good hands.</h2><p>Enable WebGL to visit the 3D brain. Open Memories to explore memory and history.</p></div>;
  return <SceneBoundary><Canvas orthographic shadows dpr={[1, 1.7]} camera={{ position: [16, 14, 19], zoom: 45, near: .1, far: 100 }} gl={{ antialias: true, powerPreference: "high-performance" }} aria-label="Interactive isometric brain office with six walking BrainBob memory workers">
    <color attach="background" args={["#f0e9dd"]} />
    <ambientLight intensity={1.55} color="#fff5e2" />
    <directionalLight position={[5, 12, 8]} intensity={2.8} color="#fff1d5" castShadow shadow-mapSize={[2048, 2048]} shadow-camera-left={-12} shadow-camera-right={12} shadow-camera-top={12} shadow-camera-bottom={-12} shadow-normalBias={.04} />
    <directionalLight position={[-8, 5, -3]} intensity={.6} color="#e7ddf5" />
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -.58, 0]} receiveShadow><planeGeometry args={[200, 200]} /><meshStandardMaterial color="#f0e9dd" roughness={1} /></mesh>
    <Room />
    {banks.map((bank) => <Cabinet key={bank.scope} bank={bank} selected={props.selectedScope === bank.scope} active={props.cue?.scope === bank.scope} onClick={() => { props.onScope(bank.scope); props.onSelect(bank.memory); }} />)}
    <Desk position={[-3.6, 0, .9]} />
    <Desk position={[.2, 0, .6]} />
    <Desk position={[3.8, 0, -1]} rotation={-.1} audit />
    {props.cue ? <EventStage key={props.cue.id} cue={props.cue} playing={props.playing} speed={props.speed} reducedMotion={props.reducedMotion} seek={props.seek} onProgress={props.onProgress} /> : routes.map((_, index) => <Walker key={index} index={index} playing={props.playing} speed={props.speed} reducedMotion={props.reducedMotion} event={props.event} onClick={() => props.onWorker(index === 4 ? "Inspector BrainBob checks memories against their evidence." : index === 0 ? "Curator BrainBob files new memories and revisions." : "Runner BrainBob delivers memories to the team.")} />)}
    <CameraRig onReady={props.onReady} />
  </Canvas></SceneBoundary>;
}
