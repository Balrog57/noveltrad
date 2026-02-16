import unittest
from unittest.mock import MagicMock, patch
import json
from src.core.glossary_manager import GlossaryManager
from src.core.database import GlossaryTerm, Project

class TestGlossaryManager(unittest.TestCase):
    def setUp(self):
        # Mock DB project
        self.project = MagicMock(spec=Project)
        self.project.name = "Test Project"
        self.mgr = GlossaryManager(self.project)

    @patch('src.core.glossary_manager.GlossaryTerm')
    def test_add_term_extended(self, MockTerm):
        # Test adding term with new fields
        self.mgr.add_term("src", "tgt", "cat", "note", 50, False, ["v1", "v2"])
        
        MockTerm.create.assert_called_once()
        args = MockTerm.create.call_args[1]
        self.assertEqual(args['project'], self.project)
        self.assertEqual(args['source_term'], "src")
        self.assertEqual(args['priority'], 50)
        self.assertEqual(args['case_sensitive'], False)
        self.assertEqual(args['variants'], '["v1", "v2"]')

    @patch('src.core.glossary_manager.GlossaryTerm')
    def test_find_matches(self, MockTerm):
        # Mock terms retrieval
        term1 = MagicMock()
        term1.source_term = "Foo"
        term1.variants = '["Bar"]'
        term1.priority = 10
        term1.case_sensitive = True
        
        term2 = MagicMock()
        term2.source_term = "baz"
        term2.priority = 100
        term2.case_sensitive = False
        
        # Mock database select
        self.mgr.get_all = MagicMock(return_value=[term1, term2])
        
        # Test 1: Case sensitive match
        text = "Foo and Bar and BAZ"
        matches = self.mgr.find_matches(text)
        
        # Term1 matches "Foo" (source) and "Bar" (variant)
        # Term2 matches "BAZ" (source insensitive)
        
        # Should return [term2, term1] (sorted by priority 100 > 10)
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0], term2)
        self.assertEqual(matches[1], term1)

    def test_escape_xml(self):
        self.assertEqual(self.mgr._escape_xml("<>&\"'"), "&lt;&gt;&amp;&quot;&apos;")
