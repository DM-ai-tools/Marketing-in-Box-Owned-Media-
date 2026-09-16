import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useReducedMotion } from "framer-motion";
import { Markdown } from "../components/Markdown";
import {
  NODE_H,
  NODE_W,
  ancestorsOf,
  layoutPlan,
  pathToNode,
} from "../lib/planLayout";
import { buildPlanTree, flattenPlan, type PlanNodeKind } from "../lib/planTree";

/**
 * The Plan of Action as an interactive tree, with the document one click away.
 *
 * The plan is the one asset in the pipeline that is a *structure* rather than a piece of writing —
 * three phases, a set of sub-services, a hundred named assets and a month-by-month order to build
 * them in. Read as ten thousand words of prose that structure is present but unusable: you cannot
 * see how many assets Phase 2 implies, or which sub-service ranks first, without holding the whole
 * document in your head.
 *
 * Minimal on purpose, and specifically *not* colour-coded by asset type. `index.css` is a strict
 * dual-tone system — every surface a tint of ink or paper, with exactly three accents reserved for
 * state (blue running, amber needs-review, green done). Ten category hues would collide with all
 * three and turn a diagram into a legend nobody reads. Type is carried by a small monospace tag
 * instead, which is legible at any zoom and survives a black-and-white print.
 *
 * The text is never replaced. `Document` switches to the same outline every other asset gets, and
 * the diagram is derived from that document rather than from a second generation — so the two can
 * never disagree, and a plan this cannot draw falls back to the document with a stated reason.
 */

/** Short tag per kind. Upper-case and monospace, so it reads as a label rather than a word. */
const KIND_TAG: Record<PlanNodeKind, string> = {
  root: "PLAN",
  phase: "PHASE",
  summary: "SUMMARY",
  timeline: "TIMELINE",
  table: "TABLE",
  "sub-service": "SERVICE",
  category: "GROUP",
  page: "PAGE",
  blog: "BLOG",
  "lead-magnet": "MAGNET",
  funnel: "FUNNEL",
  email: "EMAIL",
  sms: "SMS",
  "case-study": "CASE",
  video: "VIDEO",
  industry: "INDUSTRY",
  location: "LOCATION",
  keyword: "KEYWORD",
  detail: "",
};

/** The three structural kinds get the accent; everything else stays neutral. */
const ACCENTED = new Set<PlanNodeKind>(["root", "phase"]);

const ZOOM_MIN = 0.35;
const ZOOM_MAX = 1.6;

function Stars({ value }: { value: number }) {
  return (
    <span className="shrink-0 text-[0.6rem] tabular-nums text-[var(--fg-faint)]" title={`${value} of 5`}>
      {"★".repeat(value)}
      {"☆".repeat(Math.max(0, 5 - value))}
    </span>
  );
}

export function PlanMindMap({ text, label }: { text: string; label: string }) {
  const tree = useMemo(() => buildPlanTree(text, label), [text, label]);
  const all = useMemo(() => flattenPlan(tree.root), [tree.root]);
  const reduceMotion = useReducedMotion();

  /* Root and its top-level sections open, everything below closed. Opening the whole tree on mount
   * puts two hundred nodes on screen at a zoom where none of them is readable, which is the wall of
   * text again in a different shape. */
  const initialExpanded = useMemo(
    () => new Set<string>([tree.root.id, ...tree.root.children.map((c) => c.id)]),
    [tree.root],
  );
  const [expanded, setExpanded] = useState<Set<string>>(initialExpanded);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 16, y: 16 });
  const [query, setQuery] = useState("");
  const [fullscreen, setFullscreen] = useState(false);

  const viewport = useRef<HTMLDivElement>(null);
  const dragging = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);

  useEffect(() => setExpanded(initialExpanded), [initialExpanded]);

  const layout = useMemo(() => layoutPlan(tree.root, expanded), [tree.root, expanded]);
  const selected = selectedId ? all.find((n) => n.id === selectedId) : undefined;
  const litPath = useMemo(
    () => (selectedId ? new Set(pathToNode(tree.root, selectedId)) : new Set<string>()),
    [selectedId, tree.root],
  );

  const toggle = useCallback((id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const fit = useCallback(() => {
    const box = viewport.current;
    if (!box) return;
    const scale = Math.min(
      1,
      (box.clientWidth - 32) / Math.max(1, layout.width),
      (box.clientHeight - 32) / Math.max(1, layout.height),
    );
    setZoom(Math.max(ZOOM_MIN, scale));
    setPan({ x: 16, y: 16 });
  }, [layout.width, layout.height]);

  /* Entering or leaving fullscreen changes how much room the tree has, so re-fit it to the new
   * box. Without this the map keeps the zoom it was given for a 22-40rem card and opens full-screen
   * as a small tree marooned in a large empty area — which reads as the button not having worked.
   *
   * On the frame after the layer is painted, because `fit` measures `viewport.clientHeight` and the
   * portalled node has no size until the browser has laid it out. */
  useEffect(() => {
    const frame = window.requestAnimationFrame(() => fit());
    return () => window.cancelAnimationFrame(frame);
  }, [fullscreen, fit]);

  /* Escape closes it, and the page behind must not scroll while a full-viewport layer is over it —
   * the same two obligations `HtmlPreview` carries for its pop-out. Both are wired only while
   * fullscreen is actually open, so the plain card leaves no listener behind. */
  useEffect(() => {
    if (!fullscreen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setFullscreen(false);
    };
    window.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [fullscreen]);

  const expandAll = () => setExpanded(new Set(all.filter((n) => n.children.length).map((n) => n.id)));
  const collapseAll = () => setExpanded(new Set([tree.root.id]));

  /** Reveal a node: open every branch above it and select it. */
  const reveal = useCallback(
    (id: string) => {
      setExpanded((prev) => new Set([...prev, ...ancestorsOf(tree.root, id)]));
      setSelectedId(id);
    },
    [tree.root],
  );

  const hits = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (needle.length < 2) return [];
    return all
      .filter((n) => n.id !== "root")
      .filter((n) => n.title.toLowerCase().includes(needle) || n.body.toLowerCase().includes(needle))
      .slice(0, 8);
  }, [query, all]);

  // Wheel to zoom, drag to pan. `passive: false` because the handler calls preventDefault to stop
  // the page scrolling behind the diagram.
  useEffect(() => {
    const box = viewport.current;
    if (!box) return;
    const onWheel = (event: WheelEvent) => {
      if (!event.ctrlKey && Math.abs(event.deltaY) < 2) return;
      event.preventDefault();
      setZoom((z) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, z * (event.deltaY < 0 ? 1.08 : 0.92))));
    };
    box.addEventListener("wheel", onWheel, { passive: false });
    return () => box.removeEventListener("wheel", onWheel);
  }, []);

  if (!tree.available) {
    return (
      <div className="mt-2 rounded-xl border border-[var(--border)] bg-[var(--bg-sunken)] px-3 py-2.5 text-[0.8rem] text-[var(--fg-muted)]">
        <span className="font-semibold text-[var(--fg)]">No diagram for this plan.</span>{" "}
        {tree.reason} The full document is below, unchanged.
      </div>
    );
  }

  const canvas = (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--bg-sunken)]">
      {/* Header strip: the plan's headline figures, which are the first thing anyone asks of a plan. */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-[var(--border)] px-2.5 py-1.5 text-[0.72rem] text-[var(--fg-muted)]">
        <span className="font-semibold text-[var(--fg)]">{tree.totals.nodes} nodes</span>
        <span>{tree.totals.phases} phases</span>
        <span>{tree.totals.assets} named assets</span>
        {tree.totals.months ? <span>{tree.totals.months}-month timeline</span> : null}
        <span className="flex-1" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Find a node…"
          aria-label="Find a node in the plan"
          className="w-[8.5rem] rounded-full border border-[var(--border-strong)] bg-[var(--bg)] px-2 py-[2px] text-[0.7rem] outline-none focus:border-[var(--color-electric-blue)]"
        />
        <button type="button" onClick={expandAll} className="cursor-pointer hover:text-[var(--fg)]">
          Expand all
        </button>
        <button type="button" onClick={collapseAll} className="cursor-pointer hover:text-[var(--fg)]">
          Collapse
        </button>
        <button type="button" onClick={fit} className="cursor-pointer hover:text-[var(--fg)]">
          Fit
        </button>
        <button
          type="button"
          onClick={() => setFullscreen((v) => !v)}
          className="cursor-pointer font-semibold hover:text-[var(--fg)]"
        >
          {fullscreen ? "Exit fullscreen" : "Fullscreen"}
        </button>
      </div>

      {hits.length > 0 && (
        <div className="flex flex-wrap gap-1 border-b border-[var(--border)] px-2.5 py-1.5">
          {hits.map((hit) => (
            <button
              key={hit.id}
              type="button"
              onClick={() => reveal(hit.id)}
              className="cursor-pointer rounded-full border border-[var(--border-strong)] px-2 py-[2px] text-[0.68rem] hover:bg-[var(--hover)]"
            >
              {hit.title.slice(0, 40)}
            </button>
          ))}
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        <div
          ref={viewport}
          className="relative min-h-0 flex-1 cursor-grab overflow-hidden active:cursor-grabbing"
          onPointerDown={(e) => {
            if ((e.target as HTMLElement).closest("[data-node]")) return;
            dragging.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
            (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
          }}
          onPointerMove={(e) => {
            const drag = dragging.current;
            if (!drag) return;
            setPan({ x: drag.panX + (e.clientX - drag.x), y: drag.panY + (e.clientY - drag.y) });
          }}
          onPointerUp={() => {
            dragging.current = null;
          }}
          onPointerLeave={() => {
            dragging.current = null;
          }}
        >
          <div
            className="absolute left-0 top-0 origin-top-left"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              width: layout.width,
              height: layout.height,
            }}
          >
            <svg
              width={layout.width}
              height={layout.height}
              className="absolute left-0 top-0 overflow-visible"
              aria-hidden
            >
              {layout.edges.map((edge) => {
                const lit = litPath.has(edge.fromId) && litPath.has(edge.toId);
                return (
                  <path
                    key={edge.id}
                    d={edge.path}
                    fill="none"
                    strokeWidth={lit ? 1.8 : 1.1}
                    stroke={lit ? "var(--color-electric-blue)" : "var(--border-strong)"}
                    /* The data-flow animation, and only on the branch leading to the selected node.
                     * Animating every edge at once is decoration that competes with the content;
                     * animating the one path the operator just asked about shows the plan flowing
                     * from the root to the thing they clicked. */
                    className={lit && !reduceMotion ? "plan-flow" : undefined}
                  />
                );
              })}
            </svg>

            {layout.nodes.map(({ node, x, y, collapsed, hasChildren }) => {
              const accent = ACCENTED.has(node.kind);
              const isSelected = node.id === selectedId;
              const onPath = litPath.has(node.id);
              return (
                <div
                  key={node.id}
                  data-node={node.id}
                  className="absolute flex items-center gap-1.5 rounded-lg border px-2 text-left"
                  style={{
                    left: x,
                    top: y,
                    width: NODE_W,
                    height: NODE_H,
                    backgroundColor: isSelected ? "var(--bg-raised)" : "var(--bg)",
                    borderColor: isSelected
                      ? "var(--color-electric-blue)"
                      : onPath
                        ? "color-mix(in srgb, var(--color-electric-blue) 45%, var(--border))"
                        : "var(--border)",
                    boxShadow: isSelected
                      ? "0 0 0 3px color-mix(in srgb, var(--color-electric-blue) 14%, transparent)"
                      : undefined,
                  }}
                >
                  {hasChildren ? (
                    <button
                      type="button"
                      onClick={() => toggle(node.id)}
                      aria-label={collapsed ? `Expand ${node.title}` : `Collapse ${node.title}`}
                      aria-expanded={!collapsed}
                      className="flex h-4 w-4 shrink-0 cursor-pointer items-center justify-center rounded border border-[var(--border-strong)] text-[0.62rem] font-bold leading-none text-[var(--fg-muted)] hover:bg-[var(--hover)]"
                    >
                      {collapsed ? "+" : "−"}
                    </button>
                  ) : (
                    <span
                      aria-hidden
                      className="h-1 w-1 shrink-0 rounded-full"
                      style={{ backgroundColor: "var(--border-strong)" }}
                    />
                  )}

                  <button
                    type="button"
                    onClick={() => setSelectedId(node.id)}
                    className="min-w-0 flex-1 cursor-pointer text-left"
                    title={node.title}
                  >
                    <span
                      className="block truncate text-[0.72rem] font-semibold leading-tight"
                      style={accent ? { color: "var(--color-electric-blue)" } : undefined}
                    >
                      {node.title}
                    </span>
                    <span className="flex items-center gap-1.5 leading-tight">
                      {KIND_TAG[node.kind] && (
                        <span className="font-mono text-[0.55rem] tracking-wider text-[var(--fg-faint)]">
                          {KIND_TAG[node.kind]}
                        </span>
                      )}
                      {node.volume ? (
                        <span className="text-[0.58rem] tabular-nums text-[var(--fg-faint)]">
                          ~{node.volume.toLocaleString()}/mo
                        </span>
                      ) : null}
                      {node.stars ? <Stars value={node.stars} /> : null}
                    </span>
                  </button>

                  {collapsed && node.count > 0 && (
                    <span className="shrink-0 rounded-full bg-[var(--bg-sunken)] px-1 text-[0.58rem] tabular-nums text-[var(--fg-muted)]">
                      {node.count}
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          <div className="pointer-events-none absolute bottom-1.5 left-2 text-[0.62rem] text-[var(--fg-faint)]">
            drag to pan · scroll to zoom · {Math.round(zoom * 100)}%
          </div>
        </div>

        {/* The detail panel. A node's own text, verbatim — the diagram is a way into the document,
            not a summary of it. */}
        <div className="hidden w-[17rem] shrink-0 flex-col border-l border-[var(--border)] bg-[var(--bg)] md:flex">
          {selected ? (
            <>
              <div className="border-b border-[var(--border)] px-2.5 py-2">
                <p className="text-[0.8rem] font-semibold leading-tight">{selected.title}</p>
                <p className="mt-0.5 flex items-center gap-2 text-[0.62rem] text-[var(--fg-faint)]">
                  {KIND_TAG[selected.kind] && <span className="font-mono tracking-wider">{KIND_TAG[selected.kind]}</span>}
                  {selected.count > 0 && <span>{selected.count} below</span>}
                  {selected.slug && <span className="truncate font-mono">{selected.slug}</span>}
                </p>
              </div>
              <div className="doc-measure pane-scroll min-h-0 flex-1 overflow-y-auto px-2.5 py-2"
                style={{ "--md-cover": "var(--bg)", "--doc-measure": "100%" } as React.CSSProperties}>
                {selected.body.trim() ? (
                  <Markdown text={selected.body} />
                ) : (
                  <p className="text-[0.76rem] text-[var(--fg-muted)]">
                    This node is a heading — its detail is in the {selected.count} node
                    {selected.count === 1 ? "" : "s"} beneath it.
                  </p>
                )}
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center px-3 text-[0.76rem] leading-relaxed text-[var(--fg-muted)]">
              Click any node to read that step in full. Use <span className="mx-1 font-semibold">+</span> to open a
              branch.
            </div>
          )}
        </div>
      </div>
    </div>
  );

  if (fullscreen) {
    const layer = (
      <div className="fixed inset-0 z-50 flex flex-col gap-2 bg-[var(--bg)] p-3">
        <p className="shrink-0 text-[0.8rem] font-semibold">{label} — plan map</p>
        {canvas}
      </div>
    );

    // Portalled to `<body>`, and that is the whole fix rather than a tidiness preference.
    //
    // `position: fixed` resolves against the viewport *only* while no ancestor establishes a
    // containing block, and in this transcript two separate ancestors do:
    //
    //   * the transcript pane is a Tailwind `@container` (`container-type: inline-size`), which
    //     applies containment;
    //   * every card carries `.msg-rise`, whose `animation-fill-mode: both` leaves the final
    //     keyframe's `transform: translateY(0)` applied for good — a transform, therefore a
    //     containing block, permanently and not just for the 0.28s the animation runs.
    //
    // So `inset-0` pinned the "fullscreen" map to the *card*, and since the transcript column is
    // narrower than the map's normal `clamp(22rem,58vh,40rem)` box, pressing Fullscreen made the
    // tree smaller — which is exactly what it looked like. Rendering into `<body>` escapes both
    // ancestors, and is the same treatment `HtmlPreview` already needed for its pop-out.
    //
    // Rendered in place when there is no document to portal into, which is where `smoke/` runs.
    return typeof document === "undefined" ? layer : createPortal(layer, document.body);
  }

  return <div className="mt-2 flex h-[clamp(22rem,58vh,40rem)] flex-col">{canvas}</div>;
}
