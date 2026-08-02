from pathlib import Path

from lxml import etree

from src.core.epub.attribution_page import (
    ATTRIBUTION_FILENAME,
    ATTRIBUTION_ID,
    XHTML_MEDIA_TYPE,
    add_attribution_page,
    build_attribution_xhtml,
)
from src.config import GENERATOR_NAME, GENERATOR_SOURCE, NAMESPACES


XHTML_NS = "http://www.w3.org/1999/xhtml"
EPUB_OPS_NS = "http://www.idpf.org/2007/ops"
OPF_NS = NAMESPACES['opf']


def _enable_attribution(monkeypatch):
    """Force both flags on regardless of the developer's local .env."""
    monkeypatch.setattr("src.core.epub.attribution_page.ATTRIBUTION_ENABLED", True)
    monkeypatch.setattr("src.core.epub.attribution_page.ATTRIBUTION_PAGE_ENABLED", True)


def _build_minimal_opf(opf_dir: Path, version: str = "3.0") -> Path:
    """Write a minimal OPF (one manifest item, one itemref) and return its path."""
    opf_path = opf_dir / "content.opf"
    opf_path.write_text(
        f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="{OPF_NS}" version="{version}" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Test Book</dc:title>
  </metadata>
  <manifest>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>""",
        encoding="utf-8",
    )
    (opf_dir / "chapter1.xhtml").write_text("<html/>", encoding="utf-8")
    return opf_path


def _manifest_items(opf_tree):
    manifest = opf_tree.getroot().find('.//opf:manifest', namespaces=NAMESPACES)
    return manifest.findall('.//opf:item', namespaces=NAMESPACES)


def _spine_itemrefs(opf_tree):
    spine = opf_tree.getroot().find('.//opf:spine', namespaces=NAMESPACES)
    return spine.findall('.//opf:itemref', namespaces=NAMESPACES)


# --- build_attribution_xhtml -------------------------------------------------


def test_build_attribution_xhtml_epub2_uses_div_without_epub_type():
    xhtml_bytes = build_attribution_xhtml("2.0")
    root = etree.fromstring(xhtml_bytes)

    assert root.tag == f"{{{XHTML_NS}}}html"
    assert b"<div" in xhtml_bytes
    assert b"epub:type" not in xhtml_bytes
    assert b"<section" not in xhtml_bytes


def test_build_attribution_xhtml_epub3_uses_section_with_colophon_type():
    xhtml_bytes = build_attribution_xhtml("3.0")
    root = etree.fromstring(xhtml_bytes)

    section = root.find(f".//{{{XHTML_NS}}}section")
    assert section is not None
    assert section.get(f"{{{EPUB_OPS_NS}}}type") == "colophon"


def test_both_variants_contain_generator_name_and_source_verbatim():
    for version in ("2.0", "3.0"):
        xhtml_bytes = build_attribution_xhtml(version)
        text = xhtml_bytes.decode("utf-8")
        assert GENERATOR_NAME in text
        assert GENERATOR_SOURCE in text


# --- add_attribution_page -----------------------------------------------------


def test_happy_path_adds_manifest_item_and_last_spine_itemref(tmp_path: Path, monkeypatch):
    _enable_attribution(monkeypatch)
    opf_path = _build_minimal_opf(tmp_path, version="3.0")
    opf_tree = etree.parse(str(opf_path))

    href = add_attribution_page(opf_tree, str(tmp_path))

    assert href == ATTRIBUTION_FILENAME
    assert (tmp_path / ATTRIBUTION_FILENAME).exists()

    items = _manifest_items(opf_tree)
    attribution_items = [i for i in items if i.get("id") == ATTRIBUTION_ID]
    assert len(attribution_items) == 1
    assert attribution_items[0].get("href") == ATTRIBUTION_FILENAME
    assert attribution_items[0].get("media-type") == XHTML_MEDIA_TYPE

    itemrefs = _spine_itemrefs(opf_tree)
    assert itemrefs[-1].get("idref") == ATTRIBUTION_ID


def test_master_switch_off_disables_page(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("src.core.epub.attribution_page.ATTRIBUTION_ENABLED", False)
    monkeypatch.setattr("src.core.epub.attribution_page.ATTRIBUTION_PAGE_ENABLED", True)
    opf_path = _build_minimal_opf(tmp_path)
    opf_tree = etree.parse(str(opf_path))

    before_items = len(_manifest_items(opf_tree))
    before_refs = len(_spine_itemrefs(opf_tree))

    href = add_attribution_page(opf_tree, str(tmp_path))

    assert href is None
    assert not (tmp_path / ATTRIBUTION_FILENAME).exists()
    assert len(_manifest_items(opf_tree)) == before_items
    assert len(_spine_itemrefs(opf_tree)) == before_refs


def test_page_flag_off_disables_page(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("src.core.epub.attribution_page.ATTRIBUTION_ENABLED", True)
    monkeypatch.setattr("src.core.epub.attribution_page.ATTRIBUTION_PAGE_ENABLED", False)
    opf_path = _build_minimal_opf(tmp_path)
    opf_tree = etree.parse(str(opf_path))

    before_items = len(_manifest_items(opf_tree))
    before_refs = len(_spine_itemrefs(opf_tree))

    href = add_attribution_page(opf_tree, str(tmp_path))

    assert href is None
    assert not (tmp_path / ATTRIBUTION_FILENAME).exists()
    assert len(_manifest_items(opf_tree)) == before_items
    assert len(_spine_itemrefs(opf_tree)) == before_refs


def test_idempotent_on_second_call(tmp_path: Path, monkeypatch):
    _enable_attribution(monkeypatch)
    opf_path = _build_minimal_opf(tmp_path)
    opf_tree = etree.parse(str(opf_path))

    first_href = add_attribution_page(opf_tree, str(tmp_path))
    second_href = add_attribution_page(opf_tree, str(tmp_path))

    assert first_href == ATTRIBUTION_FILENAME
    assert second_href is None

    attribution_items = [i for i in _manifest_items(opf_tree) if i.get("id") == ATTRIBUTION_ID]
    assert len(attribution_items) == 1

    matching_refs = [r for r in _spine_itemrefs(opf_tree) if r.get("idref") == ATTRIBUTION_ID]
    assert len(matching_refs) == 1


def test_foreign_id_collision_falls_back_to_suffixed_name(tmp_path: Path, monkeypatch):
    _enable_attribution(monkeypatch)
    opf_path = _build_minimal_opf(tmp_path)
    opf_tree = etree.parse(str(opf_path))

    # A foreign item already owns our id, but under a different filename, so
    # the idempotence guard (which requires id AND filename to match ours)
    # does not fire and the collision must be resolved via suffixing.
    manifest = opf_tree.getroot().find('.//opf:manifest', namespaces=NAMESPACES)
    foreign = etree.SubElement(manifest, '{%s}item' % OPF_NS)
    foreign.set('id', ATTRIBUTION_ID)
    foreign.set('href', 'something-else.xhtml')
    foreign.set('media-type', 'application/xhtml+xml')

    href = add_attribution_page(opf_tree, str(tmp_path))

    assert href == "tbl-attribution-1.xhtml"
    attribution_items = [i for i in _manifest_items(opf_tree) if i.get("href") == href]
    assert len(attribution_items) == 1
    assert attribution_items[0].get("id") == "tbl-attribution-1"


def test_never_raises_when_opf_dir_does_not_exist(tmp_path: Path, monkeypatch):
    _enable_attribution(monkeypatch)
    opf_path = _build_minimal_opf(tmp_path)
    opf_tree = etree.parse(str(opf_path))

    before_items = len(_manifest_items(opf_tree))
    before_refs = len(_spine_itemrefs(opf_tree))

    missing_dir = str(tmp_path / "does-not-exist")
    href = add_attribution_page(opf_tree, missing_dir)

    assert href is None
    assert len(_manifest_items(opf_tree)) == before_items
    assert len(_spine_itemrefs(opf_tree)) == before_refs
