import { create } from "zustand";
import { deleteChatSession, listChatSessions } from "../pipeline/pipelineApi";
import type { ChatSessionSummary } from "../pipeline/pipelineApi";

/** Just the history sidebar's list — `pipelineStore` owns the active session's actual content
 * and calls back into `refresh()` here whenever it creates/renames a session, so the sidebar
 * stays in sync without polling. */
interface ChatSessionsState {
  sessions: ChatSessionSummary[];
  loading: boolean;
  loaded: boolean;
  /** Set when the list could not be fetched. Kept distinct from "fetched, and it's empty" so the
   * sidebar never reports a backend outage as "no previous chats yet" — that misread cost real
   * debugging time once already. */
  error: string | null;
  refresh: () => Promise<void>;
  remove: (sessionId: string) => Promise<void>;
}

export const useChatSessionsStore = create<ChatSessionsState>((set, get) => ({
  sessions: [],
  loading: false,
  loaded: false,
  error: null,

  refresh: async () => {
    set({ loading: true });
    try {
      const sessions = await listChatSessions();
      set({ sessions, loading: false, loaded: true, error: null });
    } catch (err) {
      console.error("Failed to load chat history", err);
      set({
        loading: false,
        loaded: true,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  },

  remove: async (sessionId: string) => {
    const prev = get().sessions;
    set({ sessions: prev.filter((s) => s.id !== sessionId) });
    try {
      await deleteChatSession(sessionId);
    } catch (err) {
      console.error("Failed to delete chat session", err);
      set({ sessions: prev, error: err instanceof Error ? err.message : String(err) });
    }
  },
}));
