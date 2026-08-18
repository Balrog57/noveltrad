## 2024-08-18 - Added ARIA labels to icon-only buttons
**Learning:** This application uses a custom localization engine where attributes are handled via data-i18n-attr (e.g. data-i18n-attr="aria-label:key"). Screen readers require accessible labels for icon-only buttons.
**Action:** Always append aria-label to data-i18n-attr when adding tooltips (title) or standalone accessible names to icon-only buttons in templates.
