import { toPreviewDocument } from "../lib/htmlBlocks";

/**
 * A built HTML file at postage-stamp size.
 *
 * `lead_magnet` emits one standalone document per selected concept — ten of them on a full run —
 * and `pillar_page` emits the designed page. Rendered as Markdown those are fenced code blocks,
 * which is the one form in which a *designed* artefact tells its reviewer nothing at all: you
 * cannot tell a good landing page from a bad one by reading its markup.
 *
 * The scale trick is the whole implementation: the iframe is laid out at a real desktop width and
 * then transformed down, because an iframe sized to 88px would trigger the page's own mobile
 * breakpoints and show a stack of full-width blocks rather than the layout being reviewed.
 *
 * `pointer-events-none` and `tabIndex={-1}` because it is an image, not a document — clicks belong
 * to the button wrapping it, which opens the real preview. `sandbox` without `allow-scripts`, so a
 * generated page cannot run anything from inside a thumbnail.
 */

/** Width the frame is laid out at before scaling. A desktop breakpoint, so the thumbnail shows the
 * desktop layout. */
const LAYOUT_WIDTH = 1280;
const LAYOUT_HEIGHT = 900;

export function PreviewThumb({
  html,
  label,
  onOpen,
  width = 104,
}: {
  html: string;
  label: string;
  onOpen?: () => void;
  width?: number;
}) {
  const scale = width / LAYOUT_WIDTH;
  const height = Math.round(width * 0.72);

  const frame = (
    <span
      className="block overflow-hidden rounded-t-[7px] bg-white"
      style={{ width, height }}
      aria-hidden
    >
      <iframe
        title={label}
        srcDoc={toPreviewDocument(html)}
        tabIndex={-1}
        sandbox="allow-same-origin"
        loading="lazy"
        className="pointer-events-none border-0"
        style={{
          width: LAYOUT_WIDTH,
          height: LAYOUT_HEIGHT,
          transform: `scale(${scale})`,
          transformOrigin: "top left",
        }}
      />
    </span>
  );

  const caption = (
    <span className="block truncate px-1 py-[3px] text-[0.6rem] leading-tight text-[var(--fg-muted)]">
      {label}
    </span>
  );

  if (!onOpen) {
    return (
      <span className="shrink-0 overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--bg)]" style={{ width }}>
        {frame}
        {caption}
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={onOpen}
      title={`Open ${label}`}
      className="shrink-0 cursor-pointer overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--bg)] text-left transition-colors hover:border-[var(--border-strong)]"
      style={{ width }}
    >
      {frame}
      {caption}
    </button>
  );
}
