"use client";

import { Component, memo, useEffect, useMemo, useRef, useState, type RefObject } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, RoundedBox } from "@react-three/drei";
import * as THREE from "three";
import { Label } from "./scene-label";
import { EventStage } from "./event-stage";
import { cinematicsAt, cueForSession, scopeCharacters, type SceneCue, type SceneCinematics } from "@/lib/scene-animation";
import { clientOrganization, defaultReader, drawersForTier } from "@/lib/sample-company";
import { SessionWorker, type DeskSession } from "./session-worker";
import { BrainBob } from "./brain-bob";
import type { MemoryEvent, MemoryScope } from "@/lib/memory";
import { canRead, type BackendMemory } from "@/lib/brain-api";

export type SceneHandle = { reset: () => void; zoom: (factor: number) => void };
type SceneProps = {
  playing: boolean; reducedMotion: boolean; speed: number; event?: MemoryEvent;
  cue?: SceneCue; seek?: { value: number; revision: number }; onProgress: (progress: number) => void;
  selectedScope: MemoryScope | "all"; selectedMemory: string;
  flaggedScopes?: MemoryScope[];
  reader?: string;
  sessions?: DeskSession[];
  memories?: BackendMemory[];
  onSelect: (memoryId: string) => void; onScope: (scope: MemoryScope) => void;
  onWorker: (name: string) => void; onReady: (handle: SceneHandle) => void;
};
const palette = { floor: "#e8d7b9", green: "#b99a76", trim: "#6e5b49", wall: "#e7b6ae", fold: "#c98f91", dark: "#43392f" };
const banks: { scope: MemoryScope; x: number; color: string; label: string; memory: string }[] = [
  { scope: "individual", x: -3.8, color: "#93bac3", label: "INDIVIDUAL", memory: "coffee" },
  { scope: "team", x: -.5, color: "#d7b268", label: "TEAM", memory: "sources" },
  { scope: "organization", x: 3.2, color: "#baa6ce", label: "ORGANIZATION", memory: "launch" },
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

function Cabinet({ bank, reader, memories = [], selected, active, onClick }: { bank: typeof banks[number]; reader: string; memories?: BackendMemory[]; selected: boolean; active: boolean; onClick: () => void }) {
  const allDrawers = drawersForTier(bank.scope, reader);
  const drawers = bank.scope === "individual" ? [...allDrawers.filter((drawer) => drawer.accessible), ...allDrawers.filter((drawer) => !drawer.accessible)].slice(0, 3) : allDrawers;
  const count = (path: string) => memories.filter((memory) => memory.scope === path && canRead(path, reader) && memory.status !== "retired").length;
  const total = allDrawers.filter((drawer) => drawer.accessible).reduce((sum, drawer) => sum + count(drawer.path), 0);
  return <group position={[bank.x, 0, -3.85]} onClick={(e) => { e.stopPropagation(); onClick(); }}
    onPointerOver={() => { document.body.style.cursor = "pointer"; }} onPointerOut={() => { document.body.style.cursor = "auto"; }}>
    {[-.49, .49].map((x) => <Box key={x} position={[x, .13, 0]} size={[.12, .25, .68]} color={palette.trim} />)}
    <Box position={[0, 1.22, 0]} size={[1.35, 2.15, .8]} color={bank.color} radius={.06} />
    {drawers.map((drawer, i) => {
      const y = drawers.length === 2 ? 1.65 - i * .9 : 1.8 - i * .65;
      return <group key={drawer.path} position={[0, 0, active && drawer.accessible ? .2 : 0]}>
        <Box position={[0, y, .428]} size={[1.15, drawers.length === 2 ? .8 : .56, .05]} color={drawer.accessible ? "#f4d88b" : bank.color} radius={.025} />
        <Label position={[0, y + .08, .5]} text={`${drawer.label.toUpperCase()}${drawer.accessible ? ` · ${count(drawer.path)}` : ""}`} width={1.03} compact selected={drawer.accessible} onClick={onClick} />
        <Box position={[-.08, y - .12, .48]} size={[.33, .05, .04]} color="#79664e" radius={.015} />
        {!drawer.accessible ? <group position={[.37, y - .12, .49]}><mesh position={[0, .04, 0]}><torusGeometry args={[.045, .012, 6, 10, Math.PI]} /><meshStandardMaterial color="#6d6673" /></mesh><Box position={[0, 0, 0]} size={[.1, .08, .03]} color="#6d6673" radius={.01} /></group> : null}
      </group>;
    })}
    <Box position={[0, 2.33, 0]} size={[1.45, .1, .86]} color={palette.trim} />
    {active ? <mesh position={[0, 2.55, 0]}><sphereGeometry args={[.09, 12, 10]} /><meshBasicMaterial color="#f4cf49" /></mesh> : null}
    <Label position={[0, 2.75, 0]} text={`${bank.label} · ${total}`} width={2.6} selected={selected} onClick={onClick} />
    {bank.scope === "individual" ? <Label position={[0, .15, .55]} text="18 PEOPLE · INSPECT" width={1.15} onClick={onClick} /> : null}
  </group>;
}

const Desk = memo(function Desk({ position, rotation = 0, audit = false, occupied = false }: { position: [number, number, number]; rotation?: number; audit?: boolean; occupied?: boolean }) {
  return <group position={position} rotation={[0, rotation, 0]}>
    <Box position={[0, 1, 0]} size={[2.1, .14, 1.2]} color="#a17d56" radius={.04} />
    <Box position={[0, .89, 0]} size={[1.95, .12, 1.08]} color="#765c42" />
    {[-.85, .85].flatMap((x) => [-.43, .43].map((z) => <Box key={`${x}-${z}`} position={[x, .47, z]} size={[.11, .91, .11]} color="#6c5844" />))}
    <group position={occupied ? [-.5, 0, .1] : [-.23, 0, -.22]} rotation={[0, occupied ? Math.atan2(.68, -.82) : 0, 0]}>
    <Box position={[0, 1.4, 0]} size={[.62, .49, .42]} color="#d5cbb9" radius={.06} />
    <Box position={[0, 1.4, .223]} size={[.48, .34, .025]} color="#5f8b9d" radius={.02} />
    <Box position={[0, 1.19, .12]} size={[.28, .1, .3]} color="#bbae98" />
    <Box position={[0, 1.1, .52]} size={[.64, .045, .22]} color="#d5cbb9" />
    {[-.07, 0, .07].map((y) => <Box key={y} position={[0, 1.4 + y, -.213]} size={[.32, .018, .012]} color="#b4a995" radius={.004} />)}
    </group>
    {!occupied ? [0, 1, 2, 3].map((i) => <Box key={i} position={[.65, 1.1 + i * .027, .06]} size={[.4, .025, .46]} color={i % 2 ? "#efedd6" : "#dedac4"} rotation={[0, i % 2 * .1, 0]} radius={.005} />) : null}
    <mesh position={[-.8, 1.19, .2]} castShadow><cylinderGeometry args={[.07, .065, .16, 10]} /><meshStandardMaterial color={audit ? "#e5b958" : "#e9d9c0"} /></mesh>
    <group position={occupied ? [.18, .22, -.72] : [0, 0, 1]} rotation={[0, occupied ? Math.PI : 0, 0]}>
      <Box position={[0, .55, 0]} size={[.55, .1, .55]} color="#9f8164" />
      <Box position={[0, .86, .22]} size={[.55, .5, .08]} color="#9f8164" />
      <mesh position={[0, .27, 0]}><cylinderGeometry args={[.045, .045, .5, 8]} /><meshStandardMaterial color="#695744" /></mesh>
      <Box position={[0, .07, 0]} size={[.7, .07, .1]} color="#695744" />
      <Box position={[0, .07, 0]} size={[.1, .07, .7]} color="#695744" />
    </group>
    {audit ? <Label position={[0, 1.95, -.1]} text="EVIDENCE DESK" width={1.65} /> : null}
  </group>;
});


function SceneLighting({ cinematics }: { cinematics: RefObject<SceneCinematics> }) {
  const ambient = useRef<THREE.AmbientLight>(null);
  const key = useRef<THREE.DirectionalLight>(null);
  const fill = useRef<THREE.DirectionalLight>(null);
  const faceLight = useRef<THREE.DirectionalLight>(null);
  const ground = useRef<THREE.MeshStandardMaterial>(null);
  const { scene } = useThree();
  const colors = useMemo(() => ({ day: new THREE.Color("#f0e9dd"), night: new THREE.Color("#252032"), fire: new THREE.Color("#37212b"), mix: new THREE.Color() }), []);
  useFrame(() => {
    const { darkness, heat } = cinematics.current;
    colors.mix.copy(colors.night).lerp(colors.fire, heat);
    if (scene.background instanceof THREE.Color) scene.background.copy(colors.day).lerp(colors.mix, darkness);
    ground.current?.color.copy(colors.day).lerp(colors.mix, darkness);
    if (ambient.current) ambient.current.intensity = THREE.MathUtils.lerp(1.55, .55, darkness);
    if (key.current) key.current.intensity = THREE.MathUtils.lerp(2.8, 1.35, darkness);
    if (fill.current) fill.current.intensity = THREE.MathUtils.lerp(.6, 1.1, darkness);
    if (faceLight.current) faceLight.current.intensity = darkness * 1.6;
  }, -.5);
  return <>
    <color attach="background" args={["#f0e9dd"]} />
    <ambientLight ref={ambient} intensity={1.55} color="#fff5e2" />
    <directionalLight ref={key} position={[5, 12, 8]} intensity={2.8} color="#fff1d5" castShadow shadow-mapSize={[2048, 2048]} shadow-camera-left={-12} shadow-camera-right={12} shadow-camera-top={12} shadow-camera-bottom={-12} shadow-normalBias={.04} />
    <directionalLight ref={fill} position={[-8, 5, -3]} intensity={.6} color="#c6b4f5" />
    <directionalLight ref={faceLight} position={[6, 5, 14]} intensity={0} color="#fff3d0" />
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -.58, 0]} receiveShadow><planeGeometry args={[200, 200]} /><meshStandardMaterial ref={ground} color="#f0e9dd" roughness={1} /></mesh>
  </>;
}

function CameraRig({ onReady, cinematics }: Pick<SceneProps, "onReady"> & { cinematics: RefObject<SceneCinematics> }) {
  const controls = useRef<React.ComponentRef<typeof OrbitControls>>(null);
  const appliedZoom = useRef(1);
  const { camera, invalidate, size } = useThree();
  useFrame(() => {
    // Multiply only our contribution: wheel/button zoom and orbit remain user-controlled.
    const next = cinematics.current.zoom;
    if (next !== appliedZoom.current) {
      camera.zoom *= next / appliedZoom.current;
      camera.updateProjectionMatrix();
      appliedZoom.current = next;
    }
  });
  useEffect(() => {
    const fitZoom = Math.max(10, Math.min(size.width / 19, size.height / 13));
    camera.zoom = fitZoom * appliedZoom.current;
    camera.updateProjectionMatrix();
    camera.lookAt(0, .9, 0);
    camera.updateMatrixWorld();
    controls.current?.target.set(0, .9, 0);
    controls.current?.update();
    invalidate();
    onReady({
      reset: () => { camera.position.set(16, 14, 19); camera.zoom = fitZoom * appliedZoom.current; camera.updateProjectionMatrix(); controls.current?.target.set(0, .9, 0); controls.current?.update(); invalidate(); },
      zoom: (factor) => { camera.zoom = THREE.MathUtils.clamp(camera.zoom * factor, 10, 85); camera.updateProjectionMatrix(); invalidate(); },
    });
  }, [camera, invalidate, onReady, size]);
  return <OrbitControls ref={controls} target={[0, .9, 0]} enablePan={false} minZoom={10} maxZoom={85} minPolarAngle={.4} maxPolarAngle={1.15} minAzimuthAngle={-.3} maxAzimuthAngle={1.45} enableDamping dampingFactor={.08} />;
}

class SceneBoundary extends Component<{ children: React.ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <div className="scene-fallback"><span>THE MEMORY FLOOR</span><h2>The crew is taking a screen break.</h2><p>3D couldn’t start in this browser. Your memory records and retrace controls still work.</p></div> : this.props.children; }
}

export default function BrainScene(props: SceneProps) {
  const [supported, setSupported] = useState(true);
  const reader = props.reader ?? defaultReader;
  const cue = useMemo(() => cueForSession(props.cue, reader), [props.cue, reader]);
  const cinematics = useRef<SceneCinematics>(cinematicsAt(undefined, 0));
  useEffect(() => {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl2");
    setSupported(Boolean(gl));
    gl?.getExtension("WEBGL_lose_context")?.loseContext();
  }, []);
  if (!supported) return <div className="scene-fallback"><h2>Your memories are in good hands.</h2><p>Enable WebGL to visit the 3D brain. Open Memories to explore memory and history.</p></div>;
  return <SceneBoundary><Canvas orthographic shadows dpr={[1, 1.7]} camera={{ position: [16, 14, 19], zoom: 45, near: .1, far: 100 }} gl={{ antialias: true, powerPreference: "high-performance" }} aria-label={`Interactive memory office: click a tier cabinet to browse its files${props.sessions?.length ? `, or one of ${props.sessions.length} seated session Bobs` : ""}`}>
    <SceneLighting cinematics={cinematics} />
    <Room />
    <Label text="RUSTY ROD · CONSULTING" position={[-2.8, 4.25, -4.8]} width={3.4} />
    <Label text={`CLIENT · ${clientOrganization.name.toUpperCase()}`} position={[1.6, 4.25, -4.8]} width={3.4} />
    {banks.map((bank) => <Cabinet key={bank.scope} bank={bank} reader={reader} memories={props.memories} selected={props.selectedScope === bank.scope} active={cue?.scope === bank.scope} onClick={() => { props.onScope(bank.scope); props.onSelect(bank.memory); }} />)}
    {props.flaggedScopes?.map((scope) => <Label key={scope} text="FLAGGED · OWNER REVIEW" position={[scopeCharacters[scope].x, 3.35, -3.8]} width={2.6} />)}
    {([[-3.6, 0, .9], [.2, 0, .6], [3.8, 0, -1]] as [number, number, number][]).map((position, index) => {
      const session = props.sessions?.[index];
      return <group key={index} position={position} rotation={[0, session ? .62 : index === 2 ? -.1 : 0, 0]} onClick={session ? (event) => { event.stopPropagation(); session.onOpen(); } : undefined}>
        <Desk position={[0, 0, 0]} occupied={Boolean(session)} audit={!session && index === 2 && props.cue?.evaluation?.phase !== "check"} />
        {session ? <SessionWorker session={session} animate={props.playing && !props.reducedMotion} /> : null}
      </group>;
    })}
    {cue ? <EventStage key={cue.id} cue={cue} playing={props.playing} speed={props.speed} reducedMotion={props.reducedMotion} seek={props.seek} onProgress={props.onProgress} cinematics={cinematics} /> : <group position={[-5.4, 0, 2.5]} rotation={[0, .55, 0]} onClick={(event) => { event.stopPropagation(); props.onWorker("Memory Bob looks after your session file."); }}>
      <Box position={[0, .55, 0]} size={[.75, .12, .65]} color="#a17d56" />
      {[-.25, .25].flatMap((x) => [-.2, .2].map((z) => <Box key={`${x}-${z}`} position={[x, .26, z]} size={[.07, .5, .07]} color="#765c42" />))}
      <group position={[0, .45, 0]}><BrainBob walking={false} /></group>
      <Label text="MEMORY BOB" position={[0, 2.25, 0]} width={1.8} onClick={() => props.onWorker("Memory Bob looks after your session file.")} />
    </group>}
    <CameraRig onReady={props.onReady} cinematics={cinematics} />
  </Canvas></SceneBoundary>;
}
