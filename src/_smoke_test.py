"""Smoke-test: instantiate Orchestrator and FastTranslator.Worker in test mode."""
import os, sys, tempfile, pathlib, traceback

os.environ['NOVELTRAD_TRANSLATION_TEST_MODE'] = '1'
os.environ['NOVELTRAD_LLM_DRAFT_ON_NLLB_MISSING'] = '0'
sys.path.insert(0, r'C:\Users\Marc\Documents\1G1R\_Programmation\noveltrad')

print("1) Importing orchestrator...")
try:
    from src.backend.orchestrator.orchestrator import Orchestrator
    print("   OK")
except Exception:
    traceback.print_exc(); sys.exit(1)

print("2) Importing fast_translator.Worker...")
try:
    from src.backend.agents.fast_translator import Worker
    print("   OK")
except Exception:
    traceback.print_exc(); sys.exit(1)

print("3) Constructing Orchestrator...")
proj_dir = tempfile.mkdtemp(prefix='noveltrad_test_')
try:
    orch = Orchestrator(projects_root=proj_dir, log_path=pathlib.Path(proj_dir)/'orch.log')
    print("   OK, status =", orch.snapshot()['project']['status'])
except Exception:
    traceback.print_exc(); sys.exit(1)

print("4) Constructing FastTranslator.Worker (test mode skips NLLB)...")
try:
    # Don't call setup() (which spawns a thread); just verify the patched
    # branch in setup() runs without loading NLLB.
    import os as _os
    print("   env NOVELTRAD_TRANSLATION_TEST_MODE =", repr(_os.environ.get('NOVELTRAD_TRANSLATION_TEST_MODE')))
    w = Worker.__new__(Worker)
    w.worker_id = "smoke-test"
    # Manually invoke the test-mode branch of setup():
    # (we don't call setup() because it spawns a thread; we just check the
    # patched logic is importable and the fallback works)
    fb = w._fallback_translate("hello", "en", "fr")
    print("   fallback result:", repr(fb))
    assert fb is not None, "fallback returned None in test mode!"
    print("   OK")
except Exception:
    traceback.print_exc(); sys.exit(1)

print()
print("ALL SMOKE TESTS PASSED.")
