"""Drag & drop document list component (SDD 13.13).

Streamlit cannot reorder rows natively, so this component renders the
document table inside a components.v1.html iframe with HTML5 drag & drop.
The new order is communicated back through st.query_params (read by the
project view), keeping the component stateless and the metadata in SQLite.
"""

from __future__ import annotations

import html
import json

import streamlit as st

from noveltrad.core.contracts import Document


def document_table(
    documents: list[Document],
    *,
    theme: str,
    locked: bool,
    t,
) -> None:
    """Render the draggable document table."""
    rows = []
    for doc in documents:
        rows.append(
            {
                "id": doc.id,
                "name": doc.display_name,
                "status": doc.status.value,
                "progress": round(doc.progress),
                "words": doc.word_count,
                "lang": doc.detected_language or "?",
            }
        )
    payload = json.dumps(rows)
    colors = _theme_colors(theme)
    order = json.dumps([doc.id for doc in documents])
    html_body = f"""
    <style>
      body {{ font-family: 'Roboto', sans-serif; margin: 0; padding: 0;
             background: {colors["surface"]}; color: {colors["text"]}; }}
      table {{ width: 100%; border-collapse: collapse; }}
      th {{ text-align: left; padding: 8px 10px; font-size: 13px;
           color: {colors["muted"]}; border-bottom: 2px solid {colors["border"]};
           font-weight: 500; text-transform: uppercase; }}
      td {{ padding: 8px 10px; border-bottom: 1px solid {colors["border"]};
           font-size: 14px; }}
      tr {{ cursor: grab; }}
      tr.dragging {{ opacity: 0.4; }}
      tr.drag-over {{ border-top: 2px solid {colors["primary"]}; }}
      .handle {{ cursor: grab; color: {colors["muted"]}; }}
      .status {{ display: inline-block; padding: 2px 8px; border-radius: 12px;
                font-size: 12px; font-weight: 500; }}
      .status.Completed {{ background: {colors["success_bg"]}; color: {colors["success"]}; }}
      .status.Failed {{ background: {colors["error_bg"]}; color: {colors["error"]}; }}
      .status.Running, .status.ToTranslate {{
        background: {colors["primary_bg"]}; color: {colors["primary"]}; }}
    </style>
    <table id="doc-table">
      <thead>
        <tr>
          <th style="width:30px"></th>
          <th>{html.escape(t("doc.name"))}</th>
          <th style="width:110px">{html.escape(t("doc.status"))}</th>
          <th style="width:70px">{html.escape(t("doc.words"))}</th>
          <th style="width:70px">{html.escape(t("doc.lang"))}</th>
        </tr>
      </thead>
      <tbody id="doc-body"></tbody>
    </table>
    <script>
      const rows = {payload};
      const order = {order};
      const locked = {"true" if locked else "false"};
      const body = document.getElementById('doc-body');
      function render() {{
        body.innerHTML = '';
        const byId = {{}};
        rows.forEach(r => byId[r.id] = r);
        order.forEach(id => {{
          const r = byId[id];
          const tr = document.createElement('tr');
          tr.draggable = !locked;
          tr.dataset.id = id;
          tr.innerHTML = `
            <td class="handle">&#9776;</td>
            <td>${{r.name}}</td>
            <td><span class="status ${{r.status}}">${{r.status}} ${{r.progress}}%</span></td>
            <td>${{r.words}}</td>
            <td>${{r.lang}}</td>`;
          tr.addEventListener('dragstart', (e) => {{
            e.dataTransfer.setData('text/plain', id);
            tr.classList.add('dragging');
          }});
          tr.addEventListener('dragend', () => tr.classList.remove('dragging'));
          tr.addEventListener('dragover', (e) => {{
            e.preventDefault();
            tr.classList.add('drag-over');
          }});
          tr.addEventListener('dragleave', () => tr.classList.remove('drag-over'));
          tr.addEventListener('drop', (e) => {{
            e.preventDefault();
            tr.classList.remove('drag-over');
            const draggedId = Number(e.dataTransfer.getData('text/plain'));
            const from = order.indexOf(draggedId);
            const to = order.indexOf(Number(tr.dataset.id));
            if (from < 0 || to < 0 || from === to) return;
            order.splice(from, 1);
            order.splice(to, 0, draggedId);
            render();
            const url = new URL(window.parent.location.href);
            url.searchParams.set('nt_order', order.join(','));
            window.parent.location.href = url.toString();
          }});
          body.appendChild(tr);
        }});
      }}
      render();
    </script>
    """
    st.components.v1.html(html_body, height=40 + len(rows) * 44 + 40)


def _theme_colors(theme: str) -> dict[str, str]:
    colors = {
        "light": {
            "surface": "#ffffff",
            "text": "#1a1c1e",
            "muted": "#5f6368",
            "border": "#e0e0e0",
            "primary": "#0d9488",
            "primary_bg": "#e0f2f1",
            "success": "#2e7d32",
            "success_bg": "#e6f4ea",
            "error": "#b3261e",
            "error_bg": "#fce8e6",
        },
        "dark": {
            "surface": "#1e1e2e",
            "text": "#e4e6eb",
            "muted": "#9aa0a6",
            "border": "#3f3f56",
            "primary": "#4dd0c4",
            "primary_bg": "#0b3d38",
            "success": "#81c995",
            "success_bg": "#1e3a28",
            "error": "#f2b8b5",
            "error_bg": "#3d1f1d",
        },
        "sepia": {
            "surface": "#faf4e4",
            "text": "#3b2f1c",
            "muted": "#7a6a4f",
            "border": "#d8ccae",
            "primary": "#8a5a2b",
            "primary_bg": "#f0e0c8",
            "success": "#4d6b3a",
            "success_bg": "#e8edd9",
            "error": "#9c3b2e",
            "error_bg": "#f5ded8",
        },
    }
    return colors.get(theme, colors["light"])
