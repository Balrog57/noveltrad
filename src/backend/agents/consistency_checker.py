"""ConsistencyChecker agent — Agent 5 of the v4 pipeline.

Vector-based consistency check: for every chunk, look up the top-K
neighbour chunks (by source-text embedding) and verify the same
named entity / term is translated consistently.

We use a simple TF-IDF cosine similarity backend by default (no
external deps). If the StateStore has a working LanceDB handle, we
prefer that. Both backends are read-only — the agent emits a list of
`consistency_flags` in the payload, the orchestrator persists them.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any

from .base_worker import BaseWorker

logger = logging.getLogger(__name__)


# ---------- TF-IDF backend (default) ----------


_WORD = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text or "")]


def _tfidf_embed(text: str, vocab: dict[str, int], idf: dict[str, float]) -> dict[int, float]:
    tokens = _tokenize(text)
    if not tokens:
        return {}
    tf = Counter(tokens)
    out: dict[int, float] = {}
    for tok, count in tf.items():
        idx = vocab.get(tok)
        if idx is None:
            continue
        out[idx] = (1.0 + float(count)) * idf.get(tok, 1.0)
    return out


def _cosine(a: dict[int, float], b: dict[int, float]) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) & set(b)
    if not keys:
        return 0.0
    dot = sum(a[k] * b[k] for k in keys)
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _build_tfidf(
    corpus: list[str],
) -> tuple[dict[str, int], dict[str, float], list[dict[int, float]]]:
    """Compute vocab + idf + per-doc sparse embeddings."""
    docs_tokens = [_tokenize(d) for d in corpus]
    df: Counter[str] = Counter()
    for toks in docs_tokens:
        for t in set(toks):
            df[t] += 1
    vocab = {tok: i for i, tok in enumerate(sorted(df))}
    n = max(1, len(corpus))
    idf = {tok: (1.0 + (n / (count + 1))) for tok, count in df.items()}
    embeddings = [_tfidf_embed(d, vocab, idf) for d in corpus]
    return vocab, idf, embeddings


# ---------- agent ----------


class Worker(BaseWorker):
    use_control_thread = True

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        action = msg.get("action")
        if action not in ("check_consistency",):
            return self._emit_error(
                msg.get("chunk_id"),
                "unknown_action",
                f"consistency_checker: unknown action {action!r}",
            )
        payload = msg.get("payload") or {}
        chunk_id = msg.get("chunk_id")
        src = payload.get("source_text", "")
        tgt = payload.get("glossary_applied") or payload.get("raw_translation") or ""
        neighbours: list[dict[str, Any]] = payload.get("neighbours") or []
        if not (src and tgt):
            return self._emit_error(
                chunk_id,
                "empty_input",
                "consistency_checker: missing source/translation",
            )
        flags = self._check(src, tgt, neighbours)
        return self._emit_done(
            chunk_id,
            {
                "consistency_flags": flags,
                "status": "consistency_checked",
            },
        )

    @staticmethod
    def _check(
        source: str,
        target: str,
        neighbours: list[dict[str, Any]],
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Compare target with the K nearest neighbours (by source TF-IDF).

        Flags: any source term that appears in the current source but
        whose target translation differs from the consensus among
        neighbours. Conservative — false positives are okay, the user
        can dismiss them in the chunk detail dialog.
        """
        if not neighbours:
            return []
        corpus = [n.get("source_text", "") for n in neighbours] + [source]
        vocab, idf, embs = _build_tfidf(corpus)
        sims = [
            (_cosine(embs[-1], embs[i]), neighbours[i]) for i in range(len(neighbours))
        ]
        sims.sort(key=lambda x: -x[0])
        top = [n for s, n in sims[:top_k] if s > 0.1]
        if not top:
            return []
        # Build a per-source-term target consensus.
        consensus: dict[str, Counter[str]] = {}
        for n in top:
            tgt_n = n.get("glossary_applied") or n.get("raw_translation") or ""
            src_n = n.get("source_text", "")
            for term in _candidate_terms(src_n):
                if term.lower() in source.lower():
                    consensus.setdefault(term, Counter())[_best_match(term, tgt_n)] += 1
        flags: list[dict[str, Any]] = []
        for term, counter in consensus.items():
            if not counter:
                continue
            expected, _ = counter.most_common(1)[0]
            found = _best_match(term, target)
            if found and expected != found:
                flags.append(
                    {
                        "source_term": term,
                        "expected_translation": expected,
                        "found_translation": found,
                        "confidence": 0.6,
                    }
                )
        return flags


def _candidate_terms(text: str) -> list[str]:
    """Naive term extractor: capitalized bigrams + bare proper nouns."""
    words = _WORD.findall(text)
    out: list[str] = []
    for i, w in enumerate(words):
        if w[:1].isupper() and len(w) > 1:
            out.append(w)
        if i + 1 < len(words) and words[i][:1].isupper() and words[i + 1][:1].isupper():
            out.append(f"{words[i]} {words[i + 1]}")
    return out


def _best_match(term: str, text: str) -> str:
    """Approximate: look for the same term translated in `text`.

    A real implementation would use an alignment model; here we just
    look for any capitalized span after the first occurrence of the
    source term. If the term is uncommon, we return the first
    non-ASCII span (works for EN→ZH/JA/KO targets).
    """
    if term not in text:
        # Fallback: any consecutive non-ASCII run of 1..20 chars after
        # a reasonable offset.
        m = re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]{1,15}", text)
        return m.group(0) if m else ""
    idx = text.find(term)
    after = text[idx + len(term) : idx + len(term) + 30]
    m = re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]{1,15}", after)
    if m:
        return m.group(0)
    return ""


__all__ = ["Worker"]
