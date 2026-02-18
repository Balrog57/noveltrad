import os
import pytest
from src.core.project_manager import ProjectManager
from src.core.database import Segment, TranslationMemory

def test_project_lifecycle(tmp_path):
    # 1. Setup
    pm = ProjectManager()
    db_path = tmp_path / "test_project.ntrad"
    src_file = tmp_path / "chapter1.txt"
    src_file.write_text("Hello world.\nThis is a test.", encoding="utf-8")
    
    # 2. Create Project
    project = pm.create_project(
        name="Test Project",
        db_path=str(db_path),
        source_file=str(src_file),
        source_lang="en",
        target_lang="fr"
    )
    
    assert project.name == "Test Project"
    assert os.path.exists(str(db_path))
    
    # 3. Verify Import
    segments = pm.get_segments()
    assert len(segments) == 2
    assert segments[0].source_text == "Hello world."
    
    # 4. Translate a segment
    pm.save_translation(segments[0].id, "Bonjour le monde.")
    
    # 5. Verify Database Update
    updated_seg = Segment.get_by_id(segments[0].id)
    assert updated_seg.target_text == "Bonjour le monde."
    assert updated_seg.status == "translated"
    
    # 6. Export Project
    export_path = tmp_path / "export.txt"
    pm.export_project(str(export_path))
    
    assert export_path.exists()
    content = export_path.read_text(encoding="utf-8")
    assert "Bonjour le monde." in content

def test_tm_sharing(tmp_path):
    # 1. Setup Project A
    pm_a = ProjectManager()
    db_path_a = tmp_path / "project_a.ntrad"
    src_file_a = tmp_path / "source_a.txt"
    src_file_a.write_text("Shared term.", encoding="utf-8")
    
    pm_a.create_project("Project A", str(db_path_a), str(src_file_a), "en", "fr")
    
    # 2. Add to TM in Project A
    # Note: In real app, add_to_tm looks at current_project properties
    pm_a.add_to_tm("Shared term", "Terme partagé")
    
    pm_a.close_project()
    
    # 3. Setup Project B (Same DB? No, usually separate DBs in file-based SQLite)
    # WAIT: The implementation uses a separate SQLite file strictly per project?
    # Let's check init_db in database.py... 
    # Actually, if they use separate .ntrad files, they DON'T share the TM *by default* 
    # unless there is a global TM mechanism.
    # The specs mention "Global TM" vs "Project TM".
    # Let's verify if ProjectManager uses a global DB or local.
    # Looking at project_manager.py: import init_db -> creates connection.
    # It seems strictly local to .ntrad file currently.
    # So this test might fail if unrelated.
    # BUT, Application usually has a way to import/merge TMs.
    
    # Let's test TMX Import/Export as the sharing mechanism then.
    
    # Re-open A
    pm_a.load_project(str(db_path_a))
    tmx_path = tmp_path / "shared.tmx"
    # Export TM from A
    pm_a.export_tm(str(tmx_path))
    pm_a.close_project()
    
    # 4. Project B
    pm_b = ProjectManager()
    db_path_b = tmp_path / "project_b.ntrad"
    src_file_b = tmp_path / "source_b.txt"
    src_file_b.write_text("Shared term.", encoding="utf-8") # Same text
    
    pm_b.create_project("Project B", str(db_path_b), str(src_file_b), "en", "fr")
    
    # Confirm untranslated
    segs = pm_b.get_segments()
    assert segs[0].target_text is None or segs[0].target_text == ""
    
    # 5. Import TMX into B (Simulating "Global Memory" or just Import)
    # We use import_tm function for TM table or import_project_tmx for segments?
    # import_tm populates the memory. import_project_tmx populates segments.
    # Let's populate TM first.
    count = pm_b.import_tm(str(tmx_path))
    assert count == 1
    
    # 6. Search TM in B
    matches = pm_b.get_fuzzy_matches("Shared term")
    assert len(matches) > 0
    assert matches[0]['target'] == "Terme partagé"
    assert matches[0]['similarity'] == 100

def test_tmx_roundtrip(tmp_path):
    # 1. Create Project and Translate
    pm = ProjectManager()
    db_path = tmp_path / "roundtrip.ntrad"
    src_file = tmp_path / "roundtrip.txt"
    src_file.write_text("Roundtrip test.", encoding="utf-8")
    
    pm.create_project("Roundtrip", str(db_path), str(src_file), "en", "fr")
    seg = pm.get_segments()[0]
    pm.save_translation(seg.id, "Test aller-retour.")
    
    # 2. Export TMX (Project segments)
    tmx_path = tmp_path / "project.tmx"
    pm.export_project_tmx(str(tmx_path))
    
    pm.close_project()
    
    # 3. New Project with same source
    db_path_2 = tmp_path / "roundtrip_2.ntrad"
    pm_2 = ProjectManager()
    pm_2.create_project("Roundtrip 2", str(db_path_2), str(src_file), "en", "fr")
    
    # 4. Import TMX (Apply to segments)
    count = pm_2.import_project_tmx(str(tmx_path))
    
    # 5. Verify Auto-Translation
    assert count == 1
    seg_2 = pm_2.get_segments()[0]
    assert seg_2.target_text == "Test aller-retour."
    assert seg_2.status == "translated"
