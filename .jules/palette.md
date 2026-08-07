## 2025-02-12 - Streamlit Icon-Only Button Accessibility
**Learning:** Icon-only buttons in Streamlit (like '↑', '↓', '🗑') lack accessible names for screen readers and tooltips for mouse users by default.
**Action:** Always provide the `help` parameter to `st.button` when using an icon as the label to ensure both visual tooltips and screen reader accessibility.
