#!/usr/bin/env python3
"""Batch translate all Renegade Immortal chapters with premium profile.

On Windows, multiprocessing uses 'spawn' which re-imports this module.
ALL code that creates multiprocessing workers (via orchestrator) MUST be
inside the `if __name__ == '__main__':` guard.
"""
import sys, os, time, multiprocessing
from pathlib import Path


def main():
    multiprocessing.freeze_support()

    # Ensure NovelTrad venv modules come first
    sys.path.insert(0, str(Path(__file__).resolve().parent / ".venv" / "Lib" / "site-packages"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    # Load config
    from src.gui.app_config import ConfigManager
    ConfigManager().apply_environment()

    print(f"[batch] NLLB_MODEL={os.environ.get('NLLB_MODEL','?')}")
    print(f"[batch] OLLAMA_MODEL={os.environ.get('OLLAMA_MODEL','?')}")
    print(f"[batch] OLLAMA_BASE_URL={os.environ.get('OLLAMA_BASE_URL','?')}")
    print(f"[batch] OPENAI_API_KEY={'***' if os.environ.get('OPENAI_API_KEY') else 'NOT SET'}")

    from fastapi.testclient import TestClient
    from src.backend.server import create_app
    import tempfile

    # Discovery
    source_dir = Path(r"C:\Users\Marc\Downloads\wuxiaworld")
    output_dir = source_dir / "target"
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(source_dir.glob("*.txt"))
    # Exclude files that look like they're in subdirs
    files = [f for f in files if f.parent == source_dir]
    print(f"[batch] Found {len(files)} files")

    total_start = time.time()
    success = 0
    fail = 0
    skip = 0

    for i, f in enumerate(files):
        fname = f.name
        out_path = output_dir / f"{f.stem}_{f.stem}.txt"

        if out_path.exists():
            existing = out_path.read_text(encoding="utf-8")
            if len(existing) > 100:
                print(f"[{i+1}/{len(files)}] SKIP {fname} ({len(existing)} chars)")
                skip += 1
                continue

        print(f"[{i+1}/{len(files)}] {fname} ({f.stat().st_size} bytes)...", flush=True)

        # Rate-limit guard: wait between chapters to avoid 429
        if i > 0:
            time.sleep(3)

        # Create fresh client per file
        tmp = tempfile.mkdtemp(prefix="noveltrad_batch_")
        try:
            app = create_app(db_path=Path(tmp) / ".state.db", vector_dir=Path(tmp) / ".vectors")
            client = TestClient(app)
        except Exception as e:
            print(f"  FAIL create_app: {e}")
            fail += 1
            continue

        payload = {
            "project_dir": str(source_dir),
            "source_path": str(f),
            "source_lang": "en",
            "target_lang": "fr",
            "output_path": str(out_path),
            "output_format": "txt",
            "parse": True,
            "profile": "premium",
        }

        try:
            res = client.post("/projects", json=payload)
            if res.status_code != 200:
                print(f"  FAIL: {res.status_code} {res.text[:200]}")
                fail += 1
                continue
            pid = res.json()["project_id"]

            start = time.time()
            while time.time() - start < 600:
                state = client.get("/pipeline/state").json()
                art = state.get("output_artifact") or {}
                if art.get("output_path"):
                    elapsed = time.time() - start
                    out = Path(art["output_path"])
                    text = out.read_text(encoding="utf-8") if out.exists() else ""
                    print(f"  OK {elapsed:.0f}s  {len(text)} chars  {len(text.splitlines())} lines")
                    success += 1
                    break
                proj = state.get("project") or {}
                if proj.get("status") in ("error", "stopped"):
                    events = state.get("event_log_tail", [])
                    last_err = next((e.get("message","?") for e in reversed(events) if e.get("level") == "error"), "?")
                    print(f"  FAIL {proj['status']}: {last_err[:200]}")
                    fail += 1
                    break
                time.sleep(0.5)
            else:
                print(f"  FAIL TIMEOUT after 600s")
                fail += 1

        except Exception as e:
            print(f"  EXCEPTION: {e}")
            fail += 1

        # Cleanup tmp dir
        try:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass

        # Progress summary every 5 files
        if (i + 1) % 5 == 0:
            elapsed_total = time.time() - total_start
            rate = (i + 1) / elapsed_total * 60 if elapsed_total > 0 else 0
            remaining = (len(files) - (i + 1)) / rate if rate > 0 else 0
            print(f"  --- [{i+1}/{len(files)}] success={success} fail={fail} skip={skip} rate={rate:.1f}/min ETA={remaining:.0f}min ---")

    total_elapsed = time.time() - total_start
    print(f"\n[batch] DONE in {total_elapsed/60:.0f}min")
    print(f"[batch] {success} success, {fail} fail, {skip} skipped, {len(files)} total")


if __name__ == '__main__':
    main()
