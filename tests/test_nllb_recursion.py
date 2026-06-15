import unittest
from src.backend.engines.nllb_engine import NLLBEngine

class TestNLLBRecursion(unittest.TestCase):
    def test_single_newline_no_recursion(self):
        engine = NLLBEngine(model="/tmp/mock_model")

        # We can test translate directly, mock _translator so available=True
        engine._translator = True
        engine._load_error = None

        # mock sp.encode
        class MockSP:
            def encode(self, *args, **kwargs):
                return ["1", "2"]
            def decode(self, *args, **kwargs):
                return "decoded"

        engine._sp = MockSP()
        engine._sp_target = MockSP()

        class MockTranslator:
            def translate_batch(self, *args, **kwargs):
                class Res:
                    hypotheses = [["tgt", "a", "b"]]
                return [Res()]
        engine._translator = MockTranslator()

        # This should not raise RecursionError after fix
        res = engine.translate("Hello\nWorld", "en", "fr")
        self.assertEqual(res, "decoded")

    def test_multiblock_newline_works(self):
        engine = NLLBEngine(model="/tmp/mock_model")
        engine._translator = True
        engine._load_error = None

        class MockSP:
            def encode(self, *args, **kwargs):
                return ["1", "2"]
            def decode(self, *args, **kwargs):
                return "decoded"

        engine._sp = MockSP()
        engine._sp_target = MockSP()

        class MockTranslator:
            def translate_batch(self, *args, **kwargs):
                class Res:
                    hypotheses = [["tgt", "a", "b"]]
                return [Res()]
        engine._translator = MockTranslator()

        # This should translate the multiblock text successfully, preserving paragraphs
        res = engine.translate("Hello\n\nWorld", "en", "fr")
        self.assertEqual(res, "decoded\n\ndecoded")

if __name__ == "__main__":
    unittest.main()
