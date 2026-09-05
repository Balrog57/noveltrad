# Palette's Journal

Critical UX/accessibility learnings for NovelTrad. Routine improvements are not logged here.

## 2026-08-25 - Collapsible section toggles use non-focusable divs
**Learning:** Settings, Notifications, and Activity Log collapsibles were `<div onclick>` headers — invisible to keyboard and screen readers. The `.prompt-options-toggle` pattern should be `<button type="button">` with `aria-expanded` / `aria-controls`, plus `button.prompt-options-toggle` reset styles and `:focus-visible`.
**Action:** When touching any collapsible header, convert div → button and sync `aria-expanded` in the toggle handler. All three Settings-tab collapsibles (Provider & Defaults, Notifications, Activity Log) now follow this pattern.
## 2026-09-05 - Tooltips for disabled state
**Learning:** Disabled action buttons (like batch download/delete) lack context for why they are disabled or what prerequisite is needed.
**Action:** Always provide tooltips (`title` and `data-i18n-attr`) on disabled primary and secondary buttons explaining the missing prerequisite (e.g. "No files selected"). Remove or update the tooltip when the button becomes enabled.
