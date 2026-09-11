/* Stopping the stage in progress. Not shipped — see smoke/README.md.
 *
 * Two halves, because server rendering can only prove a first paint:
 *
 *   - the selectors are pure functions, so `selectCanStop` and `selectStoppableStage` are called
 *     directly against seeded state. That is where the real decisions are — *whether* there is
 *     something to stop, and *which* stage it is — and a stop aimed at the wrong stage would
 *     supersede the wrong cards.
 *   - the render checks prove the bar appears and names that stage, and that the card left behind
 *     says what was discarded. The inline confirm is local component state, so its second step is
 *     not reachable here and is not asserted.
 *
 * What none of this proves is the abort actually landing on the wire — `generationRequests` is a
 * module-level map and the stream is never started under a render check.
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";
import { shallow } from "zustand/vanilla/shallow";
import { GenerationStream } from "../src/pipeline/GenerationStream";
import { ASSET_BY_ID } from "../src/data/assetCatalog";
import {
  selectCanStop,
  selectNeedsResume,
  selectStoppableStage,
  usePipelineStore,
  type PipelineMessage,
} from "../src/pipeline/pipelineStore";
import { useUiStore } from "../src/store/uiStore";

let pass = 0;
const fails: string[] = [];
const ok = (name: string, cond: boolean, extra?: string) => {
  if (cond) pass++;
  else fails.push(name + (extra ? `  ->  ${extra}` : ""));
};

/** See the note above `render()` in card.tsx for why the initial state is mutated. */
function seed(patch: Record<string, unknown>) {
  const base = {
    started: true,
    isLoadingSession: false,
    phase: "phase1" as const,
    messages: [],
    currentIndex: 2,
    intake: null,
    subStep: null,
    activeStatus: null,
    progress: 0,
    navStatus: "Ready" as const,
  };
  const full = { ...base, ...patch };
  usePipelineStore.setState(full as never);
  Object.assign(usePipelineStore.getInitialState(), full);
}
function seedUi(patch: Record<string, unknown>) {
  useUiStore.setState(patch as never);
  Object.assign(useUiStore.getInitialState(), patch);
}

const PILLAR = ASSET_BY_ID.pillar_page;
const CRO = ASSET_BY_ID.cro;

function generation(over: Partial<PipelineMessage> = {}): PipelineMessage {
  return {
    id: "g1",
    role: "assistant",
    kind: "generation",
    assetId: "pillar_page",
    text: "Some generated markup.",
    phase: "phase1",
    createdAt: Date.now(),
    ...over,
  };
}

function question(over: Partial<PipelineMessage> = {}): PipelineMessage {
  return {
    id: "q1",
    role: "assistant",
    kind: "question",
    assetId: "pillar_page",
    field: PILLAR.fields[0],
    phase: "phase1",
    createdAt: Date.now(),
    ...over,
  };
}

const state = () => usePipelineStore.getState();

/* ---------- when there is something to stop ---------- */
{
  seedUi({ demoMode: false, workTab: "transcript", hintsOn: true });

  seed({
    intake: { asset: PILLAR, answers: {}, awaitingFieldId: PILLAR.fields[0].field_id },
    activeStatus: "running",
    navStatus: "Awaiting Input",
    messages: [question()],
  });
  ok("intake: stoppable", selectCanStop(state()) === true);
  ok("intake: names the stage", selectStoppableStage(state())?.assetId === "pillar_page", JSON.stringify(selectStoppableStage(state())));

  seed({ activeStatus: "running", messages: [generation({ streaming: true })] });
  ok("streaming: stoppable", selectCanStop(state()) === true);

  seed({ subStep: "competitor", activeStatus: "running", messages: [] });
  ok("competitor sub-step: stoppable", selectCanStop(state()) === true);

  // A finished draft nobody saved is still work in progress — the operator can decide they do not
  // want it, and Save/Refine/Re-run are not ways to say that.
  seed({ activeStatus: "hitl", navStatus: "Awaiting Review", messages: [generation({ savePhase: "idle" })] });
  ok("unsaved draft: stoppable", selectCanStop(state()) === true);
}

/* ---------- when there is not ---------- */
{
  seed({ messages: [generation({ savePhase: "saved" })] });
  ok("saved work only: nothing to stop", selectCanStop(state()) === false);

  seed({ started: false, messages: [] });
  ok("not started: nothing to stop", selectCanStop(state()) === false);

  seed({ isLoadingSession: true, activeStatus: "running", messages: [generation({ streaming: true })] });
  ok("loading a chat: nothing to stop", selectCanStop(state()) === false);

  // Past the last stage the run is finished; there is no stage in progress to abandon.
  seed({ currentIndex: 15, messages: [generation({ savePhase: "saved" })] });
  ok("run complete: nothing to stop", selectCanStop(state()) === false);

  seed({ messages: [generation({ savePhase: "idle", superseded: true })] });
  ok("superseded draft only: nothing to stop", selectCanStop(state()) === false);
}

/* ---------- Phase 2's run-level questions are not assets ---------- */
{
  // Both are properties of the run, not of a stage. Offering "Stop this asset" at either would
  // clear the intake and leave the question on screen with nothing behind it — and the sub-service
  // card carries no `assetId`, so the supersede pass would not even reach it.
  const P2_FIRST = ASSET_BY_ID.pillar_page;
  seed({
    phase: "phase2",
    intake: { asset: P2_FIRST, answers: {}, awaitingFieldId: "sub_service" },
    activeStatus: "running",
    navStatus: "Awaiting Input",
    messages: [],
  });
  ok("phase2: not stoppable on the sub-service question", selectCanStop(state()) === false);

  seed({
    phase: "phase2",
    activeStatus: "running",
    messages: [
      {
        id: "sr1",
        role: "assistant",
        kind: "source-run",
        sourceRunStatus: "pending",
        phase: "phase2",
        createdAt: Date.now(),
      },
    ],
  });
  ok("phase2: not stoppable while the parent run is unchosen", selectCanStop(state()) === false);

  // Once it is chosen the leg is under way like any other, and its stages are stoppable again.
  seed({
    phase: "phase2",
    activeStatus: "running",
    currentIndex: 0,
    messages: [
      {
        id: "sr1",
        role: "assistant",
        kind: "source-run",
        sourceRunStatus: "chosen",
        phase: "phase2",
        createdAt: Date.now(),
      },
      generation({ id: "g3", streaming: true }),
    ],
  });
  ok("phase2: stoppable once the run-level questions are answered", selectCanStop(state()) === true);
  seed({ phase: "phase1" });
}

/* ---------- which stage gets stopped ---------- */
{
  // A retry or a refine streams into a card for an earlier stage while `currentIndex` sits further
  // on. Stopping has to act on the stream, not on the cursor, or it supersedes the wrong stage's
  // cards and leaves the real one running.
  seed({
    currentIndex: 6,
    activeStatus: "running",
    messages: [generation({ id: "s1", assetId: "cro", streaming: true })],
  });
  ok("target: the streaming stage wins over the cursor", selectStoppableStage(state())?.assetId === "cro", JSON.stringify(selectStoppableStage(state())));

  seed({
    currentIndex: 6,
    intake: { asset: CRO, answers: {}, awaitingFieldId: "client_name" },
    activeStatus: "running",
    messages: [],
  });
  ok("target: the intake's asset wins over the cursor", selectStoppableStage(state())?.assetId === "cro");

  seed({ currentIndex: 2, activeStatus: "hitl", messages: [] });
  ok("target: falls back to the cursor", selectStoppableStage(state())?.assetId === "pillar_page", JSON.stringify(selectStoppableStage(state())));

  seed({ currentIndex: 2, activeStatus: "hitl", messages: [] });
  ok("target: carries the label the button shows", selectStoppableStage(state())?.label === PILLAR.label, JSON.stringify(selectStoppableStage(state())));
}

/* ---------- the bar ---------- */
{
  seed({
    intake: { asset: PILLAR, answers: {}, awaitingFieldId: PILLAR.fields[0].field_id },
    activeStatus: "running",
    navStatus: "Awaiting Input",
    messages: [question()],
  });
  const html = renderToStaticMarkup(<GenerationStream />);
  ok("bar: offered", html.includes("Stop this asset"), html.slice(0, 700));
  ok("bar: names what is being worked on", html.includes("Working on") && html.includes(PILLAR.label), html.slice(0, 700));
  // One click away from destroying work in flight would be too few.
  ok("bar: does not stop on the first click", !html.includes("Keep going"), html.slice(0, 900));

  seed({ messages: [generation({ savePhase: "saved" })] });
  const done = renderToStaticMarkup(<GenerationStream />);
  ok("bar: absent with nothing in progress", !done.includes("Stop this asset"), done.slice(0, 700));
}

{
  // Finished work is a different surface; a stage in progress is not on screen there.
  seedUi({ demoMode: false, workTab: "deliverables", hintsOn: true });
  seed({
    intake: { asset: PILLAR, answers: {}, awaitingFieldId: PILLAR.fields[0].field_id },
    activeStatus: "running",
    messages: [question(), generation({ id: "g2", savePhase: "saved" })],
  });
  const html = renderToStaticMarkup(<GenerationStream />);
  ok("bar: absent on the deliverables tab", !html.includes("Stop this asset"), html.slice(0, 800));
  seedUi({ workTab: "transcript" });
}

/* ---------- the card left behind ---------- */
{
  const stoppedCard = (wasGenerating: boolean): PipelineMessage => ({
    id: "x1",
    role: "assistant",
    kind: "stage-stopped",
    assetId: "pillar_page",
    stopped: { assetId: "pillar_page", label: PILLAR.label, wasGenerating },
    phase: "phase1",
    createdAt: Date.now(),
  });

  seed({ messages: [stoppedCard(false)] });
  const intakeStop = renderToStaticMarkup(<GenerationStream />);
  ok("card: says the stage stopped", intakeStop.includes(`${PILLAR.label} stopped`), intakeStop.slice(-1200));
  ok("card: says the answers went", intakeStop.includes("answers given for it were discarded"), intakeStop.slice(-1200));
  ok("card: says approved work is untouched", intakeStop.includes("already approved has changed"), intakeStop.slice(-1200));
  ok("card: offers a restart", intakeStop.includes(`Start ${PILLAR.label} again`), intakeStop.slice(-1200));
  ok("card: points at the pipeline panel", intakeStop.includes("Asset Pipeline panel"), intakeStop.slice(-1400));

  seed({ messages: [stoppedCard(true)] });
  const streamStop = renderToStaticMarkup(<GenerationStream />);
  ok("card: says the request was cancelled", streamStop.includes("request was cancelled"), streamStop.slice(-1200));
  // Claiming a cancelled request where none was in flight would be a lie about what was spent.
  ok("card: only claims that when it happened", !intakeStop.includes("request was cancelled"), intakeStop.slice(-1200));
}

/* ---------- the resume banner must not contradict it ---------- */
{
  const stopped: PipelineMessage = {
    id: "x1",
    role: "assistant",
    kind: "stage-stopped",
    assetId: "pillar_page",
    stopped: { assetId: "pillar_page", label: PILLAR.label, wasGenerating: false },
    phase: "phase1",
    createdAt: Date.now(),
  };
  seed({ currentIndex: 2, messages: [generation({ id: "g9", savePhase: "saved", assetId: "cro" }), stopped] });
  ok("resume: banner suppressed after a stop", selectNeedsResume(state()) === false);
  const html = renderToStaticMarkup(<GenerationStream />);
  ok(
    "resume: does not offer to continue the stage just stopped",
    !html.includes("Pick up where you left off"),
    html.slice(-1000),
  );
}

/* Snapshot stability - the bug that white-screened the whole app.
 *
 * `selectStoppableStage` returns a fresh `{ assetId, label }` per call, and zustand v5 compares the
 * `useSyncExternalStore` snapshot with `Object.is` (the equality argument v4 had is gone). Passed
 * bare, it therefore reported "changed" on every commit and re-rendered until React threw "Maximum
 * update depth exceeded" - which, with no error boundary above it, unmounted the entire tree.
 *
 * Server rendering cannot reproduce that: SSR takes `getServerSnapshot` and never runs the passive
 * effect that detects the moved snapshot. So neither assertion here is a render check.
 *   - the first two pin the mechanism: the selector allocates per call (the hazard), but its
 *     results are shallow-equal, which is what `useShallow` turns into one stable reference.
 *   - the second proves the call site still uses it. Unwrapping it is a one-word edit that nothing
 *     else in this file - or in any render check - would notice.
 */
{
  seed({
    currentIndex: 2,
    intake: { asset: PILLAR, answers: {}, awaitingFieldId: "reference_design_source" },
  });
  const a = selectStoppableStage(state());
  const b = selectStoppableStage(state());
  // The defect, stated directly: two calls over identical state are NOT the same reference, which
  // is exactly what `Object.is` on the store snapshot trips over.
  ok("snapshot: selector allocates a new object per call (the hazard)", !Object.is(a, b));
  // ...but they are shallow-equal, which is the property `useShallow` converts into a stable
  // reference. A selector that stopped being value-stable would defeat the wrapper silently.
  ok("snapshot: successive results are shallow-equal, so useShallow can hold them", shallow(a, b));
  ok("snapshot: and still resolves the right stage", a?.assetId === "pillar_page");

  // Walked up from this bundle rather than hard-coded: these checks run from smoke/out-<name>/,
  // not from the source tree, so a fixed "../src/..." silently resolves to smoke/src.
  let dir = fileURLToPath(new URL(".", import.meta.url));
  let srcPath = "";
  for (let i = 0; i < 5 && !srcPath; i++) {
    const candidate = join(dir, "src", "pipeline", "GenerationStream.tsx");
    if (existsSync(candidate)) srcPath = candidate;
    dir = dirname(dir);
  }
  ok("snapshot: located GenerationStream.tsx to check", srcPath !== "");
  const src = srcPath ? readFileSync(srcPath, "utf8") : "";
  ok(
    "snapshot: GenerationStream wraps selectStoppableStage in useShallow",
    /usePipelineStore\(\s*useShallow\(\s*selectStoppableStage\s*\)\s*\)/.test(src),
  );
}

console.log(`\n${pass} passed, ${fails.length} failed`);
if (fails.length) {
  console.log("\nFAILURES:");
  fails.forEach((f) => console.log("  x " + f));
  process.exitCode = 1;
}
