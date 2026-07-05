
## 2024-05-18 - [NtTable Keyboard Accessibility]
**Learning:** Adding `tabindex="0"` to row elements (`<tr>`) or sortable headers (`<th>`) allows keyboard navigation but requires explicit `@keydown.enter` and `@keydown.space.prevent` handlers to mirror `@click` behavior, ensuring these elements behave like true interactive buttons for keyboard users.
**Action:** Always map explicit keyboard handlers for `enter` and `space.prevent` alongside `tabindex` and `click` on custom interactive components that are not native `<button>` or `<a>` elements to guarantee a fully accessible experience in Vue 3 applications.
