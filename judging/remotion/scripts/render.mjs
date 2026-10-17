import { bundle } from "@remotion/bundler";
import {
  renderMedia,
  renderStill,
  selectComposition,
} from "@remotion/renderer";
import { mkdirSync, readFileSync, existsSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
process.chdir(fileURLToPath(new URL("..", import.meta.url)));
mkdirSync("out/stills", { recursive: true });
const localChrome =
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const browserExecutable =
  process.env.BRAINBOB_CHROME ||
  (existsSync(localChrome) ? localChrome : undefined);
const serveUrl = await bundle({
  entryPoint: resolve("src/index.tsx"),
  publicDir: resolve("public"),
});
const shared = {
  serveUrl,
  browserExecutable,
  chromiumOptions: { gl: "swangle" },
  logLevel: "warn",
};
const full = await selectComposition({ ...shared, id: "BrainBobShowcase" });
const generated = JSON.parse(readFileSync("src/generated.json", "utf8"));
if (process.argv.includes("--stills")) {
  for (const [i, s] of generated.full.entries()) {
    const sceneArg = process.argv.find((x) => x.startsWith("--scene="));
    if (sceneArg && s.id !== sceneArg.split("=")[1]) continue;
    const frame =
      s.start * 30 +
      Math.min(s.durationInFrames - 20, Math.round(s.durationInFrames * 0.72));
    await renderStill({
      ...shared,
      composition: full,
      frame,
      output: resolve(
        `out/stills/${String(i + 1).padStart(2, "0")}-${s.id}.png`,
      ),
    });
    console.log(`Still ${i + 1}: ${s.title}`);
  }
} else {
  const renderLog = [];
  for (const [id, cut] of [
    ["BrainBobOneMinute", "short"],
    ["BrainBobShowcase", "full"],
  ]) {
    const composition =
      id === "BrainBobShowcase"
        ? full
        : await selectComposition({ ...shared, id });
    let last = -1;
    const start = new Date();
    await renderMedia({
      ...shared,
      composition,
      codec: "h264",
      crf: 19,
      x264Preset: "fast",
      concurrency: 8,
      outputLocation: resolve(`out/brainbob-${cut}-raw.mp4`),
      onProgress: ({ progress }) => {
        const bucket = Math.floor(progress * 10);
        if (bucket > last) {
          last = bucket;
          console.log(`${id}: ${bucket * 10}%`);
        }
      },
    });
    execFileSync("ffmpeg", [
      "-y",
      "-v",
      "error",
      "-i",
      `out/brainbob-${cut}-raw.mp4`,
      "-i",
      `out/brainbob-${cut}.srt`,
      "-map",
      "0:v",
      "-map",
      "0:a",
      "-map",
      "1:0",
      "-c:v",
      "copy",
      "-c:a",
      "copy",
      "-c:s",
      "mov_text",
      "-metadata:s:s:0",
      "language=eng",
      "-movflags",
      "+faststart",
      `out/brainbob-${cut}.mp4`,
    ]);
    renderLog.push({
      id,
      startedAt: start.toISOString(),
      finishedAt: new Date().toISOString(),
      file: `out/brainbob-${cut}.mp4`,
      width: composition.width,
      height: composition.height,
      frames: composition.durationInFrames,
      fps: composition.fps,
    });
    writeFileSync("out/render-log.json", JSON.stringify(renderLog, null, 2));
    console.log(`Finished ${id}`);
  }
}
