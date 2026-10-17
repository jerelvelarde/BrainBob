"use client";

import { useEffect, useMemo, useRef, type RefObject } from "react";
import { useFrame } from "@react-three/fiber";
import { RoundedBox } from "@react-three/drei";
import * as THREE from "three";

const yellow = "#ffd21f";
const indigo = "#7962b2";

/** One graphic face, fitted to the body surface: no separate eyeballs or glass layers. */
function makeFaceTexture(blinking: boolean) {
  const canvas = document.createElement("canvas");
  canvas.width = 512; canvas.height = 512;
  const ctx = canvas.getContext("2d")!;
  ctx.clearRect(0, 0, 512, 512);
  ctx.fillStyle = "#ed8d55";
  for (const x of [112, 400]) {
    ctx.beginPath(); ctx.ellipse(x, 297, 27, 14, 0, 0, Math.PI * 2); ctx.fill();
  }
  for (const x of [175, 337]) {
    ctx.fillStyle = "#302b3b";
    if (blinking) {
      ctx.strokeStyle = "#302b3b"; ctx.lineWidth = 12; ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(x - 28, 244); ctx.quadraticCurveTo(x, 228, x + 28, 244); ctx.stroke();
    } else {
      ctx.beginPath(); ctx.ellipse(x, 240, 32, 43, 0, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#fff9dd";
      ctx.beginPath(); ctx.arc(x - 9, 225, 7, 0, Math.PI * 2); ctx.fill();
    }
  }
  ctx.strokeStyle = "#302b3b"; ctx.lineWidth = 10; ctx.lineCap = "round";
  ctx.beginPath(); ctx.moveTo(222, 308); ctx.quadraticCurveTo(256, 346, 290, 308); ctx.stroke();
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

function Foot({ side, footRef }: { side: number; footRef: React.Ref<THREE.Group> }) {
  return <group ref={footRef} position={[side * .185, .22, .035]}>
    <mesh scale={[1, .7, 1.28]} castShadow>
      <sphereGeometry args={[.13, 18, 12]} /><meshStandardMaterial color={indigo} roughness={.9} />
    </mesh>
    <mesh position={[0, -.061, .015]} scale={[1, .22, 1.25]}>
      <sphereGeometry args={[.123, 18, 10]} /><meshStandardMaterial color="#f7dc97" roughness={1} />
    </mesh>
  </group>;
}

export type BrainBobSilhouette = "round" | "rectangle" | "slanted";

export function BrainBob({ walking = true, carrying = false, inspector = false, phase = 0, distance, silhouette = "rectangle" }: {
  walking?: boolean; carrying?: boolean; inspector?: boolean; phase?: number; distance?: RefObject<number>; silhouette?: BrainBobSilhouette;
}) {
  const body = useRef<THREE.Group>(null);
  const leftFoot = useRef<THREE.Group>(null);
  const rightFoot = useRef<THREE.Group>(null);
  const leftArm = useRef<THREE.Group>(null);
  const rightArm = useRef<THREE.Group>(null);
  const face = useRef<THREE.MeshBasicMaterial>(null);
  const elapsed = useRef(phase * 1.17);
  const shapeMatrix = useMemo(() => new THREE.Matrix4().set(
    1, silhouette === "slanted" ? .18 : 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    0, 0, 0, 1,
  ), [silhouette]);
  const textures = useMemo(() => ({ open: makeFaceTexture(false), blink: makeFaceTexture(true) }), []);
  useEffect(() => () => { textures.open.dispose(); textures.blink.dispose(); }, [textures]);

  useFrame((_, delta) => {
    if (walking) elapsed.current += Math.min(delta, .05);
    const step = distance ? distance.current * Math.PI * 2 / .72 : elapsed.current * 6;
    const sway = walking ? Math.sin(step) : 0;
    if (leftFoot.current) { leftFoot.current.position.y = .22 + Math.max(0, sway) * .045; leftFoot.current.position.z = .035 + sway * .055; }
    if (rightFoot.current) { rightFoot.current.position.y = .22 + Math.max(0, -sway) * .045; rightFoot.current.position.z = .035 - sway * .055; }
    if (leftArm.current) leftArm.current.rotation.x = -.16 * sway;
    if (rightArm.current) rightArm.current.rotation.x = carrying ? -.3 : .16 * sway;
    if (body.current) {
      body.current.position.y = walking ? Math.abs(sway) * .012 : 0;
      body.current.rotation.z = sway * .025;
    }
    if (face.current) {
      // Short staggered blinks; pausing or reduced motion leaves a calm open expression.
      const blink = walking && elapsed.current % (3.6 + phase * .19) < .14;
      const map = blink ? textures.blink : textures.open;
      if (face.current.map !== map) { face.current.map = map; face.current.needsUpdate = true; }
    }
  });

  return <group position={[0, -.13, 0]}>
    <Foot side={-1} footRef={leftFoot} /><Foot side={1} footRef={rightFoot} />
    <group ref={body}>
      {silhouette === "round" ? <>
        <mesh position={[0, .71, 0]} scale={[1, 1.02, .82]} castShadow>
          <sphereGeometry args={[.46, 40, 28]} />
          <meshStandardMaterial color={yellow} roughness={.9} toneMapped={false} />
        </mesh>
        <mesh position={[0, .71, 0]} scale={[1, 1.02, .82]}>
          <sphereGeometry args={[.463, 36, 28, Math.PI * .15, Math.PI * .7, Math.PI * .2, Math.PI * .6]} />
          <meshBasicMaterial ref={face} map={textures.open} transparent depthWrite={false} polygonOffset polygonOffsetFactor={-1} toneMapped={false} />
        </mesh>
      </> : <group position={[0, .72, 0]}>
        <group matrix={shapeMatrix} matrixAutoUpdate={false}>
          <RoundedBox args={[.84, .8, .44]} radius={.13} smoothness={5} castShadow>
            <meshStandardMaterial color={yellow} roughness={.9} toneMapped={false} />
          </RoundedBox>
          <mesh position={[0, 0, .224]}>
            <planeGeometry args={[.84, .8]} />
            <meshBasicMaterial ref={face} map={textures.open} transparent depthWrite={false} toneMapped={false} />
          </mesh>
        </group>
      </group>}
      {[-1, 1].map((side) => <group key={side} ref={side < 0 ? leftArm : rightArm} position={[side * .44, .6, 0]}>
        <mesh position={[side * .045, -.055, .02]} rotation={[0, 0, side * .35]} scale={[.7, 1.05, .75]} castShadow>
          <sphereGeometry args={[.105, 18, 12]} /><meshStandardMaterial color={yellow} roughness={.9} toneMapped={false} />
        </mesh>
        <group name={side < 0 ? "left-hand-socket" : "right-hand-socket"} position={[side * .055, -.11, .04]}>
          {carrying && side > 0 ? <RoundedBox args={[.23, .28, .035]} radius={.025} position={[.02, -.03, .12]} rotation={[-.2, 0, -.18]}>
            <meshStandardMaterial color="#fff5da" />
          </RoundedBox> : null}
        </group>
      </group>)}
      {/* Wide, shallow shorts: a slight diagonal keeps the lower silhouette playful. */}
      <group position={[0, .335, 0]} rotation={[0, 0, -.035]}>
        <RoundedBox args={[.76, .18, .49]} radius={.03} castShadow>
          <meshStandardMaterial color={indigo} roughness={1} />
        </RoundedBox>
        <RoundedBox args={[.15, .095, .025]} radius={.015} position={[.22, .005, .255]}>
          <meshStandardMaterial color="#a492cb" roughness={1} />
        </RoundedBox>
        {[-1, 1].map((side) => <mesh key={side} position={[.22 + side * .022, .01, .273]} scale={[1, 1.05, .3]}>
          <sphereGeometry args={[.026, 12, 10]} /><meshBasicMaterial color="#ffe793" toneMapped={false} />
        </mesh>)}
        <mesh position={[0, -.045, .252]}><boxGeometry args={[.013, .07, .006]} /><meshStandardMaterial color="#63508f" /></mesh>
      </group>
      {inspector ? <group position={[silhouette === "slanted" ? .12 : .055, silhouette === "round" ? 1.165 : 1.12, -.025]} rotation={[0, 0, -.14]}>
        <mesh scale={[1, .3, .85]} castShadow><sphereGeometry args={[.22, 24, 16]} /><meshStandardMaterial color={indigo} roughness={1} /></mesh>
      </group> : null}
    </group>
  </group>;
}
