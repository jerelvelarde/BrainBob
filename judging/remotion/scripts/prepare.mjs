import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
process.chdir(fileURLToPath(new URL("..", import.meta.url)));
const story = JSON.parse(readFileSync("src/story.json", "utf8"));
const fps = story.fps;
mkdirSync("public/audio", { recursive: true });
mkdirSync("out", { recursive: true });
const run = (bin, args) =>
  execFileSync(bin, args, {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
const probe = (path) =>
  Number(
    run("ffprobe", [
      "-v",
      "error",
      "-show_entries",
      "format=duration",
      "-of",
      "default=nw=1:nk=1",
      path,
    ]).trim(),
  );
const voice = process.env.BRAINBOB_VOICE || "Samantha";
const noAudio = process.argv.includes("--silent");
const timestamp = (s, sub = false) => {
  const ms = Math.round(s * 1000);
  return `${String(Math.floor(ms / 3600000)).padStart(2, "0")}:${String(Math.floor(ms / 60000) % 60).padStart(2, "0")}:${String(Math.floor(ms / 1000) % 60).padStart(2, "0")}${sub ? "," : "."}${String(ms % 1000).padStart(3, "0")}`;
};
const clocks = (s) =>
  `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
const output = {
  fps,
  voice: noAudio ? "None" : `macOS ${voice}, synthetic guide narration`,
  full: [],
  short: [],
};
let script =
  "# BrainBob demo: presenter script\n\nGenerated from `src/story.json`. Product screens are actual browser captures of the scripted walkthrough. The separate backend segment summarizes recorded real model calls. Results are measured artifacts, not new runs.\n\n";
for (const cut of ["full", "short"]) {
  const list =
    cut === "full"
      ? story.full
      : story.short.map((s) => ({
          ...story.full.find((x) => x.id === s.ref),
          ...s,
        }));
  let elapsed = 0;
  const cues = [];
  script += `## ${cut === "full" ? "Three-minute showcase" : "One-minute cut"}\n\n`;
  for (const scene of list) {
    const name = `${cut}-${scene.id}`;
    const wav = `public/audio/${name}.wav`;
    const hash = createHash("sha256")
      .update(JSON.stringify([scene.narration, scene.seconds, voice]))
      .digest("hex");
    let audioSeconds = 0;
    if (!noAudio) {
      if (
        !existsSync(wav) ||
        !existsSync(wav + ".sha256") ||
        readFileSync(wav + ".sha256", "utf8") !== hash
      ) {
        const textPath = `out/${name}.txt`;
        const aiff = `out/${name}.aiff`;
        writeFileSync(textPath, scene.narration);
        run("say", ["-v", voice, "-r", "172", "-f", textPath, "-o", aiff]);
        const original = probe(aiff);
        if (!Number.isFinite(original) || original <= 0)
          throw Error(
            "Speech synthesis produced empty audio. Run with access to macOS speech services, or pass --silent.",
          );
        const available = scene.seconds - 1.1;
        const speed = Math.max(1, original / available);
        if (speed > 1.24)
          throw Error(
            `${name}: narration too long (${original}s for ${available}s). Shorten the copy.`,
          );
        run("ffmpeg", [
          "-y",
          "-v",
          "error",
          "-i",
          aiff,
          "-af",
          `atempo=${speed},afade=t=in:d=0.035,afade=t=out:st=${Math.max(0, original / speed - 0.1)}:d=0.10`,
          "-ar",
          "48000",
          "-ac",
          "1",
          wav,
        ]);
        writeFileSync(wav + ".sha256", hash);
      }
      audioSeconds = probe(wav);
      if (audioSeconds > scene.seconds - 0.6)
        throw Error(`${name}: audio spills into next scene`);
    }
    const entry = {
      ...scene,
      start: elapsed,
      durationInFrames: scene.seconds * fps,
      audio: noAudio ? null : `audio/${name}.wav`,
      audioSeconds,
    };
    output[cut].push(entry);
    script += `### ${clocks(elapsed)}–${clocks(elapsed + scene.seconds)} · ${scene.title}\n\n**Say:** ${scene.narration}\n\n**Show:** ${scene.action}\n\n**On-screen disclosure:** ${scene.mode}\n\n`;
    const sentences = scene.narration
      .match(/[^.!?]+[.!?]+|[^.!?]+$/g)
      .map((s) => s.trim());
    const total = sentences.reduce((n, s) => n + s.split(/\s+/).length, 0);
    let at = elapsed + 0.4;
    for (const text of sentences) {
      const length =
        ((audioSeconds || scene.seconds - 1) * text.split(/\s+/).length) /
        total;
      cues.push({ start: at, end: at + length, text });
      at += length;
    }
    elapsed += scene.seconds;
    console.log(
      `${cut} ${scene.id}: ${audioSeconds.toFixed(2)}s voice / ${scene.seconds}s slot`,
    );
  }
  writeFileSync(
    `out/brainbob-${cut}.srt`,
    cues
      .map(
        (s, i) =>
          `${i + 1}\n${timestamp(s.start, true)} --> ${timestamp(s.end, true)}\n${s.text}\n`,
      )
      .join("\n"),
  );
  writeFileSync(
    `out/brainbob-${cut}.vtt`,
    "WEBVTT\n\n" +
      cues
        .map(
          (s) => `${timestamp(s.start)} --> ${timestamp(s.end)}\n${s.text}\n`,
        )
        .join("\n"),
  );
  if (elapsed !== (cut === "full" ? 180 : 60))
    throw Error(`${cut}: unexpected duration ${elapsed}`);
}
script +=
  "## Live rehearsal and fallback\n\n1. Run the frontend with `pnpm dev` from the repository root. Open `/demo`. It requires no backend key.\n2. Follow the scenario selector and controls listed above. Allow each animation to settle. Keep the scripted label visible.\n3. Use the rendered film if the browser or graphics stall. Say that it is a prepared presentation of captured screens.\n4. Present the backend segment as a recorded run. Its legacy identities differ from the current Rusty Rod selector, so do not connect that seeded scenario to this UI and claim they are the same live session.\n5. For a separate live backend demonstration, use `backend/demo/run_scenario.py` with an isolated backend and the documented environment. It makes paid inference calls. Do not reset another developer’s running state.\n6. Do not equate source correctness with leave-one-out usefulness. The latter asks whether removing a memory changes a graded answer.\n7. During Q&A, acknowledge unauthenticated demo member markers, pending durable server sessions, weak uncertainty answers, and unintegrated NemoClaw/Switchyard.\n\nThe WAV voice is a synthetic rehearsal guide. Replace each matching file under `public/audio/` with a human recording within its scene duration, then render without rerunning assets. Captions are sentence-level estimates, not forced-aligned transcripts.\n";
writeFileSync("SCRIPT.md", script);
writeFileSync("src/generated.json", JSON.stringify(output, null, 2) + "\n");
