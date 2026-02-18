import os
import pytest
from src.core.tmx_handler import TMXHandler
from dataclasses import dataclass

@dataclass
class MockSegment:
    source_text: str
    target_text: str

def test_export_tmx(tmp_path):
    # Setup
    output_file = tmp_path / "test.tmx"
    segments = [
        MockSegment("Hello", "Bonjour"),
        MockSegment("World", "Monde"),
        MockSegment("Test", "") # Should be skipped based on logic
    ]
    
    # Execute
    success = TMXHandler.export_tmx(segments, "en", "fr", str(output_file))
    
    # Verify
    assert success is True
    assert output_file.exists()
    
    with open(output_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Bonjour" in content
        assert "Monde" in content
        assert "srclang=\"en\"" in content

def test_import_tmx(tmp_path):
    # Setup
    tmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4">
  <header creationtool="NovelTrad" creationtoolversion="1.0" datatype="PlainText" segtype="sentence" adminlang="en" srclang="en" o-tmf="NovelTradDB"/>
  <body>
    <tu>
      <tuv xml:lang="en">
        <seg>Hello</seg>
      </tuv>
      <tuv xml:lang="fr">
        <seg>Bonjour</seg>
      </tuv>
    </tu>
    <tu>
      <tuv xml:lang="en">
        <seg>World</seg>
      </tuv>
      <tuv xml:lang="fr">
        <seg>Monde</seg>
      </tuv>
    </tu>
  </body>
</tmx>
"""
    input_file = tmp_path / "input.tmx"
    with open(input_file, "w", encoding="utf-8") as f:
        f.write(tmx_content)
        
    # Execute
    pairs = TMXHandler.import_tmx(str(input_file))
    
    # Verify
    assert len(pairs) == 2
    assert pairs[0] == ("Hello", "Bonjour")
    assert pairs[1] == ("World", "Monde")

def test_import_tmx_invalid(tmp_path):
    # Setup
    input_file = tmp_path / "invalid.tmx"
    with open(input_file, "w", encoding="utf-8") as f:
        f.write("<tmx>Invalid content")
        
    # Execute
    pairs = TMXHandler.import_tmx(str(input_file))
    
    # Verify
    # Should return empty list on error
    assert pairs == []
