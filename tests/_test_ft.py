"""Integration test for fast_translator test-mode patch.

Confirms:
  1) setup() returns in <1s when NOVELTRAD_TRANSLATION_TEST_MODE=1
  2) handle_task() emits a 'done' event with engine='translation-test-mode'
  3) Chinese input is processed and yields a non-empty raw_translation
"""
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("NOVELTRAD_TRANSLATION_TEST_MODE", "1")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Force stdout to UTF-8 so the print of test 3 doesn't crash on cp1252
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.backend.agents.fast_translator import Worker


class _CaptureQ:
    def __init__(self):
        self.items = []

    def put(self, item, timeout=None, **kwargs):
        self.items.append(item)

    def get(self, timeout=None):
        return self.items.pop(0)

    def qsize(self):
        return len(self.items)

    def empty(self):
        return len(self.items) == 0


def make_worker():
    in_q = _CaptureQ()
    out_q = _CaptureQ()
    ctrl_q = _CaptureQ()
    w = Worker(
        stage="fast_translator",
        worker_id="test-ft",
        input_queue=in_q,
        output_queue=out_q,
        control_queue=ctrl_q,
    )
    return w


def test_setup_speed():
    w = make_worker()
    t0 = time.perf_counter()
    w.setup()
    elapsed = time.perf_counter() - t0
    print(f"[TEST 1] setup() took {elapsed:.4f}s (must be < 1.0s)")
    assert elapsed < 1.0, f"setup() too slow: {elapsed:.3f}s"
    assert w._engine is None, "expected self._engine is None in test mode"
    print("[TEST 1] PASS - NLLB skipped in test mode")


def test_handle_task_translate():
    w = make_worker()
    w.setup()
    msg = {
        "action": "translate",
        "chunk_id": "test-chunk-1",
        "payload": {
            "source_text": "hello world",
            "source_lang": "en",
            "target_lang": "fr",
        },
    }
    w.handle_task(msg)
    events = w.output_queue.items
    types = [e.get("type") for e in events]
    print(f"[TEST 2] event types: {types}")
    done = next((e for e in events if e.get("type") == "done"), None)
    assert done is not None, f"no done event in {events}"
    engine = done["payload"]["engine"]
    assert engine == "translation-test-mode", (
        f"expected engine='translation-test-mode', got {engine!r}"
    )
    assert done["payload"]["status"] == "fast_translated"
    raw = done["payload"]["raw_translation"]
    print(f"[TEST 2] raw_translation repr: {raw!r}")
    assert raw and len(raw) > 0
    print("[TEST 2] PASS - handle_task emitted translation-test-mode event")


def test_chinese_input():
    w = make_worker()
    w.setup()
    msg = {
        "action": "translate",
        "chunk_id": "wuxia-001",
        "payload": {
            "source_text": "少年从山中走出",
            "source_lang": "zh",
            "target_lang": "fr",
        },
    }
    w.handle_task(msg)
    done_evt = next(
        (e for e in w.output_queue.items if e.get("type") == "done"),
        None,
    )
    assert done_evt is not None, "no done event"
    raw = done_evt["payload"]["raw_translation"]
    safe = raw.encode("unicode_escape").decode("ascii")
    print(f"[TEST 3] zh->fr raw_translation (escaped): {safe}")
    print(f"[TEST 3] length: {len(raw)} chars")
    assert len(raw) > 0
    print("[TEST 3] PASS - Chinese input produced translation output")


if __name__ == "__main__":
    test_setup_speed()
    print()
    test_handle_task_translate()
    print()
    test_chinese_input()
    print()
    print("=== ALL TESTS PASSED ===")
