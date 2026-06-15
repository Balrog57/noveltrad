"""Quick integration test for the fast_translator patch.

Verifies that, in NOVELTRAD_TRANSLATION_TEST_MODE=1:
1. setup() returns quickly (skips NLLB load)
2. handle_task() routes a Chinese chunk through the deterministic
   fallback and emits a translation-test-mode result
"""
import os
import sys
import time
from pathlib import Path

# Set the test-mode env var BEFORE importing the worker
os.environ["NOVELTRAD_TRANSLATION_TEST_MODE"] = "1"

PROJECT_ROOT = Path("C:/Users/Marc/Documents/1G1R/_Programmation/noveltrad")
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.agents.fast_translator import Worker  # noqa: E402


def main() -> int:
    # Bypass Worker.__init__ (it pulls a BaseWorker that needs
    # real queues). We only need a minimal object to exercise setup()
    # and handle_task().
    ft = Worker.__new__(Worker)
    ft.worker_id = "test-worker"
    ft._engine = None
    ft.stage = "fast_translator"  # required by BaseWorker._emit

    # output_queue is the only one handle_task touches (for progress
    # events and the result). put(item, timeout=2.0) is the real
    # signature; we capture into a list.
    events: list = []

    class _CaptureQ:
        def put(self, item, timeout=None):
            events.append(item)

    ft.output_queue = _CaptureQ()

    # --- Test 1: setup() should be fast (NLLB is skipped) ---
    t0 = time.time()
    ft.setup()
    elapsed = time.time() - t0
    print(f"setup() took {elapsed:.3f}s")
    assert elapsed < 5.0, f"setup() too slow: {elapsed:.3f}s"
    assert ft._engine is None, (
        f"expected engine=None in test mode, got {ft._engine!r}"
    )
    print("[OK] setup() skips NLLB in test mode")

    # --- Test 2: handle_task() with a Chinese chunk ---
    msg = {
        "chunk_id": "test-chunk-1",
        "action": "translate",
        "payload": {
            "source_text": (
                "\u5c11\u5e74\u4ece\u5c71\u4e2d\u8d70\u51fa\uff0c"
                "\u8eab\u540e\u80cc\u7740\u957f\u5251\u3002"
            ),
            "source_lang": "zh",
            "target_lang": "fr",
        },
    }
    ft.handle_task(msg)
    # The worker emits a "progress" event (100%) then a "done" event
    # onto output_queue. The done event carries raw_translation,
    # engine, and status.
    dones = [e for e in events if e.get("type") == "done"]
    assert len(dones) == 1, (
        f"expected 1 done event, got {len(dones)} (events={events!r})"
    )
    done_payload = dones[0].get("payload", {})
    engine = done_payload.get("engine")
    print(f"[OK] handle_task emitted engine={engine!r}")
    assert engine == "translation-test-mode", (
        f"unexpected engine: {engine!r}"
    )
    raw = done_payload.get("raw_translation", "")
    assert raw, "empty raw_translation in done event"
    print(f"     raw_translation: {raw[:80]!r}")
    # _fallback_translate in test mode returns "[<target_lang>] <source>"
    assert raw.startswith("[fr] "), (
        f"unexpected translation format: {raw!r}"
    )
    assert "\u5c11\u5e74" in raw, "source not echoed in fallback"
    assert done_payload.get("status") == "fast_translated"

    # --- Test 3: error path when fallback cannot translate ---
    import src.backend.agents.fast_translator as ft_mod
    original_fallback = ft_mod.Worker._fallback_translate
    ft_mod.Worker._fallback_translate = lambda self, src, sl, tl: None
    events.clear()
    msg2 = {
        "chunk_id": "test-chunk-err",
        "action": "translate",
        "payload": {
            "source_text": "another chunk",
            "source_lang": "zh",
            "target_lang": "fr",
        },
    }
    ft.handle_task(msg2)
    ft_mod.Worker._fallback_translate = original_fallback
    errs = [e for e in events if e.get("type") == "error"]
    assert len(errs) == 1, (
        f"expected 1 error event, got {len(errs)} (events={events!r})"
    )
    err_payload = errs[0].get("payload", {})
    assert err_payload.get("error_code") == "test_translation_unavailable", (
        f"unexpected error_code: {err_payload.get('error_code')!r}"
    )
    print("[OK] error path emits test_translation_unavailable")

    print("\nAll pipeline tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
