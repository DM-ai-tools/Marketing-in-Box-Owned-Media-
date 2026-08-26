import { motion } from "framer-motion";
import { TypingIndicator } from "../components/TypingIndicator";
import { ASSET_BY_ID } from "../data/assetCatalog";
import { PREPASS_BY_MAIN_ASSET } from "./pipelineData";
import { usePipelineStore } from "./pipelineStore";
import type { PipelineMessage } from "./pipelineStore";
import type { CompetitorRow } from "./pipelineApi";

/** Colour-codes how firmly each competitor's offering was confirmed on their own page. Low
 * confidence is the whole reason the field exists, so it is shown, never hidden or averaged away. */
const CONFIDENCE_STYLE: Record<string, { bg: string; fg: string }> = {
  Verified: { bg: "var(--color-signal-green)", fg: "var(--signal-green-fg)" },
  "Partially verified": { bg: "var(--color-signal-orange)", fg: "var(--signal-orange-fg)" },
  Unverified: { bg: "var(--border-strong)", fg: "var(--fg)" },
};

function ConfidenceBadge({ value }: { value: string }) {
  const style = CONFIDENCE_STYLE[value] ?? CONFIDENCE_STYLE.Unverified;
  return (
    <span
      className="shrink-0 rounded-full px-2 py-0.5 text-[0.62rem] font-semibold"
      style={{ backgroundColor: style.bg, color: style.fg }}
    >
      {value}
    </span>
  );
}

function CompetitorRowItem({ competitor }: { competitor: CompetitorRow }) {
  const host = competitor.page_url?.replace(/^https?:\/\//, "");
  return (
    <li className="border-t border-[var(--border)] px-2.5 py-2.5 first:border-t-0 @[30rem]:px-3">
      <div className="flex items-start gap-2">
        <span className="mt-0.5 w-5 shrink-0 text-[0.72rem] font-semibold text-[var(--fg-faint)]">
          {competitor.rank}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-[0.86rem] font-semibold">{competitor.name}</span>
            <span className="text-[0.72rem] text-[var(--fg-faint)]">{competitor.domain}</span>
            <ConfidenceBadge value={competitor.verification_confidence} />
            {/* The stage's own classifier — lead-magnet type, blog content focus, podcast topical
                focus. Its whole value is being scannable down the column, so it gets a pill rather
                than a line of prose. */}
            {competitor.category && (
              <span
                className="shrink-0 rounded-full border px-2 py-0.5 text-[0.66rem] font-medium"
                style={{ borderColor: "var(--border-strong)", color: "var(--fg-muted)" }}
              >
                {competitor.category}
              </span>
            )}
            {/* Given its own pill, and pushed to the end of the row, because on the Offers stage the
                price is the column the operator scans down — a value ladder is priced against it.
                Rendered verbatim as published ("From $1,500/mo"), never reformatted. */}
            {competitor.starting_price && (
              <span
                className="shrink-0 rounded-full px-2 py-0.5 text-[0.72rem] font-semibold @[34rem]:ml-auto"
                style={{
                  backgroundColor: "color-mix(in srgb, var(--color-signal-green) 16%, transparent)",
                  color: "var(--color-signal-green)",
                }}
                title="Starting price as published on the competitor's own page"
              >
                {competitor.starting_price}
              </span>
            )}
          </div>

          {competitor.page_url && (
            <a
              href={competitor.page_url}
              target="_blank"
              rel="noreferrer noopener"
              className="mt-0.5 block truncate text-[0.74rem] underline underline-offset-2"
              style={{ color: "var(--color-electric-blue)" }}
              title={competitor.page_url}
            >
              {host}
            </a>
          )}

          {competitor.offering_summary && (
            <p className="mt-1 text-[0.78rem] leading-relaxed text-[var(--fg-muted)]">
              {competitor.offering_summary}
            </p>
          )}
        </div>
      </div>
    </li>
  );
}

/** The gated competitor sub-step's card: a reviewable listing of who was found, where, how firmly
 * it was verified, and what their offering is — plus the notes explaining any gap below the
 * requested 10. The model's raw JSON is parsed server-side and deliberately never rendered here. */
export function CompetitorCard({ message }: { message: PipelineMessage }) {
  const saveCompetitorStep = usePipelineStore((s) => s.saveCompetitorStep);
  const retryCompetitorStep = usePipelineStore((s) => s.retryCompetitorStep);
  const result = message.competitor;
  const saving = message.savePhase === "saving";
  const saved = message.savePhase === "saved";
  // This card serves every competitor stage, not only CRO's: the gating one that runs before a
  // stage, and the mid-intake ones that answer a field (Pillar Page's, run on the topic the
  // operator gave). So the label comes from the catalog and the button says what approving does
  // *here* — continuing the stage that was interrupted, or resuming the intake it belongs to.
  const label = (message.assetId && ASSET_BY_ID[message.assetId]?.label) || "Competitor Analysis";
  // Named from the stage this sub-step feeds, not hardcoded: the same card now gates CRO, Offers,
  // and Pillar Page's mid-intake research.
  const mainAsset = Object.entries(PREPASS_BY_MAIN_ASSET).find(([, c]) => c.assetId === message.assetId)?.[0];
  const mainLabel = (mainAsset && ASSET_BY_ID[mainAsset]?.label) || "the next stage";
  const continuation = message.competitorFillsFieldId ? "Use This & Continue" : `Save & Continue to ${mainLabel}`;

  const header = (
    <div className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1">
      <span aria-hidden>🔎</span>
      <span className="text-[0.85rem] font-semibold">{label}</span>
      <span className="rounded-full border border-[var(--border-strong)] px-1.5 py-[1px] text-[0.62rem] font-semibold text-[var(--fg-muted)]">
        Sub-step
      </span>
    </div>
  );

  if (message.competitorError) {
    return (
      <div
        className="w-full min-w-0 max-w-[47rem] rounded-2xl border-2 bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5"
        style={{ borderColor: "var(--color-signal-orange)" }}
      >
        {header}
        <p className="text-[0.85rem]" style={{ color: "var(--color-signal-orange)" }}>
          Competitor analysis failed: {message.competitorError}
        </p>
        <motion.button
          type="button"
          onClick={() => void retryCompetitorStep(message.id)}
          whileTap={{ scale: 0.97 }}
          className="mt-3 min-h-10 cursor-pointer rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold text-white sm:min-h-0"
          style={{ backgroundColor: "var(--color-electric-blue)" }}
        >
          Retry Analysis
        </motion.button>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="w-full min-w-0 max-w-[47rem] rounded-2xl border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5">
        {header}
        <p className="mb-2 text-[0.8rem] text-[var(--fg-muted)]">
          Researching competitors and verifying each one's CRO offering on their own page…
        </p>
        <TypingIndicator />
      </div>
    );
  }

  const shortfall = result.requested_count - result.returned_count;

  return (
    <div className="w-full min-w-0 max-w-[47rem] rounded-2xl border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5">
      {header}

      <p className="mb-2.5 text-[0.78rem] text-[var(--fg-muted)]">
        Benchmarked against <span className="break-all font-medium text-[var(--fg)]">{result.target_url}</span>
        {result.location ? ` in ${result.location}` : ""} —{" "}
        <span className="font-medium text-[var(--fg)]">
          {result.returned_count} of {result.requested_count}
        </span>{" "}
        competitors found.
      </p>

      {result.returned_count === 0 ? (
        <p className="rounded-xl border border-[var(--border)] px-3 py-3 text-[0.82rem] text-[var(--fg-muted)]">
          No competitors met the qualifying criteria for this run.
        </p>
      ) : (
        <ul className="overflow-hidden rounded-xl border border-[var(--border)]">
          {result.competitors.map((c) => (
            <CompetitorRowItem key={c.domain} competitor={c} />
          ))}
        </ul>
      )}

      {result.notes && (
        <div className="mt-3 rounded-xl border border-[var(--border)] bg-[var(--bg-sunken)] px-3 py-2.5">
          <div className="mb-1 text-[0.68rem] font-semibold uppercase tracking-wide text-[var(--fg-faint)]">
            Notes{shortfall > 0 ? ` — ${shortfall} short of ${result.requested_count}` : ""}
          </div>
          <p className="text-[0.78rem] leading-relaxed text-[var(--fg-muted)]">{result.notes}</p>
        </div>
      )}

      <div className="mt-3 border-t border-[var(--border)] pt-3">
        {saved ? (
          <span
            className="flex w-fit items-center gap-1.5 rounded-full px-3 py-1 text-[0.78rem] font-semibold text-white"
            style={{ backgroundColor: "var(--color-signal-green)" }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <path d="M5 12l5 5L20 7" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {message.competitorFillsFieldId ? "Saved — continuing this stage" : `Saved — continuing to ${mainLabel}`}
          </span>
        ) : (
          <>
            {message.savePhase === "error" && (
              <p className="mb-2 text-[0.78rem]" style={{ color: "var(--color-signal-orange)" }}>
                Save failed: {message.saveError}
              </p>
            )}
            <div className="flex flex-wrap items-center gap-2">
              <motion.button
                type="button"
                disabled={saving}
                onClick={() => void saveCompetitorStep(message.id)}
                whileTap={{ scale: 0.97 }}
                className="min-h-10 cursor-pointer rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60 sm:min-h-0"
                style={{ backgroundColor: "var(--color-electric-blue)" }}
              >
                {saving ? "Saving…" : message.savePhase === "error" ? "Retry Save" : continuation}
              </motion.button>
              <motion.button
                type="button"
                disabled={saving}
                onClick={() => void retryCompetitorStep(message.id)}
                whileTap={{ scale: 0.97 }}
                className="min-h-10 cursor-pointer rounded-full border-2 px-3.5 py-1.5 text-[0.8rem] font-semibold disabled:cursor-not-allowed disabled:opacity-60 sm:min-h-0"
                style={{ borderColor: "var(--color-signal-orange)", color: "var(--color-signal-orange)" }}
              >
                Re-run Analysis
              </motion.button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
