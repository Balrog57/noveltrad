# AGENTS.md - Developer Guidelines for NovelTrad

## Project Overview

NovelTrad is a PyQt6-based desktop application for novel translation with AI-powered suggestions. It uses:
- **GUI Framework**: PyQt6
- **Database**: Peewee (SQLite)
- **Translation Engines**: OpenAI LLM, Argos Translate, CTranslate2
- **Python Version**: 3.10+

## Build, Lint, and Test Commands

### Installation
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
python src/main_qt.py
```

### Code Formatting (Black)
```bash
black .
# Or for a specific file:
black src/main_qt.py
```

### Code Linting (Flake8)
```bash
flake8 .
# Or with specific config:
flake8 --max-line-length=100 --ignore=E501,W503 .
```

### Running Tests (Pytest)
```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_database.py

# Run a single test function
pytest tests/test_database.py::test_create_project

# Run a specific test class and method
pytest tests/test_database.py::TestProjectManager::test_create_project

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html
```

### Building Executable
```bash
# Using the build script (Windows)
.\Build-NovelTrad-Qt.bat

# Or directly with PyInstaller
pyinstaller NovelTrad.spec
```

## Code Style Guidelines

### General Principles
- Follow PEP 8 style guide
- Use Python 3.10+ features (match statements, typed dicts, etc.)
- Keep functions small and focused (max 50-80 lines)
- Add type hints to all new functions and methods
- Write docstrings for all public functions

### Imports
Order imports in each file (separate with blank lines):
1. Standard library (`os`, `sys`, `datetime`)
2. Third-party packages (`PyQt6`, `peewee`, `openai`)
3. Local application imports (`src.core`, `src.engines`)

```python
# Correct import order
import os
import sys
from datetime import datetime

from PyQt6.QtWidgets import QMainWindow, QWidget
from PyQt6.QtCore import Qt, QSize
from peewee import Model, SqliteDatabase

from src.core.database import Project, Segment
from src.engines.llm_engine import LLMEngine
```

### Naming Conventions
- **Classes**: `PascalCase` (e.g., `ProjectManager`, `LLMEngine`)
- **Functions/variables**: `snake_case` (e.g., `create_project`, `source_text`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_BATCH_SIZE`)
- **Private methods**: Prefix with underscore (e.g., `_init_client`)
- **File names**: `snake_case.py` (e.g., `database.py`, `llm_engine.py`)

### Type Hints
Always use type hints for function signatures:
```python
def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
    ...

def get_segments(self, chapter_id: int) -> list[Segment]:
    ...

def process_batch(self, texts: list[str]) -> dict[str, str | None]:
    ...
```

### Docstrings
Use Google-style or NumPy-style docstrings:
```python
def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
    """Translate text from source to target language.

    Args:
        text: The text to translate.
        src_lang: Source language code (e.g., 'en', 'zh').
        tgt_lang: Target language code (e.g., 'fr', 'en').

    Returns:
        The translated text, or an error message if translation fails.
    """
```

### Error Handling
- Use specific exception types, not bare `except:`
- Log errors appropriately
- Show user-friendly error messages in GUI
```python
try:
    result = self.engine.translate(text, src_lang, tgt_lang)
except ValueError as e:
    logger.error(f"Invalid language code: {e}")
    return f"[Error] Invalid language: {e}"
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    return "[Error] Network unavailable"
```

### Database Models (Peewee)
- Define a `BaseModel` class that inherits from `Model`
- Use `ForeignKeyField` with `backref` for relationships
- Initialize database connection at runtime, not at import time
```python
db = SqliteDatabase(None)  # Placeholder, initialize with init_db()

class BaseModel(Model):
    class Meta:
        database = db
```

### PyQt6 Best Practices
- Use signals/slots for inter-component communication
- Set object names for debugging (`setObjectName("MyWidget")`)
- Use layouts (QVBoxLayout, QHBoxLayout) instead of fixed positions
- Handle window close events properly
- Use `QApplication.processEvents()` for long-running operations to keep UI responsive

### Testing
- Place tests in `tests/` directory
- Name test files as `test_*.py` or `*_test.py`
- Use pytest fixtures for setup/teardown
- Mock external dependencies (LLM API, file I/O)
```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def project_manager(tmp_path):
    db_path = tmp_path / "test.db"
    pm = ProjectManager()
    pm.create_project("Test", str(db_path), "dummy.epub")
    return pm

def test_create_project(project_manager):
    assert project_manager.current_project is not None
```

## Project Structure

```
src/
├── main_qt.py          # Application entry point
├── core/               # Business logic
│   ├── database.py     # Peewee models
│   ├── project_manager.py
│   ├── glossary_manager.py
│   └── dictionary_manager.py
├── engines/           # Translation engines
│   ├── translation_engine.py  # Abstract base class
│   ├── llm_engine.py          # OpenAI/LLM integration
│   ├── argos_engine.py
│   └── nllb_engine.py
├── formats/           # File format handlers
│   ├── epub_handler.py
│   ├── docx_handler.py
│   ├── pdf_handler.py
│   └── txt_handler.py
├── gui/               # PyQt6 UI
│   ├── mainwindow.py
│   ├── components.py
│   ├── styles.py
│   └── settings_dialog.py
└── utils/             # Utilities
```

## Common Development Tasks

### Adding a New Translation Engine
1. Create new class in `src/engines/` inheriting from `TranslationEngine`
2. Implement all abstract methods
3. Register in `src/engines/__init__.py` factory function
4. Add to engine selection UI in settings

### Adding a New File Format
1. Create handler in `src/formats/`
2. Implement `load()` and `save()` methods
3. Register in `src/formats/format_handler.py`
4. Add to supported formats in file dialogs

### Database Migrations
- Peewee doesn't have built-in migrations
- For schema changes, manually update database or create migration script
- Back up database before migrations
