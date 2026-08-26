import { motion } from "framer-motion";
import { ASSET_CATALOG, CATEGORY_ORDER } from "../data/assetCatalog";
import { useChatStore } from "../store/chatStore";

export function AssetPicker() {
  const pickAsset = useChatStore((s) => s.pickAsset);
  const isGenerating = useChatStore((s) => s.isGenerating);
  const activeFlow = useChatStore((s) => s.flow);
  const disabled = isGenerating || !!activeFlow?.awaitingFieldId;

  return (
    <div className="mt-2 space-y-4">
      {CATEGORY_ORDER.map((category) => {
        const assets = ASSET_CATALOG.filter((a) => a.category === category);
        if (!assets.length) return null;
        return (
          <div key={category}>
            <div className="mb-1.5 text-[0.72rem] font-semibold uppercase tracking-wide text-[var(--fg-faint)]">
              {category}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {assets.map((asset) => (
                <motion.button
                  key={asset.asset_id}
                  type="button"
                  disabled={disabled}
                  onClick={() => pickAsset(asset.asset_id)}
                  whileHover={disabled ? undefined : { y: -2, borderColor: "var(--border-strong)" }}
                  whileTap={disabled ? undefined : { scale: 0.98 }}
                  transition={{ duration: 0.14 }}
                  className="text-left rounded-xl border border-[var(--border)] bg-[var(--bg-raised)] px-3.5 py-3
                    disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[0.88rem] font-semibold">{asset.label}</span>
                    {asset.live && (
                      <span className="rounded-full bg-[var(--accent)] px-1.5 py-[1px] text-[0.62rem] font-semibold text-[var(--accent-fg)]">
                        LIVE
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 text-[0.78rem] leading-snug text-[var(--fg-muted)]">{asset.description}</p>
                </motion.button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
