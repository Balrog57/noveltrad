# Palette's Journal

Critical UX/accessibility learnings for NovelTrad. Routine improvements are not logged here.

## 2026-08-25 - Collapsible section toggles use non-focusable divs
**Learning:** Settings, Notifications, and Activity Log collapsibles were `<div onclick>` headers — invisible to keyboard and screen readers. The `.prompt-options-toggle` pattern should be `<button type="button">` with `aria-expanded` / `aria-controls`, plus `button.prompt-options-toggle` reset styles and `:focus-visible`.
**Action:** When touching any collapsible header, convert div → button and sync `aria-expanded` in the toggle handler. All three Settings-tab collapsibles (Provider & Defaults, Notifications, Activity Log) now follow this pattern.
## 2026-09-04 - Ensure icon-only elements have fallback accessible names
**Learning:** Icon-only elements lacking visible text at instantiation fail accessibility checks without immediate fallback names, even if they use dynamic `data-i18n-attr` or JS hydration.
**Action:** Always provide a standard HTML `aria-label` attribute on icon-only buttons as a fallback, alongside any `data-i18n-attr` dynamic localization strings, to guarantee immediate screen-reader support.
