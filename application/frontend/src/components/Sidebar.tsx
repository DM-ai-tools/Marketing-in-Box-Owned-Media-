import { motion } from "framer-motion";
import { ASSET_BY_ID } from "../data/assetCatalog";
import { useChatStore } from "../store/chatStore";

const THEME_LABEL: Record<string, string> = { system: "Auto", light: "Light", dark: "Dark" };

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const showPicker = useChatStore((s) => s.showPicker);
  const completedAssetIds = useChatStore((s) => s.completedAssetIds);
  const theme = useChatStore((s) => s.theme);
  const cycleTheme = useChatStore((s) => s.cycleTheme);

  return (
    <div className="flex h-full w-64 flex-col border-r border-[var(--border)] bg-[var(--bg-sunken)] px-4 py-5">
      <div className="mb-5 flex items-center gap-2 px-1">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--accent)] text-[var(--accent-fg)] text-[0.8rem] font-bold">
          M
        </div>
        <span className="text-[0.92rem] font-semibold">Marketing-in-a-Box</span>
      </div>

      <motion.button
        type="button"
        onClick={() => {
          showPicker();
          onNavigate?.();
        }}
        whileHover={{ backgroundColor: "var(--hover)" }}
        whileTap={{ scale: 0.98 }}
        className="mb-5 flex items-center gap-2 rounded-xl border border-[var(--border-strong)] px-3 py-2 text-[0.85rem] font-medium cursor-pointer"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        New asset
      </motion.button>

      <div className="mb-2 text-[0.68rem] font-semibold uppercase tracking-wide text-[var(--fg-faint)]">
        Session context
      </div>
      <div className="flex-1 overflow-y-auto">
        {completedAssetIds.length === 0 ? (
          <p className="text-[0.78rem] text-[var(--fg-faint)]">
            Nothing generated yet — assets you build here get reused automatically as context for later ones.
          </p>
        ) : (
          <ul className="space-y-1">
            {completedAssetIds.map((id) => (
              <li key={id} className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-[0.82rem]">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" className="shrink-0 text-[var(--fg-muted)]">
                  <path d="M5 12l5 5L20 7" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span className="truncate">{ASSET_BY_ID[id]?.label ?? id}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <motion.button
        type="button"
        onClick={cycleTheme}
        whileHover={{ backgroundColor: "var(--hover)" }}
        whileTap={{ scale: 0.98 }}
        className="mt-3 flex items-center justify-between rounded-xl border border-[var(--border)] px-3 py-2 text-[0.8rem] cursor-pointer"
      >
        <span className="text-[var(--fg-muted)]">Theme</span>
        <span className="font-medium">{THEME_LABEL[theme]}</span>
      </motion.button>
    </div>
  );
}
