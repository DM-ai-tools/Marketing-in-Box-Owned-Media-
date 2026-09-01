import { useState } from "react";
import { motion } from "framer-motion";
import { FieldHint } from "../components/FieldHint";
import { HeadlineSearchProgress } from "./HeadlineSearchProgress";
import { usePipelineStore } from "./pipelineStore";
import type { PipelineMessage } from "./pipelineStore";
import type { HeadlineCandidate } from "./pipelineApi";

/** At least ten suggested topics for a field the operator would otherwise have typed cold.
 *
 * The design problem here is not "show a list" — it is that a list of ten fluent headlines all look
 * equally good, so a card that shows only the text turns a decision into a coin flip. Every
 * candidate therefore carries its evidence on the face of the row: real search volume from this
 * run's own keyword set, the funnel stage, the length against the channel's budget, and whether it
 * passed the headline framework's pre-publication checklist. That is what the operator is actually
 * choosing between.
 *
 * Three exits, always available: pick from the list, ask for ten more, or write your own. The last
 * one is not a fallback for failure — an operator who already knows the topic should not have to
 * wait for suggestions to get past this, which is why the field is present even while they load.
 */
export function HeadlineChoiceCard({ message }: { message: PipelineMessage }) {
  const chooseHeadlines = usePipelineStore((s) => s.chooseHeadlines);
  const writeOwnHeadline = usePipelineStore((s) => s.writeOwnHeadline);
  const rerollHeadlines = usePipelineStore((s) => s.rerollHeadlines);
  const retryHeadlines = usePipelineStore((s) => s.retryHeadlines);

  const [picked, setPicked] = useState<string[]>([]);
  const [own, setOwn] = useState("");
  const [showOwn, setShowOwn] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const state = message.headlines;
  const field = message.field;
  if (!state || !field) return null;

  const superseded = Boolean(message.superseded);
  const candidates = state.candidates ?? [];
  const multi = Boolean(state.multi);
  const busy = state.status === "chosen" || superseded;

  // Not memoised on purpose: this sits below the `!state` early return, so a `useMemo` here would
  // be a conditional hook. It filters at most a couple of dozen rows.
  const chosen = candidates.filter((c) => (state.chosenIds ?? []).includes(c.id));

  function toggle(id: string) {
    if (busy) return;
    setPicked((current) => {
      if (!multi) return [id];
      return current.includes(id) ? current.filter((x) => x !== id) : [...current, id];
    });
  }

  return (
    <div
      className="w-full min-w-0 max-w-[42rem] rounded-2xl border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5"
      style={superseded ? { opacity: 0.6 } : undefined}
    >
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="text-[0.92rem] font-medium">{field.label}</span>
        {state.serviceAnchor && (
          <span className="text-[0.72rem] text-[var(--fg-faint)]">
            all about <span className="font-medium text-[var(--fg-muted)]">{state.serviceAnchor}</span>
          </span>
        )}
      </div>

      {/* An anchor that fell through to the client's industry is a *category*, not a service — the
          topics will be correspondingly broad. Said out loud, with the fix named, because the
          alternative is an operator staring at ten generic headlines with no idea the run never
          learned what service they were for. This is exactly the state the old build was always
          silently in. */}
      {state.status === "pending" && state.anchorSource === "industry" && (
        <p className="mt-1 text-[0.72rem]" style={{ color: "var(--color-signal-orange)" }}>
          Anchored on the client's industry, not a specific service — so these are broad. Answer the
          Target Service question on an earlier stage to narrow them.
        </p>
      )}

      {/* What the batch is and is not grounded in. An operator reading ten confident headlines is
          entitled to know whether real demand data was behind them. */}
      {state.status === "pending" && (
        <p className="mt-1 text-[0.72rem] text-[var(--fg-faint)]">
          {state.groundedInKeywords
            ? "Built from this run's keyword demand and the headline framework"
            : "Built from the headline framework only — no keyword data for this run, so there are no search volumes"}
          {state.webSearchUsed ? ", with current trends checked" : ""}.
          {state.charBudget ? ` ${state.channel}: ${state.charBudget}.` : ""}
        </p>
      )}

      {/* The first load has nothing on screen to keep, so it gets the full panel: the phases of
          the call plus skeleton rows in the shape of the answer. See `HeadlineSearchProgress` for
          why a bare spinner is the wrong choice for a wait this long.

          `serviceAnchor` and `webSearch` are still undefined here — they arrive with the response —
          so the panel degrades to the generic wording rather than inventing either. */}
      {state.status === "loading" && (
        <HeadlineSearchProgress
          subject={state.subject}
          serviceAnchor={state.serviceAnchor}
          webSearch={state.webSearchUsed}
          grounded={state.groundedInKeywords}
          // The floor the request asks for (`DEFAULT_COUNT` on the backend). The real figure only
          // exists once the response lands and the anchor filter has run, so this is stated as a
          // minimum rather than a promise.
          count={10}
          attempt={state.attempt}
          onRetry={() => void retryHeadlines(message.id)}
        />
      )}

      {state.status === "error" && (
        <div className="mt-2 rounded-xl border border-[var(--border)] bg-[var(--bg-sunken)] px-3 py-2.5">
          <p className="text-[0.78rem] text-[var(--fg-muted)]">
            Couldn't fetch suggestions{state.error ? ` — ${state.error}` : "."} You can type the topic
            yourself below, or try again.
          </p>
          {/* A real button, not an underlined link. This is the primary way out of a failed gate —
              the intake is blocked on it — and it was previously the least prominent thing on the
              card. */}
          <motion.button
            type="button"
            onClick={() => void retryHeadlines(message.id)}
            whileHover={{ backgroundColor: "var(--hover)" }}
            whileTap={{ scale: 0.97 }}
            className="mt-2 min-h-10 cursor-pointer rounded-full border border-[var(--border-strong)] px-3.5 py-1.5
              text-[0.8rem] font-medium sm:min-h-0"
          >
            Try again
          </motion.button>
        </div>
      )}

      {/* The chosen answer, once settled — the card stays in the transcript as the record of what
          was picked and out of what. */}
      {state.status === "chosen" && (
        <div className="mt-2 rounded-xl border border-[var(--border)] bg-[var(--bg-sunken)] px-3 py-2.5">
          <div className="text-[0.72rem] text-[var(--fg-faint)]">
            {state.ownHeadline ? "Your own topic" : `Chosen from ${candidates.length} suggestions`}
          </div>
          {state.ownHeadline ? (
            <p className="mt-1 text-[0.84rem]">{state.ownHeadline}</p>
          ) : (
            <ol className="mt-1 space-y-1">
              {chosen.map((c) => (
                <li key={c.id} className="text-[0.84rem]">
                  {c.headline}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      {superseded && <p className="mt-2 text-[0.78rem] italic text-[var(--fg-faint)]">asked again below</p>}

      {state.status === "pending" && !superseded && (
        <>
          {multi && (
            <p className="mt-2 text-[0.75rem] text-[var(--fg-muted)]">
              Pick as many as you want{state.suggestedSelection ? ` — around ${state.suggestedSelection} works well` : ""}.
              Each one gets built.
            </p>
          )}

          {/* A re-roll keeps the current batch on screen and choosable, so it needs its own quiet
              indicator — dimming alone reads as the list having been disabled, not as a second one
              being written. */}
          {state.reloading && (
            <div className="mt-2 flex items-center gap-2 text-[0.75rem] text-[var(--fg-muted)]" role="status">
              <span className="flex gap-1" aria-hidden>
                {[0, 1, 2].map((i) => (
                  <motion.span
                    key={i}
                    className="h-1 w-1 rounded-full bg-[var(--color-electric-blue)]"
                    animate={{ opacity: [0.25, 1, 0.25] }}
                    transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15, ease: "easeInOut" }}
                  />
                ))}
              </span>
              Writing a different set — these stay selectable until it arrives.
            </div>
          )}

          <ul className="mt-2 space-y-1.5" style={state.reloading ? { opacity: 0.55 } : undefined}>
            {candidates.map((candidate) => (
              <CandidateRow
                key={candidate.id}
                candidate={candidate}
                selected={picked.includes(candidate.id)}
                multi={multi}
                expanded={expanded === candidate.id}
                onToggle={() => toggle(candidate.id)}
                onExpand={() => setExpanded(expanded === candidate.id ? null : candidate.id)}
              />
            ))}
          </ul>

          {/* Said plainly rather than hidden: a short batch is the anchor filter working, and an
              operator who sees eight where ten were promised should know why. */}
          {Boolean(state.rejectedCount) && (
            <p className="mt-1.5 text-[0.7rem] text-[var(--fg-faint)]">
              {state.rejectedCount} more were dropped for not being about {state.serviceAnchor}.
            </p>
          )}

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <motion.button
              type="button"
              disabled={!picked.length}
              onClick={() => void chooseHeadlines(message.id, picked)}
              whileTap={picked.length ? { scale: 0.97 } : undefined}
              className="min-h-10 cursor-pointer rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold text-white
                disabled:cursor-not-allowed disabled:opacity-40 sm:min-h-0"
              style={{ backgroundColor: "var(--color-electric-blue)" }}
            >
              {picked.length > 1 ? `Use these ${picked.length}` : "Use this one"}
            </motion.button>

            <motion.button
              type="button"
              disabled={state.reloading}
              onClick={() => void rerollHeadlines(message.id)}
              whileTap={{ scale: 0.97 }}
              className="min-h-10 cursor-pointer rounded-full border border-[var(--border-strong)] px-3.5 py-1.5
                text-[0.8rem] font-medium disabled:opacity-40 sm:min-h-0"
            >
              {state.reloading ? "Finding more…" : "Show me 10 more"}
            </motion.button>

            {!showOwn && (
              <button
                type="button"
                onClick={() => setShowOwn(true)}
                className="cursor-pointer py-1 text-[0.75rem] underline underline-offset-2 text-[var(--fg-muted)]"
              >
                Write my own
              </button>
            )}
          </div>
        </>
      )}

      {/* Available during loading and after a failure too — an operator who already knows the topic
          should not have to wait on a suggestion service to get past this question. */}
      {(showOwn || state.status === "error" || state.status === "loading") && !busy && (
        <div className="mt-3 border-t border-[var(--border)] pt-2.5">
          <label className="text-[0.75rem] text-[var(--fg-muted)]">Or use your own:</label>
          <FieldHint field={field} compact parts="example" />
          <div className="mt-1.5 flex flex-wrap gap-2">
            <input
              type="text"
              value={own}
              onChange={(e) => setOwn(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && own.trim()) void writeOwnHeadline(message.id, own);
              }}
              placeholder={field.placeholder ?? "Type the topic you want"}
              className="min-w-0 flex-1 rounded-xl border border-[var(--border)] bg-[var(--bg-sunken)] px-3 py-2
                text-[0.82rem] outline-none focus:border-[var(--border-strong)]"
            />
            <motion.button
              type="button"
              disabled={!own.trim()}
              onClick={() => void writeOwnHeadline(message.id, own)}
              whileTap={own.trim() ? { scale: 0.97 } : undefined}
              className="min-h-10 cursor-pointer rounded-full border border-[var(--border-strong)] px-3.5 py-1.5
                text-[0.8rem] font-medium disabled:cursor-not-allowed disabled:opacity-40 sm:min-h-0"
            >
              Use this
            </motion.button>
          </div>
        </div>
      )}
    </div>
  );
}

/** One suggestion, with the evidence that makes it comparable to the nine next to it. */
function CandidateRow({
  candidate,
  selected,
  multi,
  expanded,
  onToggle,
  onExpand,
}: {
  candidate: HeadlineCandidate;
  selected: boolean;
  multi: boolean;
  expanded: boolean;
  onToggle: () => void;
  onExpand: () => void;
}) {
  const format = typeof candidate.extras?.format === "string" ? candidate.extras.format : null;

  return (
    <li
      className="rounded-xl border px-3 py-2 transition-colors"
      style={{
        borderColor: selected ? "var(--color-electric-blue)" : "var(--border)",
        backgroundColor: selected ? "color-mix(in srgb, var(--color-electric-blue) 8%, transparent)" : "transparent",
      }}
    >
      <button type="button" onClick={onToggle} className="flex w-full cursor-pointer items-start gap-2.5 text-left">
        <span
          aria-hidden
          className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center border text-[0.6rem] text-white"
          style={{
            borderRadius: multi ? "0.25rem" : "9999px",
            borderColor: selected ? "var(--color-electric-blue)" : "var(--border-strong)",
            backgroundColor: selected ? "var(--color-electric-blue)" : "transparent",
          }}
        >
          {selected ? "✓" : ""}
        </span>

        <span className="min-w-0 flex-1">
          <span className="block text-[0.84rem] leading-snug">{candidate.headline}</span>

          <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[0.68rem] text-[var(--fg-faint)]">
            {format && <Chip>{format}</Chip>}
            {/* Volume is the one number here that was measured rather than asserted, so it leads.
                Its absence is stated, not left blank — "no demand data" is information. */}
            {candidate.search_volume !== null ? (
              <Chip>{candidate.search_volume}/mo</Chip>
            ) : (
              <Chip muted>no demand data</Chip>
            )}
            {candidate.funnel && <Chip>{candidate.funnel}</Chip>}
            <Chip muted={!candidate.channel_limit_ok}>
              {candidate.char_count} chars{candidate.channel_limit_ok ? "" : " — over budget"}
            </Chip>
            {!candidate.checklist_pass && <Chip muted>checklist: needs work</Chip>}
          </span>
        </span>
      </button>

      <button
        type="button"
        onClick={onExpand}
        className="mt-1 cursor-pointer py-0.5 pl-6 text-[0.68rem] underline underline-offset-2 text-[var(--fg-muted)]"
      >
        {expanded ? "Less" : "Why this one"}
      </button>

      {expanded && (
        <dl className="mt-1 space-y-1 pl-6 text-[0.7rem] leading-relaxed text-[var(--fg-muted)]">
          {candidate.why_it_works && <Detail label="Why it works">{candidate.why_it_works}</Detail>}
          {candidate.specificity && <Detail label="Specificity">{candidate.specificity}</Detail>}
          {candidate.primary_keyword && <Detail label="Keyword">{candidate.primary_keyword}</Detail>}
          {candidate.framework_formula && <Detail label="Formula">{candidate.framework_formula}</Detail>}
          {candidate.curiosity_elements.length > 0 && (
            <Detail label="Curiosity">{candidate.curiosity_elements.join(", ").toLowerCase()}</Detail>
          )}
          {/* Only shown when a search actually found something. A null trend is left off rather
              than rendered as "none", because an empty row reads as a shortcoming when it is in
              fact the honest answer. */}
          {candidate.trend_evidence && <Detail label="Trend">{candidate.trend_evidence}</Detail>}
          {!candidate.checklist_pass && candidate.checklist_notes && (
            <Detail label="Checklist">{candidate.checklist_notes}</Detail>
          )}
          {!candidate.grounded && (
            <Detail label="Note">Not in this run's keyword set, so it carries no demand evidence.</Detail>
          )}
        </dl>
      )}
    </li>
  );
}

function Chip({ children, muted }: { children: React.ReactNode; muted?: boolean }) {
  return (
    <span
      className="rounded-full border px-1.5 py-px"
      style={{
        borderColor: "var(--border)",
        color: muted ? "var(--fg-faint)" : "var(--fg-muted)",
      }}
    >
      {children}
    </span>
  );
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-1.5">
      <dt className="shrink-0 font-medium text-[var(--fg-faint)]">{label}:</dt>
      <dd className="min-w-0">{children}</dd>
    </div>
  );
}
