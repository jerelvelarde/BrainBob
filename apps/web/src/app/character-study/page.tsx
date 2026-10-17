"use client";
import dynamic from "next/dynamic";
const Study = dynamic(() => import("@/components/character-study"), {ssr:false});
export default function Page() { return <Study />; }
