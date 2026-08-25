# Palette's Journal

Critical UX/accessibility learnings for NovelTrad. Routine improvements are not logged here.

## 2026-08-25 - Collapsible section toggles use non-focusable divs
**Learning:** Settings, Notifications, and Activity Log collapsibles were `<div onclick>` headers — invisible to keyboard and screen readers. The `.prompt-options-toggle` pattern should be `<button type="button">` with `aria-expanded` / `aria-controls`, plus `button.prompt-options-toggle` reset styles and `:focus-visible`.
**Action:** When touching any collapsible header, convert div → button and sync `aria-expanded` in the toggle handler. Remaining div toggles: Provider & Defaults, Notifications.