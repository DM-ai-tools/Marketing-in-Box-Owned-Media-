import { create } from "zustand";

/** Which of the two work surfaces the single-column layout is showing.
 *
 * Below `lg` the transcript and the pipeline diagram cannot both be on screen and still be usable —
 * splitting a 700px-tall phone in half leaves the transcript four lines deep. So on small screens
 * they become two panes of one view and this is which one is front. From `lg` up both are mounted
 * side by side and this value is ignored. */
export type MobilePane = "chat" | "pipeline";

interface UiState {
  /** The chat-history drawer. Only ever open below `lg`; from `lg` up the sidebar is permanent. */
  sidebarOpen: boolean;
  mobilePane: MobilePane;
  /** The API usage monitor. An overlay rather than a third pane: it is something you check, not
   * something you work alongside, and a permanent column would cost the transcript width on every
   * screen to show a number that only matters occasionally. */
  usageOpen: boolean;
  openSidebar: () => void;
  closeSidebar: () => void;
  toggleSidebar: () => void;
  setMobilePane: (pane: MobilePane) => void;
  openUsage: () => void;
  closeUsage: () => void;
}

/**
 * Layout state for the responsive shell, kept out of `pipelineStore` on purpose: nothing here is
 * part of a run, none of it is persisted with a chat, and the components that read it
 * (`TopNav`, `ChatHistorySidebar`) are siblings of the pane they affect rather than children — so a
 * store beats threading props through `App`.
 */
export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: false,
  mobilePane: "chat",
  usageOpen: false,
  openSidebar: () => set({ sidebarOpen: true }),
  closeSidebar: () => set({ sidebarOpen: false }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setMobilePane: (mobilePane) => set({ mobilePane }),
  // Closes the history drawer with it: below `xl` both are overlays, and leaving the drawer open
  // underneath would put the monitor's own scroll container behind a scrim.
  openUsage: () => set({ usageOpen: true, sidebarOpen: false }),
  closeUsage: () => set({ usageOpen: false }),
}));
