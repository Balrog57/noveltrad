## 2024-05-24 - Missing ARIA labels in HTML tooltips
**Learning:** Found a pattern where icon-only buttons in HTML templates were given a title via `data-i18n-attr="title:..."` for visual tooltips, but omitted the standard `aria-label` and `aria-label` i18n attribute for screen readers.
**Action:** When adding or updating tooltips on icon-only buttons, ensure both `title` and `aria-label` are set and localized to ensure full accessibility for screen readers.
