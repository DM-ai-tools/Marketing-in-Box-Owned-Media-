import { useEffect } from "react";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { useChatSessionsStore } from "../store/chatSessionsStore";
import { useUiStore } from "../store/uiStore";
import { usePipelineStore } from "./pipelineStore";

/** The warning in front of deleting a chat from the history list.
 *
 * Mounted at the app root, not in the sidebar that raises it: below `xl` that sidebar is a drawer
 * animating on `transform`, which makes it the containing block for any `position: fixed`
 * descendant — so the dialog would be laid out inside an 85vw panel instead of over the app. The
 * sidebar sets `pendingChatDelete`; this asks about it.
 *
 * It is a modal for the same reason `ClearChatButton`'s is: a chat is an entire engagement's
 * transcript, the trash icon sits one mis-aimed tap from the row that opens that chat, and nothing
 * in this app has an undo.
 */
export function ChatDeleteDialog() {
  const target = useUiStore((s) => s.pendingChatDelete);
  const cancelDeleteChat = useUiStore((s) => s.cancelDeleteChat);
  const sessions = useChatSessionsStore((s) => s.sessions);
  const remove = useChatSessionsStore((s) => s.remove);
  const activeSessionId = usePipelineStore((s) => s.sessionId);
  const startNewChat = usePipelineStore((s) => s.startNewChat);

  // The chat can leave the list underneath the question — deleted from another tab, or dropped by a
  // refresh. Asking about a row that is no longer there would delete nothing and report nothing.
  useEffect(() => {
    if (target && !sessions.some((s) => s.id === target.id)) cancelDeleteChat();
  }, [target, sessions, cancelDeleteChat]);

  return (
    <ConfirmDialog
      open={target !== null}
      title="Delete this chat?"
      message={`“${target?.title ?? ""}” and everything in it — the transcript, the answers given and every draft that was never approved — is deleted for good.`}
      detail="Assets you already approved are not deleted: they stay in the Context Store against their run, and a later chat can still inherit them."
      confirmLabel="Delete chat"
      cancelLabel="Keep it"
      footnote="This cannot be undone."
      onCancel={cancelDeleteChat}
      onConfirm={() => {
        cancelDeleteChat();
        if (!target) return;
        // Clear the pane first, discarding the pending autosave: flushing it would race the DELETE
        // and either resurrect the row or 404 against it.
        if (target.id === activeSessionId) startNewChat({ discardUnsaved: true });
        void remove(target.id);
      }}
    />
  );
}
