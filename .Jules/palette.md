## 2025-06-13 - Missing Accessible Names on Icon-Only Buttons
**Learning:** Icon-only PyQt buttons (like `☰`, `🌙`, and `▼`) often lack accessible names for screen readers and tooltips for mouse hover, making them confusing for users trying to discover their functionality.
**Action:** Always use the custom `src.gui.a11y.configure` utility on PyQt widgets, especially icon-only buttons, to apply an accessible name (`name=...`) and a tooltip (`tooltip=...`) to ensure standard UX and a11y compliance.

## 2023-10-27 - Added ARIA-like labels to activity log toggle button
**Learning:** Found an icon-only button ("▼") in `ActivityLogWidget` without an accessible name, rendering it completely opaque to screen readers. The codebase has a custom accessibility utility `src.gui.a11y.configure` that should be universally applied to widgets to inject ARIA-like `AccessibleName` and `AccessibleDescription`, setup tooltips, shortcuts, and focus policies instead of setting Qt properties manually.
**Action:** When inspecting other icon-only buttons or interactive widgets without text, always remember to pass them through `configure()` rather than invoking `setAccessibleName` directly. If state changes visually (like expanding/collapsing), call `configure()` again to update the tooltip or description.
