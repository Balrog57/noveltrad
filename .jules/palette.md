## 2024-07-07 - Add missing interaction states to buttons masquerading as custom components

**Learning:** Custom components like `.nav-item` in Vue (which are `<button>` elements) often miss standard visual affordances like `cursor: pointer` or explicit `:focus-visible` outlines because default button styles are stripped (`border: none`, `background: transparent`), leading to poor discoverability for both mouse and keyboard users.
**Action:** Always ensure that interactive elements that strip native styling explicitly add back `cursor: pointer`, state `transition`s, and a clear `:focus-visible` state.
