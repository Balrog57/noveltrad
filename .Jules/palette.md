## 2025-06-13 - Missing Accessible Names on Icon-Only Buttons
**Learning:** Icon-only PyQt buttons (like `☰`, `🌙`, and `▼`) often lack accessible names for screen readers and tooltips for mouse hover, making them confusing for users trying to discover their functionality.
**Action:** Always use the custom `src.gui.a11y.configure` utility on PyQt widgets, especially icon-only buttons, to apply an accessible name (`name=...`) and a tooltip (`tooltip=...`) to ensure standard UX and a11y compliance.
