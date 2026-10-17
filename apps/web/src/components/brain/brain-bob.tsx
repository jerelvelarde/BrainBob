"use client";

import { useEffect, useMemo, useRef, type RefObject } from "react";
import { useFrame } from "@react-three/fiber";
import { RoundedBox } from "@react-three/drei";
import * as THREE from "three";
import type { BobExpression, BobPerformance } from "@/lib/scene-animation";

const yellow = "#ffd21f";
const indigo = "#7962b2";

/** One graphic face, fitted to the body surface: no separate eyeballs or glass layers. */
function makeFaceTexture(blinking: boolean, expression: BobExpression = "happy") {
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
  if (expression === "worried") {
    ctx.beginPath(); ctx.ellipse(256, 325, 19, 24, 0, 0, Math.PI * 2); ctx.stroke();
    for (const x of [175, 337]) {
      ctx.beginPath(); ctx.moveTo(x - 26, 181); ctx.lineTo(x + 22, x < 256 ? 163 : 196); ctx.stroke();
    }
  } else if (expression === "focused") {
    ctx.beginPath(); ctx.moveTo(236, 318); ctx.lineTo(276, 318); ctx.stroke();
    // A graphic pince-nez gives the evaluator a distinct, still friendly face.
    ctx.lineWidth = 6;
    for (const x of [175, 337]) { ctx.beginPath(); ctx.roundRect(x - 47, 190, 94, 100, 25); ctx.stroke(); }
    ctx.beginPath(); ctx.moveTo(222, 230); ctx.lineTo(290, 230); ctx.stroke();
  } else {
    ctx.beginPath(); ctx.moveTo(222, 308); ctx.quadraticCurveTo(256, 346, 290, 308); ctx.stroke();
  }
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

export function BrainBob({ walking = true, carrying = false, inspector = false, phase = 0, distance, silhouette = "rectangle", performance }: {
  walking?: boolean; carrying?: boolean; inspector?: boolean; phase?: number; distance?: RefObject<number>; silhouette?: BrainBobSilhouette;
  performance?: RefObject<BobPerformance>;
}) {
  const body = useRef<THREE.Group>(null);
  const leftFoot = useRef<THREE.Group>(null);
  const rightFoot = useRef<THREE.Group>(null);
  const leftArm = useRef<THREE.Group>(null);
  const rightArm = useRef<THREE.Group>(null);
  const face = useRef<THREE.MeshBasicMaterial>(null);
  const paperProp = useRef<THREE.Group>(null);
  const penProp = useRef<THREE.Group>(null);
  const notebookProp = useRef<THREE.Group>(null);
  const elapsed = useRef(phase * 1.17);
  const shapeMatrix = useMemo(() => new THREE.Matrix4().set(
    1, silhouette === "slanted" ? .18 : 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    0, 0, 0, 1,
  ), [silhouette]);
  const textures = useMemo(() => ({ happy: makeFaceTexture(false), worried: makeFaceTexture(false, "worried"), focused: makeFaceTexture(false, "focused"), blink: makeFaceTexture(true) }), []);
  useEffect(() => () => { Object.values(textures).forEach((texture) => texture.dispose()); }, [textures]);

  useFrame((_, delta) => {
    const act = performance?.current;
    const moving = act ? act.walking : walking;
    if (moving) elapsed.current += Math.min(delta, .05);
    const time = act?.time ?? elapsed.current;
    const step = act ? act.distance * Math.PI * 2 / .72 : distance ? distance.current * Math.PI * 2 / .72 : elapsed.current * 6;
    const sway = moving ? Math.sin(step) : 0;
    const pose = act?.pose ?? (carrying ? "carry" : "idle");
    if (leftFoot.current) { leftFoot.current.position.y = .22 + Math.max(0, sway) * .045; leftFoot.current.position.z = .035 + sway * .055; }
    if (rightFoot.current) { rightFoot.current.position.y = .22 + Math.max(0, -sway) * .045; rightFoot.current.position.z = .035 - sway * .055; }
    if (leftArm.current) {
      leftArm.current.position.y = pose === "panic" ? .9 : .6;
      leftArm.current.rotation.x = pose === "inspect" || pose === "write" ? -.9 : -.16 * sway;
      leftArm.current.rotation.z = pose === "panic" ? -2.1 + Math.sin(time * 10) * .18 : 0;
    }
    if (rightArm.current) {
      rightArm.current.position.y = pose === "panic" ? .9 : .6;
      rightArm.current.rotation.x = pose === "write" ? -1.1 + Math.sin(time * 13) * .12 : pose === "present" || pose === "inspect" ? -1.2 : pose === "carry" ? -.65 : .16 * sway;
      rightArm.current.rotation.z = pose === "panic" ? 2.1 + Math.sin(time * 11) * .18 : pose === "write" ? -.15 : 0;
    }
    if (paperProp.current) paperProp.current.visible = pose !== "write" && (act ? act.paper : carrying);
    if (penProp.current) penProp.current.visible = pose === "write";
    if (notebookProp.current) notebookProp.current.visible = pose === "write";
    if (body.current) {
      body.current.position.y = moving ? Math.abs(sway) * (pose === "panic" ? .12 : .012) : 0;
      body.current.rotation.z = sway * (pose === "panic" ? .16 : .025);
      body.current.rotation.x = pose === "inspect" || pose === "write" ? .12 : 0;
    }
    if (face.current) {
      // Short staggered blinks; pausing or reduced motion leaves a calm open expression.
      const blink = moving && time % (3.6 + phase * .19) < .14;
      const expression = act?.expression ?? "happy";
      const map = blink && expression === "happy" ? textures.blink : textures[expression];
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
          <meshBasicMaterial ref={face} map={textures.happy} transparent depthWrite={false} polygonOffset polygonOffsetFactor={-1} toneMapped={false} />
        </mesh>
      </> : <group position={[0, .72, 0]}>
        <group matrix={shapeMatrix} matrixAutoUpdate={false}>
          <RoundedBox args={[.84, .8, .44]} radius={.13} smoothness={5} castShadow>
            <meshStandardMaterial color={yellow} roughness={.9} toneMapped={false} />
          </RoundedBox>
          <mesh position={[0, 0, .224]}>
            <planeGeometry args={[.84, .8]} />
            <meshBasicMaterial ref={face} map={textures.happy} transparent depthWrite={false} toneMapped={false} />
          </mesh>
        </group>
      </group>}
      {[-1, 1].map((side) => <group key={side} ref={side < 0 ? leftArm : rightArm} position={[side * .44, .6, 0]}>
        <mesh position={[side * .045, -.055, .02]} rotation={[0, 0, side * .35]} scale={[.7, 1.05, .75]} castShadow>
          <sphereGeometry args={[.105, 18, 12]} /><meshStandardMaterial color={yellow} roughness={.9} toneMapped={false} />
        </mesh>
        <group name={side < 0 ? "left-hand-socket" : "right-hand-socket"} position={[side * .055, -.11, .04]}>
          {side > 0 ? <>
            <group ref={paperProp} visible={carrying} position={[.02, -.03, .12]} rotation={[-.2, 0, -.18]}>
              <RoundedBox args={[.3, .36, .035]} radius={.018}><meshStandardMaterial color="#fff5da" /></RoundedBox>
              {[-.07, 0, .07].map((y) => <mesh key={y} position={[0, y, .02]}><boxGeometry args={[.19, .016, .003]} /><meshBasicMaterial color="#9d91b2" /></mesh>)}
            </group>
            <group ref={penProp} visible={false} position={[.08, .02, .18]} rotation={[.4, 0, -.4]}>
              <mesh><cylinderGeometry args={[.027, .027, .3, 8]} /><meshStandardMaterial color={indigo} /></mesh>
              <mesh position={[0, -.18, 0]} rotation={[Math.PI, 0, 0]}><coneGeometry args={[.022, .06, 8]} /><meshStandardMaterial color="#55443f" /></mesh>
            </group>
          </> : null}
        </group>
      </group>)}
      <group ref={notebookProp} visible={false} position={[.1, .53, .36]} rotation={[-.6, 0, 0]}>
        <RoundedBox args={[.5, .32, .045]} radius={.015}><meshStandardMaterial color="#fff5da" /></RoundedBox>
        {[-.07, 0, .07].map((y) => <mesh key={y} position={[0, y, .026]}><boxGeometry args={[.3, .014, .004]} /><meshBasicMaterial color="#9d91b2" /></mesh>)}
      </group>
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
