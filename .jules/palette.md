# Palette's Journal

Critical UX/accessibility learnings for NovelTrad. Routine improvements are not logged here.

## 2026-08-25 - Collapsible section toggles use non-focusable divs
**Learning:** Settings, Notifications, and Activity Log collapsibles were `<div onclick>` headers — invisible to keyboard and screen readers. The `.prompt-options-toggle` pattern should be `<button type="button">` with `aria-expanded` / `aria-controls`, plus `button.prompt-options-toggle` reset styles and `:focus-visible`.
**Action:** When touching any collapsible header, convert div → button and sync `aria-expanded` in the toggle handler. All three Settings-tab collapsibles (Provider & Defaults, Notifications, Activity Log) now follow this pattern.
## 2026-09-02 - Always provide standard aria-label with dynamic i18n
**Learning:** The UI supports i18n via `data-i18n-attr="aria-label:namespace:key"`, but relying solely on this leaves elements inaccessible to screen readers before the JS payload loads. This was missed on the `preflightZone` region and `glossary-preview-close` button.
**Action:** When adding accessible names using `data-i18n-attr="aria-label:..."`, always provide a fallback HTML `aria-label="Default English text"` attribute on the element to ensure immediate accessibility.
