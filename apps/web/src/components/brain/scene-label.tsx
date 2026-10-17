"use client";

import { useEffect, useMemo } from "react";
import { Billboard } from "@react-three/drei";
import * as THREE from "three";

export function Label({ text, position, width = 1.8, selected = false, onClick }: {
  text: string; position: [number, number, number]; width?: number; selected?: boolean; onClick?: () => void;
}) {
  const texture = useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 512; canvas.height = 96;
    const context = canvas.getContext("2d");
    if (context) {
      context.fillStyle = selected ? "#f2d67a" : "#fbf9e9";
      context.beginPath(); context.roundRect(2, 2, 508, 92, 14); context.fill();
      context.strokeStyle = "#ded1b8"; context.lineWidth = 3; context.stroke();
      context.fillStyle = "#63533d"; context.font = "bold 30px monospace";
      context.textAlign = "center"; context.textBaseline = "middle"; context.fillText(text, 256, 50);
    }
    const map = new THREE.CanvasTexture(canvas); map.colorSpace = THREE.SRGBColorSpace;
    return map;
  }, [text, selected]);
  useEffect(() => () => texture.dispose(), [texture]);
  return <Billboard position={position}><mesh onClick={onClick ? (e) => { e.stopPropagation(); onClick(); } : undefined}>
    <planeGeometry args={[width, width * 96 / 512]} /><meshBasicMaterial map={texture} transparent depthWrite={false} />
  </mesh></Billboard>;
}
