import type { MemoryAction, MemoryEvent, MemoryScope } from "./memory";
import { memberForReader } from "./sample-company";

/** Presentation only. These cues never create or change a memory. */
export type SceneAction = MemoryAction | "arrived" | "rejected" | "answered" | "promoted" | "flagged" | "locked" | "resolved";
export type SceneCue = { id: string; action: SceneAction; scope: MemoryScope; title: string; source: "fixture" | "trace" | "backend" | "session";
  seconds?: number; records?: { id: string; scope: MemoryScope; cabinetX?: number }[];
  cabinetX?: number; sessionLabel?: string; destination?: Point; noticeLabel?: string;
  evaluationLabel?: string;
  evaluation?: { phase: "start" | "check" | "finish"; verdict?: "helpful" | "harmful" | "unchanged" | "unconfirmed" } };
export type Point = [number, number];

/** A session gathers from three tier cabinets without changing record permissions. */
export function cueForSession(cue: SceneCue | undefined, reader: string): SceneCue | undefined {
  const member = memberForReader(reader);
  if (!cue || !member) return undefined;
  return { ...cue, cabinetX: scopeCharacters[cue.scope].x, sessionLabel: `${member.label.split(" ")[0]}’S SESSION`,
    records: cue.records?.map((record) => ({ ...record, cabinetX: scopeCharacters[record.scope].x })) };
}
export function cueCabinetX(cue: SceneCue) { return cue.cabinetX ?? scopeCharacters[cue.scope].x; }
export type BobPose = "idle" | "carry" | "write" | "panic" | "inspect" | "present";
export type BobExpression = "happy" | "worried" | "focused";
export type BobPerformance = { time: number; distance: number; walking: boolean; pose: BobPose; expression: BobExpression; paper: boolean; reaction?: "nod" | "shake" };
export type SceneCinematics = { darkness: number; heat: number; zoom: number };

/** Seekable lighting and a single camera punch, with no wall-clock noise or flashing. */
export function cinematicsAt(action: SceneAction | undefined, progress: number, reducedMotion = false): SceneCinematics {
  const p = Math.max(0, Math.min(1, progress));
  const ramp = (from: number, to: number) => {
    const u = Math.max(0, Math.min(1, (p - from) / (to - from)));
    return u * u * (3 - 2 * u);
  };
  if (action !== "forgotten") return { darkness: 0, heat: 0, zoom: 1 };
  const envelope = ramp(0, .12) * (1 - ramp(.88, 1));
  const punch = ramp(.04, .12) * (1 - ramp(.12, .3));
  return { darkness: envelope, heat: action === "forgotten" ? envelope : 0,
    zoom: reducedMotion ? 1 : 1 + envelope * .025 + punch * .065 };
}

export const scopeCharacters = {
  individual: { name: "Maya Flores", role: "Individual", x: -3.8, color: "#93bac3" },
  team: { name: "Sales", role: "Team", x: -.5, color: "#d7b268" },
  organization: { name: "Rusty Rod", role: "Organization", x: 3.2, color: "#c4ac7d" },
} satisfies Record<MemoryScope, { name: string; role: string; x: number; color: string }>;

export const sceneClips: Record<SceneAction, { label: string; seconds: number; phases: [string, string, string]; color: string }> = {
  arrived: { label: "Conversation", seconds: 6, phases: ["Mail’s here!", "A conversation arrives", "Ready for the curator"], color: "#9c87bb" },
  created: { label: "Store", seconds: 9, phases: ["Write it down", "Off to the right cabinet", "A new memory, filed"], color: "#c2a24a" },
  retrieved: { label: "Retrieve", seconds: 9, phases: ["Find the right cabinet", "Found it! Bring the record", "Memory delivered"], color: "#648f9f" },
  updated: { label: "Rewrite", seconds: 10, phases: ["Pull the old record", "Write the correction", "File the new version"], color: "#9375b2" },
  forgotten: { label: "Delete", seconds: 12, phases: ["CODE RED. Forget that!", "EVERYBOB PANIC!", "Crisis over. History preserved."], color: "#d26c45" },
  evaluated: { label: "Evaluate", seconds: 14, phases: ["Evaluator Bob arrives", "Checks the cited memories", "Check recorded"], color: "#8972af" },
  promoted: { label: "Promote", seconds: 7, phases: ["A helpful memory", "Up to the trusted shelf", "Trusted, with evidence"], color: "#b39243" },
  flagged: { label: "Flag", seconds: 7, phases: ["This record is locked", "A concern for the owner", "Flagged. Kept for review."], color: "#ce6c73" },
  rejected: { label: "Reject", seconds: 6, phases: ["Another record arrives", "Duplicate or tombstone", "Return to sender"], color: "#ba8168" },
  answered: { label: "Answer", seconds: 7, phases: ["Gather the citations", "Deliver the answer", "Sources attached"], color: "#648f9f" },
  locked: { label: "Lock", seconds: 5, phases: ["An owner’s house rule", "Lock the record", "Owner review required"], color: "#9375b2" },
  resolved: { label: "Resolve", seconds: 5, phases: ["The owner has decided", "Clear the flag", "Kept by its owner"], color: "#648f9f" },
};

/** Base vocabulary; backend-state.ts handles scoped and multi-event choreography. */
export const backendSceneActions = {
  "episode.ingested": "arrived", "memory.added": "created", "memory.rejected": "rejected",
  "memory.retrieved": "retrieved", "answer.produced": "answered",
  "evaluation.started": "evaluated", "memory.checked": "evaluated", "evaluation.finished": "evaluated",
  "memory.promoted": "promoted", "memory.retired": "forgotten", "memory.flagged": "flagged",
  "memory.locked": "locked", "memory.resolved": "resolved",
} as const satisfies Record<string, SceneAction>;

export function cueFromMemory(event?: MemoryEvent): SceneCue | undefined {
  if (!event || event.id.startsWith("seed-")) return;
  return { id: event.id, action: event.action, scope: event.scope, title: event.title, source: "trace" };
}

export function clipPhase(action: SceneAction, progress: number) {
  return sceneClips[action].phases[progress < .28 ? 0 : progress < .78 ? 1 : 2];
}

export const workerHomes: Point[] = [[-1.65, 2.4], [1.7, 3.3], [-5.3, 1.8], [-5.2, -1.7], [4.9, .4], [4.9, 3.2]];
type Waypoint = [time: number, x: number, z: number];

/** A single deterministic path sampler makes seek, pause, and replay agree. */
export function samplePath(points: Waypoint[], progress: number) {
  const p = Math.max(0, Math.min(1, progress));
  let distance = 0;
  for (let i = 1; i < points.length; i++) {
    const [t0, x0, z0] = points[i - 1];
    const [t1, x1, z1] = points[i];
    const length = Math.hypot(x1 - x0, z1 - z0);
    if (p <= t1) {
      const u = Math.max(0, Math.min(1, (p - t0) / (t1 - t0)));
      const eased = u * u * (3 - 2 * u);
      return { x: x0 + (x1 - x0) * eased, z: z0 + (z1 - z0) * eased,
        angle: length > .01 ? Math.atan2(x1 - x0, z1 - z0) : .55,
        distance: distance + length * eased, moving: length > .01 && u > 0 && u < 1 };
    }
    distance += length;
  }
  const last = points[points.length - 1];
  return { x: last[1], z: last[2], angle: .55, distance, moving: false };
}

export function workerPerformance(action: SceneAction, scope: MemoryScope, index: number, progress: number, cabinetX?: number) {
  const p = Math.max(0, Math.min(1, progress));
  const [hx, hz] = workerHomes[index];
  const x = cabinetX ?? scopeCharacters[scope].x;
  let path: Waypoint[] = [[0, hx, hz], [1, hx, hz]];
  let pose: BobPose = "idle";
  let expression: BobExpression = "happy";
  let paper = false;
  if (action === "evaluated") {
    if (index === 4) {
      path = [[0, 6.3, 3.1], [.24, 4.8, .5], [1, 4.8, .5]];
      pose = "inspect"; expression = "focused"; paper = true;
    } else {
      const bx = [-3.8, -.5, 3.2, -3.8, 0, -.5][index];
      const [qx, qz] = [[2, 0], [2.9, 1.3], [1.6, 2.6], [3.2, 3.1], [0, 0], [4.6, 2.6]][index];
      // Staggered trips from the three banks to an orderly queue at the audit desk.
      const delay = index * .025;
      path = [[0, hx, hz], [.12 + delay, hx, -2.3], [.3 + delay, bx, -2.3],
        [.41 + delay, bx, -2.3], [.58 + delay, 1.9, -2.3],
        [.76 + delay, qx, qz], [1, qx, qz]];
      pose = p > .76 ? "present" : "panic"; expression = "worried"; paper = p > .3;
    }
  } else if (action === "forgotten") {
    const side = hx < 0 ? -1 : 1;
    const lane = [0, 0, 1, 2, 1, 2][index];
    const outside = side * (6.2 - lane * .35);
    const front = 2 + lane * .95;
    path = [[0, hx, hz], [.12, outside, hz], [.38, outside, -2.6 + lane * .28], [.57, outside, front],
      [.75, side * (.9 + lane * 1.2), front], [.91, outside, front], [1, outside, front]];
    pose = p > .94 ? "idle" : "panic"; expression = p > .94 ? "happy" : "worried"; paper = p < .8;
  } else if (index === (action === "retrieved" || action === "answered" ? 1 : 0)) {
    if (action === "retrieved") {
      path = [[0, 1.7, 3.3], [.18, 1.7, -2.3], [.34, x, -2.3], [.45, x, -2.3], [.62, 1.7, -2.3], [.84, 1.7, 2.5], [1, .7, 2.5]];
      paper = p > .36 && p < .92; pose = "carry";
    } else if (action === "created" || action === "updated") {
      path = action === "updated"
        ? [[0, x, -2.3], [.18, -2, -2.3], [.32, -2, .9], [.58, -2, .9], [.7, -2, -2.3], [.88, x, -2.3], [1, x, -2.3]]
        : [[0, -2, .9], [.24, -2, .9], [.48, -2, -2.3], [.78, x, -2.3], [1, x, -2.3]];
      const writing = action === "updated" ? p > .32 && p < .58 : p < .24;
      pose = writing ? "write" : p > .8 ? "present" : "carry";
      expression = writing ? "focused" : "happy"; paper = p < .85;
    } else if (action === "answered") {
      path = [[0, 4.8, .5], [.3, 4.8, 2.6], [.7, .7, 2.6], [1, .7, 2.6]];
      paper = p < .8; pose = "present";
    } else {
      path = [[0, x - 1.2, -2.3], [.3, x, -2.3], [.7, x, -2.3], [1, x - .7, -2.3]];
      pose = action === "flagged" ? "inspect" : "present";
      expression = action === "flagged" || action === "rejected" ? "worried" : "happy";
      paper = action !== "flagged";
    }
  }
  const sample = samplePath(path, p);
  return { ...sample, pose, expression, paper };
}

/** Backend audit clips visit only the cited record, rather than staging a whole-brain inspection. */
export function performanceForCue(cue: SceneCue, index: number, progress: number) {
  if (cue.action === "retrieved" && cue.destination && index === 1) {
    const x = cueCabinetX(cue), [dx, dz] = cue.destination;
    const sample = samplePath([[0, 1.7, 3.3], [.18, 1.7, -2.3], [.34, x, -2.3], [.45, x, -2.3], [.65, 1.7, -2.3], [.85, dx + 1, dz + 1], [1, dx, dz + .9]], progress);
    return { ...sample, pose: "carry" as const, expression: "happy" as const, paper: progress > .36 && progress < .92 };
  }
  if (!cue.evaluation) return workerPerformance(cue.action, cue.scope, index, progress, cue.cabinetX);
  if (index !== 4) {
    // Keep the worried crew spread around their desks while the cited paper travels.
    // Reusing the rehearsal's converging paths for every check piled them onto the inspector.
    const [x, z] = workerHomes[index];
    return { ...samplePath([[0, x, z], [1, x, z]], progress), pose: "panic" as const, expression: "worried" as const, paper: true };
  }
  // Enter through the open right side; the evaluator never mobilizes the whole crew.
  const path: Waypoint[] = cue.evaluation.phase === "start" ? [[0, 7.8, 3.2], [.7, 4.8, 2.3], [1, 4.8, 2.3]]
    : cue.evaluation.phase === "finish" ? [[0, 4.8, 2.3], [.3, 4.8, 2.3], [1, 7.8, 3.2]]
    : [[0, 4.8, 2.3], [1, 4.8, 2.3]];
  return { ...samplePath(path, progress), pose: "inspect" as const, expression: "focused" as const, paper: true };
}
