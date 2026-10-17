"use client";

import { RoundedBox } from "@react-three/drei";

/** One session dossier; the three tabs are individual, team, and organization context. */
export function SessionFolder() {
  return <group>
    <RoundedBox args={[.67, .76, .055]} radius={.035} position={[0, 0, -.04]} castShadow><meshStandardMaterial color="#d9ad64" /></RoundedBox>
    {["#93bac3", "#d7b268", "#baa6ce"].map((color, i) => <group key={color} position={[0, i * .025, .005 + i * .018]}>
      <mesh><boxGeometry args={[.58, .66, .012]} /><meshStandardMaterial color="#fff8e8" /></mesh>
      <RoundedBox args={[.16, .1, .025]} radius={.02} position={[-.2 + i * .2, .35, 0]}><meshStandardMaterial color={color} /></RoundedBox>
    </group>)}
    <RoundedBox args={[.67, .51, .04]} radius={.025} position={[0, -.13, .09]} castShadow><meshStandardMaterial color="#e8c17d" /></RoundedBox>
    <mesh position={[0, -.08, .113]}><planeGeometry args={[.4, .16]} /><meshStandardMaterial color="#fff6dc" /></mesh>
    {[-.04, -.09].map((y) => <mesh key={y} position={[0, y, .115]}><planeGeometry args={[.28, .018]} /><meshBasicMaterial color="#967f60" /></mesh>)}
  </group>;
}
