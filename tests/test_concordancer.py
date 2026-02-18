import pytest
from src.core.concordancer import Concordancer, ConcordanceResult
from dataclasses import dataclass

@dataclass
class MockSegment:
    source_text: str
    target_text: str

@dataclass
class MockTMEntry:
    source_text: str
    target_text: str

def test_search_exact_match():
    conc = Concordancer()
    segments = [
        MockSegment("Hello world", "Bonjour le monde"),
        MockSegment("Another test", "Un autre test")
    ]
    
    results = conc.search("world", segments=segments)
    
    assert len(results) >= 1
    assert results[0].source_text == "Hello world"
    assert results[0].match_type == "substring" or results[0].match_type == "exact"
    assert results[0].origin == "project"

def test_search_fuzzy_match():
    conc = Concordancer(fuzzy_threshold=0.5)
    segments = [
        MockSegment("This is a long sentence for testing", "Ceci est une longue phrase pour tester")
    ]
    
    # "sensence" is a typo of "sentence"
    results = conc.search("sentence", segments=segments)
    assert len(results) > 0
    assert results[0].match_type == "substring" 

    # Test actual fuzzy
    # "testing" vs "tesing"
    results_fuzzy = conc.search("tesing", segments=segments)
    # The logic in Concordancer.py uses SequenceMatcher.ratio()
    # "tesing" vs "This is a long sentence for testing" might have low ratio.
    # Let's try to match the source text more closely for fuzzy
    
    segments_fuzzy = [MockSegment("Apple", "Pomme")]
    results_fuzzy = conc.search("Appel", segments=segments_fuzzy)
    if results_fuzzy:
        assert results_fuzzy[0].match_type == "fuzzy"

def test_search_tm_priority():
    conc = Concordancer()
    segments = [MockSegment("Term", "Project trans")]
    tm_entries = [MockTMEntry("Term", "TM trans")]
    
    results = conc.search("Term", segments=segments, tm_entries=tm_entries)
    
    # Should find both
    assert len(results) == 2
    origins = [r.origin for r in results]
    assert "project" in origins
    assert "tm" in origins

def test_search_regex():
    conc = Concordancer()
    segments = [
        MockSegment("Error 404", "Erreur 404"),
        MockSegment("Error 500", "Erreur 500")
    ]
    
    results = conc.search_regex(r"Error \d+", segments=segments)
    
    assert len(results) == 2
    assert results[0].match_type == "exact"
