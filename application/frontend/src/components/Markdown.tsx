import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** A generated table is the one element in a stage's output whose width this UI does not control —
 * a competitor matrix can be nine columns wide, and the transcript column can be 320px. Squeezing
 * it to fit makes it unreadable, so it gets its own horizontal scroller and keeps its real width
 * (see `.md-scroll` in `index.css`). The pane it sits in never widens. */
function ScrollableTable({ children, ...props }: React.ComponentPropsWithoutRef<"table">) {
  return (
    <div className="md-scroll my-2">
      <table {...props}>{children}</table>
    </div>
  );
}

export function Markdown({ text }: { text: string }) {
  return (
    <div
      className="
        prose-block text-[0.9rem] leading-relaxed @[30rem]:text-[0.95rem]
        [&_h2]:text-[1.02rem] [&_h2]:font-semibold [&_h2]:mt-0 [&_h2]:mb-2 @[30rem]:[&_h2]:text-[1.05rem]
        [&_h3]:text-[0.92rem] [&_h3]:font-semibold [&_h3]:mt-4 [&_h3]:mb-1.5 [&_h3]:opacity-90
        [&_h2]:text-balance [&_h3]:text-balance
        [&_p]:my-1.5 [&_ul]:my-1.5 [&_ol]:my-1.5 [&_li]:my-0.5
        [&_ul]:list-disc [&_ol]:list-decimal [&_ul]:pl-4.5 [&_ol]:pl-4.5 @[30rem]:[&_ul]:pl-5 @[30rem]:[&_ol]:pl-5
        [&_strong]:font-semibold
        [&_blockquote]:border-l-2 [&_blockquote]:pl-3 [&_blockquote]:italic
        [&_blockquote]:opacity-80 [&_blockquote]:my-2
        [&_code]:font-mono [&_code]:text-[0.85em] [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded
        [&_code]:bg-[var(--bg-sunken)]
        [&_table]:w-full [&_table]:border-collapse [&_table]:text-[0.88em]
        [&_th]:text-left [&_th]:font-semibold [&_th]:py-1 [&_th]:pr-3
        [&_td]:py-1 [&_td]:pr-3 [&_th]:border-b [&_td]:border-b
        [&_th]:border-[var(--border)] [&_td]:border-[var(--border)]
        [&_hr]:my-3 [&_hr]:border-[var(--border)]
        [&_img]:max-w-full [&_img]:h-auto
      "
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ table: ScrollableTable }}>
        {text}
      </ReactMarkdown>
    </div>
  );
}
