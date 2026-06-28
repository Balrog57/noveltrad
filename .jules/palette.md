
## 2026-06-28 - Contextual Accessible Names on Dynamic Table Actions
**Learning:** For dynamic tables displaying items (like projects), simply using an icon or generic text ("Open", "✏", "🗑") on per-row action buttons creates an accessibility issue for screen readers, as the context (the specific row item) is lost.
**Action:** Always use the `configure()` utility on per-row action buttons immediately after instantiation to inject the row's specific context into its `AccessibleName` (e.g., "Rename {item_name}").
