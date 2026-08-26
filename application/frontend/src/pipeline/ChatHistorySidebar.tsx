import { useEffect } from "react";
import { motion } from "framer-motion";
import { useChatSessionsStore } from "../store/chatSessionsStore";
import { useUiStore } from "../store/uiStore";
import { usePipelineStore } from "./pipelineStore";

/** "12m ago" while a chat is recent enough for that to mean something, else `null` — past a week
 * the absolute stamp rendered beside it (see `absoluteTime`) is the more useful of the two, and
 * showing both would just print the same date twice. */
function relativeTime(iso: string): string | null {
  const then = new Date(iso).getTime();
  const diffMs = Date.now() - then;
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return null;
}

/** Compact absolute stamp: day + month + clock time for this year ("17 Aug, 3:47 pm"), day +
 * month + year for anything older ("17 Aug 2025"). Locale-formatted rather than hand-built so a
 * non-en-US strategist gets their own date order and 24h clock. */
function absoluteTime(iso: string): string {
  const d = new Date(iso);
  const options: Intl.DateTimeFormatOptions =
    d.getFullYear() === new Date().getFullYear()
      ? { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }
      : { day: "numeric", month: "short", year: "numeric" };
  return d.toLocaleString(undefined, options);
}

function PlusIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function ChatBubbleIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" className="shrink-0">
      <path
        d="M4 5h16v11H8l-4 4V5z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
      <path
        d="M5 7h14M9 7V5h6v2M7 7l1 13h8l1-13"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ChatHistorySidebar() {
  const sessions = useChatSessionsStore((s) => s.sessions);
  const loading = useChatSessionsStore((s) => s.loading);
  const loaded = useChatSessionsStore((s) => s.loaded);
  const error = useChatSessionsStore((s) => s.error);
  const refresh = useChatSessionsStore((s) => s.refresh);
  const remove = useChatSessionsStore((s) => s.remove);

  const activeSessionId = usePipelineStore((s) => s.sessionId);
  const isLoadingSession = usePipelineStore((s) => s.isLoadingSession);
  const loadingSessionId = usePipelineStore((s) => s.loadingSessionId);
  const startNewChat = usePipelineStore((s) => s.startNewChat);
  const loadSession = usePipelineStore((s) => s.loadSession);

  // Below `xl` this list is a drawer over the transcript, so every action that changes what the
  // transcript is showing has to get out of the way to reveal it. Above `xl` the sidebar is docked
  // and `sidebarOpen` is already false, making these calls no-ops rather than special cases.
  const closeSidebar = useUiStore((s) => s.closeSidebar);
  const setMobilePane = useUiStore((s) => s.setMobilePane);
  const openChat = () => {
    closeSidebar();
    setMobilePane("chat");
  };

  useEffect(() => {
    if (!loaded) void refresh();
  }, [loaded, refresh]);

  return (
    <div className="flex h-full w-[17rem] max-w-[85vw] shrink-0 flex-col border-r border-[var(--border)] bg-[var(--bg-sunken)] px-3 pb-[max(1rem,env(safe-area-inset-bottom))] pt-4 sm:w-72 xl:w-64 2xl:w-72">
      <div className="mb-4 flex items-center gap-2 px-1">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)] text-[var(--accent-fg)] text-[0.8rem] font-bold">
          M
        </div>
        <span className="min-w-0 flex-1 truncate text-[0.9rem] font-semibold">Marketing-in-a-Box</span>
        {/* Tapping the scrim closes the drawer too, but a scrim is not a discoverable control —
            and on a phone the sidebar covers nearly the whole screen, so there is little scrim to
            aim at. Not rendered once the sidebar is docked and has nothing to close. */}
        <button
          type="button"
          onClick={closeSidebar}
          aria-label="Close chat history"
          className="-mr-1 flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-lg text-[var(--fg-faint)] hover:bg-[var(--hover)] hover:text-[var(--fg)] xl:hidden"
        >
          <CloseIcon />
        </button>
      </div>

      <motion.button
        type="button"
        onClick={() => {
          startNewChat();
          openChat();
        }}
        whileHover={{ backgroundColor: "var(--hover)" }}
        whileTap={{ scale: 0.98 }}
        className="mb-4 flex min-h-11 cursor-pointer items-center gap-2 rounded-xl border border-[var(--border-strong)] px-3 py-2 text-[0.85rem] font-medium sm:min-h-0"
      >
        <PlusIcon />
        New chat
      </motion.button>

      <div className="mb-2 px-1 text-[0.68rem] font-semibold uppercase tracking-wide text-[var(--fg-faint)]">
        Chat History
      </div>

      {/* An error while the list is non-empty (a failed open, a failed autosave) has nowhere else
          to appear — the full error block below only renders when there is nothing to show. */}
      {error && sessions.length > 0 && (
        <div className="mb-2 rounded-lg border px-2 py-1.5" style={{ borderColor: "var(--color-signal-orange)" }}>
          <p className="break-words text-[0.7rem] leading-relaxed" style={{ color: "var(--color-signal-orange)" }}>
            {error}
          </p>
          <button
            type="button"
            onClick={() => void refresh()}
            className="mt-1 cursor-pointer text-[0.68rem] font-medium underline underline-offset-2 text-[var(--fg-muted)]"
          >
            Retry
          </button>
        </div>
      )}

      <div className="pane-scroll min-h-0 flex-1 overflow-y-auto">
        {loading && sessions.length === 0 ? (
          <p className="px-1 text-[0.78rem] text-[var(--fg-faint)]">Loading…</p>
        ) : error && sessions.length === 0 ? (
          <div className="px-1">
            <p className="text-[0.78rem]" style={{ color: "var(--color-signal-orange)" }}>
              Couldn't load chat history.
            </p>
            <p className="mt-1 break-words text-[0.68rem] leading-relaxed text-[var(--fg-faint)]">{error}</p>
            <button
              type="button"
              onClick={() => void refresh()}
              className="mt-2 cursor-pointer rounded-lg border border-[var(--border-strong)] px-2 py-1 text-[0.72rem] font-medium"
            >
              Retry
            </button>
          </div>
        ) : sessions.length === 0 ? (
          <p className="px-1 text-[0.78rem] text-[var(--fg-faint)]">
            No previous chats yet — start one above and it'll show up here.
          </p>
        ) : (
          <ul className="space-y-1">
            {sessions.map((s) => {
              const active = s.id === activeSessionId;
              const relative = relativeTime(s.updated_at);
              const absolute = absoluteTime(s.updated_at);
              return (
                <li key={s.id} className="group relative">
                  <button
                    type="button"
                    disabled={isLoadingSession}
                    onClick={() => {
                      void loadSession(s.id);
                      openChat();
                    }}
                    className={`flex w-full cursor-pointer items-start gap-2 rounded-lg px-2 py-2 pr-9 text-left transition-colors disabled:cursor-wait ${
                      active ? "bg-[var(--active)]" : "hover:bg-[var(--hover)]"
                    }`}
                  >
                    <span className="mt-0.5 text-[var(--fg-muted)]">
                      <ChatBubbleIcon />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[0.82rem] font-medium">
                        {s.title}
                        {loadingSessionId === s.id && (
                          <span className="ml-1.5 text-[0.68rem] font-normal text-[var(--fg-faint)]">opening…</span>
                        )}
                      </span>
                      {/* Relative for scanning, absolute for precision. `title` carries the full
                          stamps — including when the chat was started, which the row itself has no
                          room for — since a relative label alone can't be checked against notes. */}
                      <span
                        className="block truncate text-[0.68rem] text-[var(--fg-faint)]"
                        title={`Last updated ${new Date(s.updated_at).toLocaleString()}\nStarted ${new Date(
                          s.created_at,
                        ).toLocaleString()}`}
                      >
                        {relative ? `${relative} · ${absolute}` : absolute}
                      </span>
                    </span>
                  </button>
                  <button
                    type="button"
                    aria-label="Delete chat"
                    onClick={(e) => {
                      e.stopPropagation();
                      // Clear the pane first, discarding the pending autosave: flushing it would
                      // race the DELETE and either resurrect the row or 404 against it.
                      if (active) startNewChat({ discardUnsaved: true });
                      void remove(s.id);
                    }}
                    className="hover-reveal absolute right-1 top-1/2 flex h-8 w-8 -translate-y-1/2 cursor-pointer items-center justify-center rounded-md text-[var(--fg-faint)] transition-opacity hover:bg-[var(--border)] hover:text-[var(--fg)]"
                  >
                    <TrashIcon />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
