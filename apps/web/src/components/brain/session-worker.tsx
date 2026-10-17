"use client";

import { useEffect, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { BrainBob } from "./brain-bob";
import { SessionFolder } from "./session-folder";
import { Label } from "./scene-label";
import type { BobPerformance } from "@/lib/scene-animation";

export type DeskSession = { label: string; status: string; working?: boolean; selected: boolean; onOpen: () => void; onFile: () => void };

/** A seated agent stays with its session while the memory crew moves around the room. */
export function SessionWorker({ session, animate }: { session: DeskSession; animate: boolean }) {
  const [hovered, setHovered] = useState(false);
  const performance = useRef<BobPerformance>({ time: 1, distance: 0, walking: false, pose: "idle", expression: "happy", paper: false });
  useEffect(() => () => { document.body.style.cursor = "auto"; }, []);
  useFrame((_, delta) => {
    if (animate) performance.current.time += Math.min(delta, .05);
    performance.current.pose = session.working ? "write" : "idle";
  }, -1);
  return <group onClick={(event) => { event.stopPropagation(); session.onOpen(); }}
    onPointerOver={(event) => { event.stopPropagation(); setHovered(true); document.body.style.cursor = "pointer"; }}
    onPointerOut={() => { setHovered(false); document.body.style.cursor = "auto"; }}>
    <group position={[.18, .62, -.72]} rotation={[0, .32, 0]} scale={1.15}><BrainBob walking={false} performance={performance} /></group>
    <group position={[.64, 1.22, .27]} rotation={[-Math.PI / 2 + .2, 0, -.12]} scale={hovered ? 1.3 : 1.2} onClick={(event) => { event.stopPropagation(); session.onFile(); }}><SessionFolder /></group>
    <Label text={`${session.label.toUpperCase()} · ${session.status.toUpperCase()}`} position={[.15, 2.38, .05]} width={2.5} selected={session.selected || hovered} onClick={session.onOpen} />
    <Label text="OPEN FILE" position={[.7, 1.18, .89]} width={1.2} selected={session.selected || hovered} onClick={session.onFile} />
    {session.selected || hovered ? <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, .05, .1]}><ringGeometry args={[1.35, 1.4, 48]} /><meshBasicMaterial color="#e2b653" /></mesh> : null}
  </group>;
}
