import assert from "node:assert/strict";
import { readFileSync, existsSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
process.chdir(fileURLToPath(new URL("..", import.meta.url)));
const read = (p) => JSON.parse(readFileSync(p, "utf8"));
const story = read("src/story.json");
const manifest = read("src/generated.json");
const captures = read("evidence/captures.json");
const checks = [];
for (const cut of ["full", "short"]) {
  const scenes = manifest[cut];
  assert.equal(
    scenes.reduce((n, s) => n + s.seconds, 0),
    cut === "full" ? 180 : 60,
  );
  assert.equal(new Set(scenes.map((s) => s.id)).size, scenes.length);
  let at = 0;
  for (const s of scenes) {
    assert.equal(s.start, at);
    assert.equal(s.durationInFrames, s.seconds * 30);
    at += s.seconds;
    const source =
      cut === "full"
        ? story.full.find((x) => x.id === s.id)
        : story.short.find((x) => x.ref === s.id);
    assert.equal(
      s.narration,
      source.narration,
      `${cut}/${s.id}: stale narration`,
    );
    if (s.audio) {
      assert(existsSync(`public/${s.audio}`));
      assert(s.audioSeconds > 0 && s.audioSeconds < s.seconds - 0.4);
    }
    if (s.image) {
      assert(existsSync(`public/screens/${s.image}.jpg`));
      assert(captures.captures.some((x) => x.file === s.image + ".jpg"));
    }
    assert(s.mode.length > 8);
  }
  checks.push(
    `${cut}: exact duration, contiguous timeline, current narration, assets, disclosures and audio fit`,
  );
}
const report = readFileSync("evidence/rusty-rod-results.md", "utf8");
assert(
  report.includes("| maintained_no_audit | 68/76 | 1/24 | 12/13 | 0/32 |"),
);
assert(report.includes("| append_only | 67/76 | 4/24 | 0/13 | 0/32 |"));
assert(report.includes("accuracy +1.3 [-5.3, +7.9]"));
const ctx = read("evidence/longmemeval-summary.json");
assert.equal(ctx.conditions.full.avg_ctx_tokens, 108946);
assert.equal(ctx.conditions.brainbob.avg_ctx_tokens, 2681);
assert.deepEqual(ctx.conditions.full.overall, [39, 50]);
assert.deepEqual(ctx.conditions.brainbob.overall, [35, 50]);
const meta = read("evidence/backend-run-meta.json");
assert.equal(Object.keys(meta.checks).length, 15);
assert(Object.values(meta.checks).every(Boolean));
const responses = read("evidence/backend-selected-responses.json");
assert.equal(responses.steps[0].response.answer, "6 PM");
assert(responses.steps[3].response.answer.includes("10 PM"));
checks.push(
  "Displayed benchmark counts match archived artifacts; backend trace contains 15 passed checks and both cited answers",
);
const hashes = {};
for (const c of captures.captures) {
  const path = `public/screens/${c.file}`;
  hashes[path] = createHash("sha256").update(readFileSync(path)).digest("hex");
}
if (process.argv.includes("--videos")) {
  for (const cut of ["full", "short"]) {
    const path = `out/brainbob-${cut}.mp4`;
    const probe = JSON.parse(
      execFileSync(
        "ffprobe",
        ["-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        { encoding: "utf8" },
      ),
    );
    const video = probe.streams.find((s) => s.codec_type === "video");
    assert.equal(video.width, 1920);
    assert.equal(video.height, 1080);
    assert.equal(video.r_frame_rate, "30/1");
    assert(probe.streams.some((s) => s.codec_type === "audio"));
    assert(probe.streams.some((s) => s.codec_type === "subtitle"));
    assert(
      Math.abs(Number(probe.format.duration) - (cut === "full" ? 180 : 60)) <
        0.1,
    );
    execFileSync("ffmpeg", ["-v", "error", "-i", path, "-f", "null", "-"], {
      stdio: ["ignore", "pipe", "pipe"],
    });
    hashes[path] = createHash("sha256")
      .update(readFileSync(path))
      .digest("hex");
    checks.push(
      `${cut}: full decode, 1080p/30fps, expected duration, audio and captions`,
    );
  }
}
const result = { checkedAt: new Date().toISOString(), checks, sha256: hashes };
writeFileSync("out/verification.json", JSON.stringify(result, null, 2) + "\n");
console.log(checks.join("\n"));
