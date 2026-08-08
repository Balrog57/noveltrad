## 2024-05-24 - Discoverability with Disabled Buttons
**Learning:** Hiding primary actions (like 'Launch') when prerequisites aren't met creates layout shifts and makes the happy path undiscoverable in Streamlit.
**Action:** Always render primary action buttons but use `disabled=True` combined with the `help` parameter to provide actionable tooltips explaining what the user needs to do to enable them.
