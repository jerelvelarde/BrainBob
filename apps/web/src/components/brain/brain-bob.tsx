"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { RoundedBox } from "@react-three/drei";
import * as THREE from "three";

const butter = "#ffe28b";
const violet = "#b1a0cf";

function Foot({ side, legRef }: { side: number; legRef: React.Ref<THREE.Group> }) {
  return <group ref={legRef} position={[side * .15, .47, 0]}>
    <mesh position={[0, -.08, 0]} castShadow><capsuleGeometry args={[.045, .1, 4, 10]} /><meshStandardMaterial color={butter} /></mesh>
    <mesh position={[side * .012, -.2, .045]} scale={[1, .62, 1.35]} castShadow>
      <sphereGeometry args={[.11, 16, 12]} /><meshStandardMaterial color="#877799" roughness={1} />
    </mesh>
  </group>;
}

export function BrainBob({ walking = true, carrying = false, inspector = false, phase = 0 }: {
  walking?: boolean; carrying?: boolean; inspector?: boolean; phase?: number;
}) {
  const body = useRef<THREE.Group>(null);
  const leftLeg = useRef<THREE.Group>(null);
  const rightLeg = useRef<THREE.Group>(null);
  const leftArm = useRef<THREE.Group>(null);
  const rightArm = useRef<THREE.Group>(null);
  const time = useRef(phase);
  const smile = useMemo(() => new THREE.QuadraticBezierCurve3(
    new THREE.Vector3(-.065, .8, .285),
    new THREE.Vector3(0, .745, .29),
    new THREE.Vector3(.065, .8, .285),
  ), []);

  useFrame((_, delta) => {
    if (walking) time.current += Math.min(delta, .05) * 5;
    const sway = walking ? Math.sin(time.current) * .2 : 0;
    if (leftLeg.current) leftLeg.current.rotation.x = sway;
    if (rightLeg.current) rightLeg.current.rotation.x = -sway;
    if (leftArm.current) leftArm.current.rotation.x = -sway * .5;
    if (rightArm.current) rightArm.current.rotation.x = carrying ? -.35 : sway * .5;
    if (body.current) {
      body.current.position.y = walking ? Math.abs(Math.sin(time.current)) * .012 : 0;
      body.current.rotation.z = sway * .07;
    }
  });

  return <group ref={body}>
    {/* A shallow, soft round body keeps the face nestled in the silhouette. */}
    <mesh position={[0, .85, 0]} scale={[1, 1, .72]} castShadow>
      <sphereGeometry args={[.4, 32, 24]} /><meshStandardMaterial color={butter} roughness={1} />
    </mesh>
    {[-1, 1].map((side) => <group key={side}>
      <mesh position={[side * .13, .93, .264]} scale={[.9, 1.05, .2]}>
        <sphereGeometry args={[.103, 20, 16]} /><meshStandardMaterial color="#fff6da" roughness={1} />
      </mesh>
      <mesh position={[side * .13, .93, .282]} scale={[.82, 1.06, .22]}>
        <sphereGeometry args={[.083, 20, 16]} /><meshStandardMaterial color="#443746" roughness={.5} />
      </mesh>
      <mesh position={[side * .13 - .019, .958, .302]} scale={[1, 1, .35]}>
        <sphereGeometry args={[.024, 12, 10]} /><meshBasicMaterial color="#fffdf4" />
      </mesh>
      <mesh position={[side * .13 + .018, .911, .302]} scale={[1, 1, .35]}>
        <sphereGeometry args={[.011, 10, 8]} /><meshBasicMaterial color="#fff0d7" />
      </mesh>
      <mesh position={[side * .237, .817, .229]} rotation={[0, side * .45, 0]} scale={[1, .58, .12]}>
        <sphereGeometry args={[.077, 16, 12]} /><meshStandardMaterial color="#f1aaa5" roughness={1} />
      </mesh>
      <group ref={side < 0 ? leftArm : rightArm} position={[side * .365, .77, 0]}>
        <mesh position={[side * .035, -.07, .025]} rotation={[0, 0, side * .25]} castShadow>
          <capsuleGeometry args={[.052, .1, 4, 12]} /><meshStandardMaterial color={butter} roughness={1} />
        </mesh>
        <mesh position={[side * .055, -.15, .035]} scale={[1, .9, .8]} castShadow>
          <sphereGeometry args={[.068, 14, 12]} /><meshStandardMaterial color={butter} roughness={1} />
        </mesh>
      </group>
    </group>)}
    <mesh><tubeGeometry args={[smile, 16, .009, 6, false]} /><meshStandardMaterial color="#805557" /></mesh>

    {/* Soft overalls wrap the lower body without a tight white waistband. */}
    <mesh position={[0, .85, 0]} scale={[1, 1, .72]} castShadow>
      <sphereGeometry args={[.405, 32, 16, 0, Math.PI * 2, 2.08, Math.PI - 2.08]} />
      <meshStandardMaterial color={violet} roughness={1} />
    </mesh>
    <RoundedBox args={[.21, .15, .025]} radius={.04} position={[0, .65, .259]}>
      <meshStandardMaterial color={violet} roughness={1} />
    </RoundedBox>
    {[-1, 1].map((side) => <mesh key={side} position={[side * .025, .654, .279]} scale={[1, 1.05, .3]}>
      <sphereGeometry args={[.031, 12, 10]} /><meshStandardMaterial color="#fff3ca" />
    </mesh>)}
    <Foot side={-1} legRef={leftLeg} /><Foot side={1} legRef={rightLeg} />
    {carrying ? <RoundedBox args={[.24, .29, .04]} radius={.025} position={[.43, .65, .22]} rotation={[-.2, 0, -.2]}>
      <meshStandardMaterial color="#fff5da" />
    </RoundedBox> : null}
    {inspector ? <mesh position={[.035, 1.245, 0]} rotation={[0, 0, -.13]} scale={[1, .3, .85]} castShadow>
      <sphereGeometry args={[.245, 24, 16]} /><meshStandardMaterial color={violet} roughness={1} />
    </mesh> : null}
  </group>;
}
