# Third-party notices

NovelTrad is distributed under the GNU Affero General Public License v3.0 only
(`AGPL-3.0-only`). See `LICENSE`.

## Python runtime dependencies

The following direct dependencies are used at runtime. Full license texts of
each distribution are shipped inside the installed package metadata and can be
retrieved with `pip-licenses` or from each project's official distribution.

| Distribution | License | Purpose |
|---|---|---|
| `streamlit` 1.61.1 | Apache-2.0 | interface FR/EN and downloads |
| `httpx` 0.28.1 | BSD-3-Clause | unique async HTTP client of the three AI adapters |
| `lxml` 6.1.1 | BSD-3-Clause | strict XML/XHTML parsing, network/DTD/entities disabled |
| `beautifulsoup4` 4.15.0 | MIT | tolerant fallback for confined HTML/XHTML fragments |
| `mammoth` 1.12.0 | BSD-2-Clause | semantic DOCX extraction to intermediate HTML |
| `markdown-it-py` 4.2.0 | MIT | GFM tokenization and validation |
| `linkify-it-py` 2.1.0 | MIT | required extension of the retained `gfm-like` profile |
| `Pillow` 12.3.0 | HPND | controlled decoding and lossless WebP conversion |
| `lingua-language-detector` 2.2.0 | Apache-2.0 | local source-language detection |
| `cryptography` 50.0.0 | Apache-2.0 / BSD-3-Clause | AEAD AES-256-GCM encryption of API keys |
| `argon2-cffi` 25.1.0 | MIT | Argon2id derivation of the encryption key |

## Development and interface-test dependencies

| Distribution | License | Purpose |
|---|---|---|
| `pytest`, `pytest-asyncio`, `pytest-cov` | MIT | deterministic tests and coverage |
| `ruff` | MIT | formatting and static analysis |
| `pip-audit` | Apache-2.0 | known-vulnerability audit |
| `pip-licenses` | MIT | license inventory |
| `playwright` (interface tests only) | Apache-2.0 | FR/EN tests and three screen widths |

## Reused implementation sources

Per SDD section 20.7, NovelTrad is a clean-room implementation that may reuse
behaviors and isolated units from the inspected projects listed in the SDD when
they satisfy an existing requirement. Any actual copied or adapted unit is
recorded here with provenance, license notice, and modification indication.

No external source unit has been copied into NovelTrad as of the initial
implementation. If a unit is integrated later, it must freeze the inspected
commit, keep the required notices, mark modifications, remove out-of-scope
branches, and re-run the NovelTrad test suite.
