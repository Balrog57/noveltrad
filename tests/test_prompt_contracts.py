import unittest


class PromptContractsTests(unittest.TestCase):
    def test_contract_imports_without_pyqt6(self) -> None:
        from src.backend.agents.prompt_contracts import literary_contract

        contract = literary_contract()
        self.assertIn("proper names", contract)
        self.assertIn("glossary", contract)
        self.assertIn("halluc", contract.lower())


if __name__ == "__main__":
    unittest.main()
