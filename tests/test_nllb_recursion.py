import unittest
from unittest.mock import patch
from src.backend.engines.nllb_engine import NLLBEngine


class MockSP:
    """Mock SentencePiece processor — returns identity tokens."""
    def encode(self, *args, **kwargs):
        return ["1", "2"]
    def decode(self, *args, **kwargs):
        return "decoded"


class MockTranslator:
    """Mock CTranslate2 translator — returns one dummy hypothesis per input segment."""
    def translate_batch(self, source, *args, **kwargs):
        class Res:
            def __init__(self):
                self.hypotheses = [["tgt", "a", "b"]]
        n = len(source) if isinstance(source, list) else 1
        return [Res() for _ in range(n)]


class TestNLLBRecursion(unittest.TestCase):
    def setUp(self):
        # Prevent _lazy_load from touching the filesystem / network.
        patcher = patch.object(NLLBEngine, '_lazy_load', return_value=None)
        self._mock_load = patcher.start()
        self.addCleanup(patcher.stop)

    def _mock_engine(self) -> NLLBEngine:
        engine = NLLBEngine(model="/mock/model")
        engine._translator = MockTranslator()
        engine._sp = MockSP()
        engine._sp_target = MockSP()
        engine._load_error = None
        return engine

    def test_single_newline_no_recursion(self):
        """A single \n should NOT trigger multiblock — no RecursionError."""
        engine = self._mock_engine()
        res = engine.translate("Hello\nWorld", "en", "fr")
        self.assertEqual(res, "decoded")

    def test_multiblock_newline_works(self):
        """Double \n\n should trigger multiblock and preserve paragraph structure."""
        engine = self._mock_engine()
        res = engine.translate("Hello\n\nWorld", "en", "fr")
        self.assertEqual(res, "decoded\n\ndecoded")


if __name__ == "__main__":
    unittest.main()
