import React from "react";
import {
  AbsoluteFill,
  Audio,
  Composition,
  Img,
  Sequence,
  interpolate,
  registerRoot,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import generated from "./generated.json";
import trace from "../evidence/backend-selected-responses.json";
import context from "../evidence/longmemeval-summary.json";
type Scene = (typeof generated.full)[number];
const C = {
  paper: "#f6f2e9",
  ink: "#292820",
  muted: "#716e64",
  purple: "#6c568a",
  line: "#d9d2c4",
  green: "#426847",
  red: "#9f5145",
};
const label: React.CSSProperties = {
  fontSize: 20,
  fontWeight: 700,
  letterSpacing: 2.6,
  lineHeight: 1.5,
};
function Reveal({
  children,
  delay = 0,
  style = {},
}: {
  children: React.ReactNode;
  delay?: number;
  style?: React.CSSProperties;
}) {
  const f = useCurrentFrame();
  const p = interpolate(f, [delay, delay + 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        opacity: p,
        transform: `translateY(${(1 - p) * 20}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
function Header({ title }: { title: string }) {
  return (
    <Reveal style={{ position: "absolute", left: 72, top: 64, right: 72 }}>
      <div style={{ ...label, color: C.purple, marginBottom: 18 }}>
        THE SHARED BRAIN
      </div>
      <h1
        style={{
          fontSize: 66,
          lineHeight: 1.04,
          letterSpacing: -2.3,
          margin: 0,
          fontWeight: 700,
        }}
      >
        {title}
      </h1>
    </Reveal>
  );
}
function Picture({
  name,
  style,
}: {
  name: string;
  style: React.CSSProperties;
}) {
  return (
    <Img
      src={staticFile(`screens/${name}.jpg`)}
      style={{ objectFit: "contain", ...style }}
    />
  );
}
function Screen({
  scene,
  portrait = false,
}: {
  scene: Scene;
  portrait?: boolean;
}) {
  return (
    <>
      <Header title={scene.title} />
      <Reveal
        delay={9}
        style={{
          position: "absolute",
          left: 72,
          top: 310,
          width: portrait ? 750 : 350,
        }}
      >
        <div
          style={{
            fontSize: portrait ? 104 : 82,
            fontWeight: 700,
            color: C.purple,
            letterSpacing: -5,
            lineHeight: 1.05,
          }}
        >
          {scene.metric}
        </div>
        <p
          style={{
            fontSize: portrait ? 36 : 30,
            lineHeight: 1.5,
            whiteSpace: "pre-line",
            marginTop: 35,
            color: C.muted,
          }}
        >
          {scene.detail}
        </p>
        {scene.id === "audit" && portrait ? (
          <p
            style={{
              fontSize: 28,
              lineHeight: 1.5,
              marginTop: 45,
              maxWidth: 650,
            }}
          >
            An older source cannot replace the later approval.
            <br />
            <strong style={{ color: C.ink }}>
              Insufficient evidence means retain.
            </strong>
          </p>
        ) : null}
      </Reveal>
      <Reveal
        delay={7}
        style={{
          position: "absolute",
          left: portrait ? 970 : 475,
          top: portrait ? 200 : 220,
          width: portrait ? 850 : 1373,
          height: portrait ? 785 : 772,
        }}
      >
        <Picture
          name={scene.image!}
          style={{
            width: "100%",
            height: "100%",
            borderRadius: 12,
            filter: "drop-shadow(0 18px 22px #29282016)",
          }}
        />
      </Reveal>
    </>
  );
}
function Cover({ scene }: { scene: Scene }) {
  return (
    <>
      <Reveal
        style={{
          position: "absolute",
          left: 72,
          top: 190,
          zIndex: 2,
          width: 650,
        }}
      >
        <div style={{ ...label, color: C.purple, marginBottom: 28 }}>
          RECURSIVE AGENTS HACKATHON
        </div>
        <h1
          style={{
            fontSize: 136,
            lineHeight: 1,
            letterSpacing: -8,
            margin: "0 0 35px",
          }}
        >
          BrainBob
        </h1>
        <p
          style={{
            fontSize: 54,
            lineHeight: 1.12,
            letterSpacing: -1.6,
            margin: 0,
            maxWidth: 550,
          }}
        >
          {scene.subtitle}
        </p>
        <p style={{ fontSize: 25, color: C.muted, marginTop: 65 }}>
          Memory correctness for agent teams
        </p>
      </Reveal>
      <Reveal
        delay={6}
        style={{
          position: "absolute",
          left: 720,
          top: 165,
          width: 1135,
          height: 690,
        }}
      >
        <Picture name="office" style={{ width: "100%", height: "100%" }} />
      </Reveal>
    </>
  );
}
function Architecture() {
  const rows = [
    [
      "The workspace",
      "Next.js + React Three Fiber",
      "CopilotKit chat, session files, source inspection",
    ],
    [
      "The memory service",
      "Python + FastAPI",
      "Scoped BM25 retrieval, maintenance, JSONL history",
    ],
    [
      "The model connection",
      "Direct Crusoe inference",
      "Nemotron answering and extraction, gpt-oss judging",
    ],
  ];
  return (
    <>
      <Header title="What we built" />
      <div style={{ position: "absolute", left: 72, right: 72, top: 245 }}>
        {rows.map((r, i) => (
          <Reveal
            key={r[0]}
            delay={10 + i * 12}
            style={{
              display: "grid",
              gridTemplateColumns: "410px 580px 1fr",
              gap: 30,
              borderTop: `1px solid ${C.line}`,
              padding: "35px 0",
              alignItems: "start",
            }}
          >
            <div style={{ fontSize: 31, color: C.purple }}>{r[0]}</div>
            <div style={{ fontSize: 37, fontWeight: 700 }}>{r[1]}</div>
            <div style={{ fontSize: 28, lineHeight: 1.4, color: C.muted }}>
              {r[2]}
            </div>
          </Reveal>
        ))}
      </div>
      <Reveal
        delay={50}
        style={{
          position: "absolute",
          left: 72,
          top: 810,
          fontSize: 28,
          lineHeight: 1.6,
          color: C.muted,
        }}
      >
        HTTP requests perform work. SSE events drive the office and retrace.
        <br />
        Pending: authentication, durable server sessions, NemoClaw and
        Switchyard.
      </Reveal>
    </>
  );
}
function Trace() {
  const f = useCurrentFrame();
  const stages = [
    ["01 / ASK", "6 PM", "Wrong answer cites m2"],
    ["02 / CHECK", "Wrong → right", "Remove m2 and re-ask"],
    ["03 / REVIEW", "Retire m2", "Fresh confirmation passed; promote m3"],
    ["04 / FRESH AGENT", "10 PM", "New question cites m1"],
  ];
  return (
    <>
      <Header title="A recorded real-model correction loop" />
      <div
        style={{
          position: "absolute",
          left: 72,
          right: 72,
          top: 260,
          display: "grid",
          gridTemplateColumns: "repeat(4,1fr)",
          gap: 44,
        }}
      >
        {stages.map((s, i) => (
          <Reveal
            key={s[0]}
            delay={10 + i * 18}
            style={{ borderTop: `5px solid ${C.purple}`, paddingTop: 24 }}
          >
            <div style={{ ...label, color: C.muted }}>{s[0]}</div>
            <div
              style={{
                fontSize: i === 1 ? 49 : 66,
                fontWeight: 700,
                lineHeight: 1.1,
                margin: "24px 0",
                color: i === 0 ? C.red : i === 3 ? C.green : C.ink,
              }}
            >
              {s[1]}
            </div>
            <div style={{ fontSize: 27, lineHeight: 1.4 }}>{s[2]}</div>
          </Reveal>
        ))}
      </div>
      <Reveal
        delay={80}
        style={{
          position: "absolute",
          left: 72,
          right: 72,
          top: 575,
          borderTop: `1px solid ${C.line}`,
          paddingTop: 30,
        }}
      >
        <div style={{ ...label, color: C.purple }}>
          RECORDED RESPONSE / JOHN / m1
        </div>
        <blockquote
          style={{
            fontSize: 44,
            lineHeight: 1.3,
            margin: "20px 0",
            maxWidth: 1610,
          }}
        >
          “{trace.steps[3].response.answer}”
        </blockquote>
      </Reveal>
      <div
        style={{
          position: "absolute",
          left: 72,
          right: 72,
          top: 850,
          fontSize: 24,
          lineHeight: 1.5,
          color: C.muted,
        }}
      >
        Oct 17, 13:16 PDT. Two prior harmful-task signals came from seeded real
        calls.
        <br />
        Separate legacy scenario. 15/15 recorded checks passed. Selected
        example, not an accuracy benchmark.
      </div>
    </>
  );
}
function Bar({
  title,
  value,
  max,
  color,
  note,
  delay = 0,
}: {
  title: string;
  value: number;
  max: number;
  color: string;
  note: string;
  delay?: number;
}) {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    fps,
    frame: Math.max(0, f - delay),
    config: { damping: 200 },
    durationInFrames: 40,
  });
  return (
    <div style={{ marginBottom: 38 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 30,
          marginBottom: 15,
        }}
      >
        <span>{title}</span>
        <strong>{note}</strong>
      </div>
      <div style={{ height: 32, background: "#e3ded2" }}>
        <div
          style={{
            height: "100%",
            width: `${((100 * value) / max) * p}%`,
            background: color,
          }}
        />
      </div>
    </div>
  );
}
function Correctness() {
  return (
    <>
      <Header title="Maintenance keeps the right fact active" />
      <Reveal
        delay={7}
        style={{ position: "absolute", left: 72, top: 250, width: 1070 }}
      >
        <div style={{ ...label, color: C.muted, marginBottom: 35 }}>
          CORRECT MEMORY UPDATES
        </div>
        <Bar
          title="Append-only memory"
          value={0}
          max={13}
          color={C.line}
          note="0 / 13"
          delay={10}
        />
        <Bar
          title="Write-time maintenance"
          value={12}
          max={13}
          color={C.purple}
          note="12 / 13"
          delay={20}
        />
        <p
          style={{
            fontSize: 28,
            lineHeight: 1.6,
            color: C.muted,
            marginTop: 55,
          }}
        >
          Answer accuracy:{" "}
          <strong style={{ color: C.ink }}>68/76 vs 67/76</strong>
          <br />
          Paired difference +1.3 points, 95% CI [−5.3, +7.9]
          <br />
          No significant answer gain. Recent audit added +0.0 points.
        </p>
      </Reveal>
      <Reveal
        delay={24}
        style={{ position: "absolute", left: 1280, top: 285, width: 540 }}
      >
        <div
          style={{
            fontSize: 135,
            letterSpacing: -7,
            fontWeight: 700,
            color: C.green,
          }}
        >
          0 / 32
        </div>
        <p style={{ fontSize: 34, lineHeight: 1.35, marginTop: 8 }}>
          Valid memories
          <br />
          wrongly retired
        </p>
        <p
          style={{
            fontSize: 25,
            color: C.muted,
            lineHeight: 1.5,
            marginTop: 50,
          }}
        >
          30 synthetic held-out scenarios.
          <br />
          Deterministic grading.
          <br />
          One run, 76 questions per condition.
        </p>
      </Reveal>
      <div
        style={{
          position: "absolute",
          left: 72,
          bottom: 108,
          fontSize: 21,
          color: C.muted,
        }}
      >
        Source: Rusty Rod held-out run 20261017-131504. Weakness: maintained
        answers named unresolved conflicts in 0/3 checks.
      </div>
    </>
  );
}
function Context() {
  const full = context.conditions.full,
    bb = context.conditions.brainbob;
  return (
    <>
      <Header title="Less context, with an accuracy tradeoff" />
      <Reveal
        delay={8}
        style={{ position: "absolute", left: 72, top: 250, width: 1070 }}
      >
        <div style={{ ...label, color: C.muted, marginBottom: 35 }}>
          AVERAGE ANSWER CONTEXT / TOKENS
        </div>
        <Bar
          title="Full conversation history"
          value={full.avg_ctx_tokens}
          max={full.avg_ctx_tokens}
          color="#c4bba9"
          note={full.avg_ctx_tokens.toLocaleString("en-US")}
          delay={10}
        />
        <Bar
          title="BrainBob retrieved memory"
          value={bb.avg_ctx_tokens}
          max={full.avg_ctx_tokens}
          color={C.purple}
          note={bb.avg_ctx_tokens.toLocaleString("en-US")}
          delay={20}
        />
        <p style={{ fontSize: 32, lineHeight: 1.6, marginTop: 55 }}>
          Correct answers: <strong>35/50</strong> with BrainBob
          <br />
          versus <strong>39/50</strong> with full history
        </p>
      </Reveal>
      <Reveal
        delay={20}
        style={{ position: "absolute", left: 1280, top: 290, width: 540 }}
      >
        <div
          style={{
            fontSize: 160,
            letterSpacing: -8,
            fontWeight: 700,
            color: C.purple,
          }}
        >
          40×
        </div>
        <p style={{ fontSize: 34, lineHeight: 1.35, marginTop: 5 }}>
          Smaller answer context
          <br />
          <span style={{ color: C.muted }}>approximately</span>
        </p>
        <p
          style={{
            fontSize: 25,
            lineHeight: 1.5,
            marginTop: 50,
            color: C.muted,
          }}
        >
          Four fewer correct answers.
          <br />
          Extraction + retrieval only.
          <br />
          No audit in this run.
        </p>
      </Reveal>
      <div
        style={{
          position: "absolute",
          left: 72,
          bottom: 108,
          fontSize: 21,
          color: C.muted,
        }}
      >
        Source: LongMemEval subset 20261017-110432. n=50. gpt-oss-120b judge
        differs from official protocol. No claim of parity.
      </div>
    </>
  );
}
function Close() {
  return (
    <>
      <Reveal style={{ position: "absolute", left: 72, top: 170, width: 1650 }}>
        <div style={{ ...label, color: C.purple, marginBottom: 35 }}>
          BRAINBOB
        </div>
        <h1
          style={{
            fontSize: 112,
            letterSpacing: -5,
            lineHeight: 1.06,
            margin: 0,
            maxWidth: 1450,
          }}
        >
          Shared memory,
          <br />
          with a visible history
        </h1>
        <p
          style={{
            fontSize: 38,
            color: C.muted,
            marginTop: 45,
            lineHeight: 1.5,
          }}
        >
          Inspect what an agent knows.
          <br />
          Trace why it changed.
        </p>
      </Reveal>
      <Reveal
        delay={20}
        style={{
          position: "absolute",
          left: 72,
          top: 800,
          right: 72,
          borderTop: `1px solid ${C.line}`,
          paddingTop: 30,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "start",
        }}
      >
        <div style={{ fontSize: 34, fontWeight: 700 }}>
          github.com/jerelvelarde/BrainBob
        </div>
        <div
          style={{
            fontSize: 24,
            color: C.muted,
            lineHeight: 1.5,
            textAlign: "right",
          }}
        >
          Next: authentication, durable sessions,
          <br />
          stronger uncertainty handling
        </div>
      </Reveal>
    </>
  );
}
function Slide({
  scene,
  index,
  total,
}: {
  scene: Scene;
  index: number;
  total: number;
}) {
  const f = useCurrentFrame();
  const fade = interpolate(
    f,
    [scene.durationInFrames - 10, scene.durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  return (
    <AbsoluteFill
      style={{
        fontFamily: "Arial, Helvetica, sans-serif",
        color: C.ink,
        background: C.paper,
        opacity: fade,
      }}
    >
      {scene.kind === "cover" ? (
        <Cover scene={scene} />
      ) : scene.kind === "screen" || scene.kind === "portrait" ? (
        <Screen scene={scene} portrait={scene.kind === "portrait"} />
      ) : scene.kind === "architecture" ? (
        <Architecture />
      ) : scene.kind === "trace" ? (
        <Trace />
      ) : scene.kind === "correctness" ? (
        <Correctness />
      ) : scene.kind === "context" ? (
        <Context />
      ) : (
        <Close />
      )}
      <div
        style={{
          position: "absolute",
          left: 72,
          right: 72,
          bottom: 34,
          display: "flex",
          justifyContent: "space-between",
          fontSize: 18,
          color: C.muted,
        }}
      >
        <span>{scene.mode}</span>
        <span>
          BrainBob / {String(index + 1).padStart(2, "0")}—
          {String(total).padStart(2, "0")}
        </span>
      </div>
    </AbsoluteFill>
  );
}
function Film({
  cut = "full",
  voice = true,
}: {
  cut?: "full" | "short";
  voice?: boolean;
}) {
  const scenes = generated[cut] as Scene[];
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      {scenes.map((scene, index) => (
        <Sequence
          key={scene.id}
          name={scene.title}
          from={scene.start * generated.fps}
          durationInFrames={scene.durationInFrames}
        >
          <Slide scene={scene} index={index} total={scenes.length} />
          {voice && scene.audio ? (
            <Sequence from={12}>
              <Audio src={staticFile(scene.audio)} volume={0.92} />
            </Sequence>
          ) : null}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}
const Root = () => (
  <>
    <Composition
      id="BrainBobShowcase"
      component={Film}
      durationInFrames={5400}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{ cut: "full" as const, voice: true }}
    />
    <Composition
      id="BrainBobOneMinute"
      component={Film}
      durationInFrames={1800}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{ cut: "short" as const, voice: true }}
    />
    <Composition
      id="BrainBobPresenter"
      component={Film}
      durationInFrames={5400}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{ cut: "full" as const, voice: false }}
    />
  </>
);
registerRoot(Root);
