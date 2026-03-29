import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class ProjectStructure:
    """Manages OmegaT-compliant .noveltrad/ folder structure for NovelTrad v1.1."""
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.noveltrad_dir = self.project_dir / ".noveltrad"
        
        self.structure: Dict[str, List[str]] = {
            "root": [
                "project.json",
                "project_save.tmx",
                "project_save.tmx.bak",
                "project_save.tmx.timestamp.bak",
                "project_stats.txt",
                "ignored_words.txt",
                "learned_words.txt",
                "segmentation.conf",
                "filters.xml",
                "uiLayout.xml",
                "last_entry.properties",
            ],
            "repositories": [
                "git/",
                "svn/",
            ],
            "tm": [
                "enforce/",
                "auto/",
                "mt/",
                "tmx2source/",
                "export/",
            ],
            "backup": [
                "backup/",
            ],
            "snapshots": [
                "snapshots/",
            ],
            "documentation": [
                "documentation/",
            ],
            "glossary": [
                "glossary/",
            ],
            "dictionary": [
                "dictionary/",
            ],
            "prompts": [
                "prompts/",
            ],
            "notes": [
                "notes/",
            ],
        }
    
    def create_structure(self) -> bool:
        """Create the complete OmegaT-compliant .noveltrad/ structure."""
        try:
            self._create_root()
            self._create_subdirectories()
            self._create_empty_files()
            self._create_gitignore()
            return True
        except Exception as e:
            print(f"Error creating project structure: {e}")
            return False
    
    def _create_root(self) -> None:
        """Create .noveltrad/ root directory."""
        self.noveltrad_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_subdirectories(self) -> None:
        """Create all subdirectories."""
        subdirs = [
            self.noveltrad_dir / ".repositories",
            self.noveltrad_dir / ".repositories" / "git",
            self.noveltrad_dir / ".repositories" / "svn",
            self.noveltrad_dir / "backup",
            self.noveltrad_dir / "snapshots",
            self.noveltrad_dir / "documentation",
            self.noveltrad_dir / "tm",
            self.noveltrad_dir / "tm" / "enforce",
            self.noveltrad_dir / "tm" / "auto",
            self.noveltrad_dir / "tm" / "mt",
            self.noveltrad_dir / "tm" / "tmx2source",
            self.noveltrad_dir / "tm" / "export",
            self.project_dir / "source",
            self.project_dir / "target",
            self.project_dir / "glossary",
            self.project_dir / "dictionary",
            self.project_dir / "prompts",
            self.project_dir / "notes",
        ]
        
        for subdir in subdirs:
            subdir.mkdir(parents=True, exist_ok=True)
    
    def _create_empty_files(self) -> None:
        """Create essential empty files."""
        files = [
            self.noveltrad_dir / "project_stats.txt",
            self.noveltrad_dir / "ignored_words.txt",
            self.noveltrad_dir / "learned_words.txt",
            self.noveltrad_dir / "segmentation.conf",
            self.noveltrad_dir / "filters.xml",
            self.noveltrad_dir / "uiLayout.xml",
            self.noveltrad_dir / "last_entry.properties",
        ]
        
        for file_path in files:
            file_path.touch(exist_ok=True)
    
    def _create_gitignore(self) -> None:
        """Create .gitignore with rationale for OmegaT compatibility."""
        gitignore_content = [
            "# NovelTrad OmegaT-compliant Project - .gitignore",
            "# Generated for v1.1 project structure",
            "",
            "# ============================================",
            "# Project-Specific Files (Never Commit)",
            "# ============================================",
            "",
            "# Project metadata",
            "project.json",
            "",
            "# Translation Memory (may contain sensitive data)",
            "project_save.tmx",
            "project_save.tmx.bak",
            "project_save.tmx.timestamp.bak",
            "tm/**/*.tmx",
            "",
            "# User-specific UILayout",
            "uiLayout.xml",
            "",
            "# Last position marker",
            "last_entry.properties",
            "",
            "# ============================================",
            "# Backup & Snapshots (Local Only)",
            "# ============================================",
            "",
            "# Automatic backups",
            "backup/",
            "snapshots/",
            "!snapshots/.gitkeep",
            "",
            "# ============================================",
            "# Temporary & Cache Files",
            "# ============================================",
            "",
            "*.tmp",
            "*.temp",
            "*.swp",
            "*.swo",
            "*~",
            ".cache/",
            "__pycache__/",
            "",
            "# ============================================",
            "# IDE & Editor Files",
            "# ============================================",
            "",
            ".vscode/",
            ".idea/",
            "*.sublime-project",
            "*.sublime-workspace",
            ".DS_Store",
            "Thumbs.db",
            "",
            "# ============================================",
            "# Log Files",
            "# ============================================",
            "",
            "*.log",
            "logs/",
            "",
            "# ============================================",
            "# build_script.py & Deployment",
            "# ============================================",
            "",
            "build/",
            "dist/",
            "*.spec",
        ]
        
        gitignore_path = self.project_dir / ".gitignore"
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("\n".join(gitignore_content))
    
    def get_structure_info(self) -> Dict[str, any]:
        """Return structure information."""
        info = {
            "project_dir": str(self.project_dir),
            "noveltrad_dir": str(self.noveltrad_dir),
            "created": False,
            "folders": [],
            "files": [],
        }
        
        if self.noveltrad_dir.exists():
            info["created"] = True
            for root, dirs, files in os.walk(self.noveltrad_dir):
                rel_path = os.path.relpath(root, self.project_dir)
                if rel_path != ".":
                    info["folders"].append(rel_path + "/")
                for file in files:
                    info["files"].append(os.path.join(rel_path, file))
        
        return info
    
    def validate_structure(self) -> bool:
        """Validate that essential files/folders exist."""
        essential = [
            self.noveltrad_dir,
            self.noveltrad_dir / "tm" / "enforce",
            self.noveltrad_dir / "tm" / "auto",
            self.noveltrad_dir / "tm" / "mt",
            self.project_dir / "source",
            self.project_dir / "target",
        ]
        
        for path in essential:
            if not path.exists():
                return False
        return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        project_dir = sys.argv[1]
    else:
        project_dir = "./test_project"
    
    structure = ProjectStructure(project_dir)
    if structure.create_structure():
        print(f"✓ Project structure created at: {project_dir}")
        info = structure.get_structure_info()
        print(f"  Folders: {len(info['folders'])}")
        print(f"  Files: {len(info['files'])}")
    else:
        print("✗ Failed to create project structure")
