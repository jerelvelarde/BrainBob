"use client";

import { useEffect, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { BrainBob } from "./brain/brain-bob";

function StudyCamera() {
  const { camera, size } = useThree();
  useEffect(() => {
    camera.position.set(0, .65, 8);
    camera.lookAt(0, .65, 0);
    camera.zoom = Math.min(size.width / 5.4, size.height / 2.8);
    camera.updateProjectionMatrix();
  }, [camera, size]);
  return null;
}

export default function Study() {
  const [animate, setAnimate] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(true);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(media.matches);
    update(); media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return <main className="character-study">
    <header><div><a href="/">← Back to the brain</a><h1>Finding BrainBob’s shape.</h1><p>Same bright yellow, face, and pants. Three silhouettes.</p></div>
      <button onClick={() => setAnimate(!animate)} disabled={reducedMotion} aria-pressed={animate}>{animate ? "Pause movement" : "Preview movement"}</button></header>
    <div className="character-study-canvas">
      <Canvas orthographic camera={{position:[0,.65,8],zoom:180}} dpr={[1,2]} aria-label="BrainBob silhouette comparison: circle, rounded rectangle, and gentle parallelogram">
        <color attach="background" args={["#f9f5eb"]}/>
        <ambientLight intensity={1.55} color="#fff5e2"/>
        <directionalLight position={[5,12,8]} intensity={2.8} color="#fff1d5"/>
        <group position={[-1.6,0,0]}><BrainBob silhouette="round" walking={animate && !reducedMotion}/></group>
        <BrainBob silhouette="rectangle" walking={animate && !reducedMotion}/>
        <group position={[1.6,0,0]}><BrainBob silhouette="slanted" walking={animate && !reducedMotion}/></group>
        <StudyCamera />
      </Canvas>
    </div>
    <div className="character-study-labels">
      <div><h2>Circle</h2><p>Soft, but less distinctive.</p></div>
      <div><h2>Rounded rectangle</h2><p>Chosen · clear face and silhouette.</p></div>
      <div><h2>Gentle parallelogram</h2><p>More attitude, with a little lean.</p></div>
    </div>
    <footer>Separate face, arms, hand sockets, and props leave room for expressions and task animations.</footer>
  </main>;
}
