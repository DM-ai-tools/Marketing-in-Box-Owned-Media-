import { Component, type ErrorInfo, type ReactNode } from "react";

/** The last line of defence between a render throw and a blank page.
 *
 * React unmounts the *entire* tree when a render throws and nothing catches it, so without this a
 * single bad message in a reopened chat takes the whole application with it — nav, sidebar and all
 * — and leaves a plain white screen carrying no clue about what failed. That is the worst possible
 * failure for an operator to report and the worst to diagnose: the one place the stack was written
 * is a console nobody had open at the time.
 *
 * So the boundary shows the error rather than hiding it. The message and the component stack are on
 * screen and copyable, because the operator hitting this is the one person who can say what they
 * had just done — and a bug report with a stack in it is worth more than ten without.
 *
 * `onReset` is what makes it more than a nicer error page. A crash while *rendering a chat* is
 * survivable: the chat is a row in the database, not lost work, and dropping back to the welcome
 * screen puts the operator somewhere they can open a different one. Reloading the page would only
 * reopen the same chat and crash again.
 */
interface Props {
  children: ReactNode;
  /** Called by "Back to safety". Should leave the app on a screen that does not re-render whatever
   * threw — in practice, clearing the loaded chat. */
  onReset?: () => void;
}

interface State {
  error: Error | null;
  componentStack: string | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, componentStack: null };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Still logged: the console keeps the source-mapped stack, which is more precise than the
    // component stack rendered below.
    console.error("Render crashed", error, info.componentStack);
    this.setState({ componentStack: info.componentStack ?? null });
  }

  private reset = () => {
    this.setState({ error: null, componentStack: null });
    this.props.onReset?.();
  };

  render() {
    const { error, componentStack } = this.state;
    if (!error) return this.props.children;

    const report = `${error.name}: ${error.message}\n\n${error.stack ?? ""}\n\nComponent stack:${componentStack ?? " (unavailable)"}`;

    return (
      <div className="flex h-full min-h-screen flex-col items-center justify-center gap-4 px-5 py-10 text-center">
        <div className="w-full max-w-[42rem] rounded-2xl border border-[var(--border)] bg-[var(--bg-raised)] px-5 py-5 text-left">
          <h1 className="text-[1.05rem] font-semibold">Something in this view failed to render</h1>
          <p className="mt-1.5 text-[0.85rem] leading-relaxed text-[var(--fg-muted)]">
            Nothing has been lost — every chat, run and approved asset is stored on the server, not in
            this page. Go back to safety to open a different chat.
          </p>

          <pre className="mt-3 max-h-[16rem] overflow-auto rounded-lg border border-[var(--border)] bg-[var(--bg-sunken)] p-3 text-[0.72rem] leading-relaxed whitespace-pre-wrap">
            {report}
          </pre>

          <div className="mt-3.5 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={this.reset}
              className="min-h-10 cursor-pointer rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold text-white sm:min-h-0"
              style={{ backgroundColor: "var(--color-electric-blue)" }}
            >
              Back to safety
            </button>
            <button
              type="button"
              onClick={() => void navigator.clipboard?.writeText(report)}
              className="min-h-10 cursor-pointer rounded-full border border-[var(--border-strong)] px-3.5 py-1.5 text-[0.8rem] font-medium sm:min-h-0"
            >
              Copy error
            </button>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="min-h-10 cursor-pointer rounded-full border border-[var(--border-strong)] px-3.5 py-1.5 text-[0.8rem] font-medium sm:min-h-0"
            >
              Reload
            </button>
          </div>
        </div>
      </div>
    );
  }
}
