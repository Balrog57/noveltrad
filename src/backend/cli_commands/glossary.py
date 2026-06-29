"""``glossary`` subcommand: list / add / remove / search terms."""
from __future__ import annotations

from argparse import ArgumentParser

from ..cli_client import get_client


def add_arguments(sub: ArgumentParser) -> None:
    pa = sub.add_subparsers(dest="action", required=True)
    pa.add_parser("list", help="List all terms")
    gadd = pa.add_parser("add", help="Add a term")
    gadd.add_argument("source_term")
    gadd.add_argument("target_term")
    gadd.add_argument("--category")
    grem = pa.add_parser("remove", help="Remove a term")
    grem.add_argument("source_term")
    gs = pa.add_parser("search", help="Search glossary")
    gs.add_argument("query")


def run(args) -> int:
    client = get_client(args)

    if args.action == "list":
        data = client.get("/lexicon").json()
        terms = data.get("terms", [])
        if not terms:
            print("[glossary] Empty.")
            return 0
        print(f"{'Source':<25} {'Target':<25} {'Category':<15}")
        print("-" * 70)
        for t in terms[:50]:
            print(
                f"{t.get('source',''):<25} {t.get('target',''):<25} "
                f"{t.get('category',''):<15}"
            )
        if len(terms) > 50:
            print(f"  ... ({len(terms) - 50} more)")
        return 0

    if args.action == "add":
        payload = {
            "source": args.source_term,
            "target": args.target_term,
            "category": args.category or "",
            "confidence": 1.0,
            "validated_by_user": True,
        }
        client.post("/lexicon", json=payload)
        print(f"[glossary] Added: {args.source_term} -> {args.target_term}")
        return 0

    if args.action == "remove":
        # Search for term
        data = client.get("/lexicon").json()
        terms = data.get("terms", [])
        found = [t for t in terms if t.get("source") == args.source_term]
        if not found:
            print(f"[glossary] Term not found: {args.source_term}")
            return 1
        for t in found:
            tid = t.get("id") or t.get("term_id")
            if tid:
                client.delete(f"/lexicon/{tid}")
                print(f"[glossary] Removed: {args.source_term}")
        return 0

    if args.action == "search":
        data = client.get("/lexicon").json()
        terms = data.get("terms", [])
        q = args.query.lower()
        matches = [
            t
            for t in terms
            if q in t.get("source", "").lower()
            or q in t.get("target", "").lower()
        ]
        if not matches:
            print(f"[glossary] No matches for '{args.query}'")
            return 0
        print(f"[glossary] {len(matches)} matches for '{args.query}':")
        for t in matches:
            print(
                f"  {t.get('source','')} -> {t.get('target','')}  "
                f"[{t.get('category','')}]"
            )
        return 0

    return 0
