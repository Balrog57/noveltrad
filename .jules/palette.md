## 2024-03-24 - Layout shift prevention and semantic navigation
**Learning:** Adding a border to an active state (like `border-left: 3px solid var(--accent)`) without defining a transparent border on the default state causes layout shift/jitter when the user clicks or hovers the item. Furthermore, instead of using `aria-label` which overwrites the link text for screen readers, `aria-current="page"` should be used to semantically indicate the active item while preserving the visible text label. Icons used purely for decoration next to text labels should have `aria-hidden="true"`.
**Action:** Always provide a transparent default border (e.g., `border-left: 3px solid transparent`) to reserve space for active state borders. Use `aria-current="page"` conditionally based on active state instead of overriding labels with `aria-label`, and hide decorative icons from screen readers.

## 2024-05-18 - Tooltips on icon-only buttons
**Learning:** While `aria-label` is crucial for screen readers, sighted mouse users are left guessing the function of an icon-only button if a native tooltip isn't provided. For instance, a simple "X" modal close button needs a `title` attribute for mouse hover functionality in addition to its `aria-label`.
**Action:** Always complement `aria-label` with a `title` attribute on icon-only buttons (like `✕` or `🗑️`) so that both screen reader users and mouse users receive context.

## 2024-07-13 - State Toggle Button Accessibility
**Learning:** Adding an `aria-label` to a state-toggling button that already contains dynamic, informative text (e.g., `{{ currentMode === 'A' ? 'A' : 'B' }}`) is an accessibility anti-pattern. The `aria-label` completely overrides the visible text for screen readers, hiding the crucial state context.
**Action:** When improving state toggle buttons, do not use `aria-label` if it overrides useful dynamic text. Instead, use a `title` attribute for a visual tooltip and `:aria-pressed="condition"` to expose the toggle state programmatically to screen readers.

## 2024-07-28 - PySide6 Toggle Button Accessibility
**Learning:** Adding static accessibility properties (e.g., `AccessibleName`, tooltips) to icon-only toggle buttons in PySide6 is insufficient, as the state (e.g., collapsed vs expanded) is lost to screen readers if it is not dynamically updated upon toggling. Relying solely on `aria-pressed` or `setChecked` can be confusing if the button implies an action rather than a generic toggle.
**Action:** When implementing collapsible UI elements in PySide6 (e.g., accordion headers) using checkable buttons, ensure the accessible name and tooltip dynamically update to reflect the new implied action (e.g., "Collapse [section]" vs "Expand [section]") inside the `toggled` slot handler.
