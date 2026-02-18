# NovelTrad Desktop

A high-performance desktop application for novel translation, featuring AI-powered suggestions (LLM) and comprehensive glossary management. Replicating the "Stitch" design philosophy for a premium user experience.

## Features

- **Native Desktop App**: Built with PyQt6 for speed and OS integration.
- **Stitch-Inspired UI**: Modern dark theme, sidebar navigation, and card-based segment editor.
- **Format Support**: EPUB, DOCX, TXT.
- **AI Integration**: Support for OpenAI, TranslateGemma (via LM Studio), Argos, and NLLB.
- **TranslateGemma Optimization**: Specialized engine for `translategemma-12b-it` using the Completion API to bypass LM Studio Jinja2 template errors. Optimized for NVIDIA RTX GPUs (e.g., RTX 5070 Ti) with a recommended 8192 context window.
- **Glossary Management**: Create and manage project-specific glossaries.
- **Offline Capable**: Core features work offline; AI features require internet if using cloud API or can run locally with LM Studio.
- **TMX Support**: Import and Export industry-standard Translation Memories.
- **Quality Assurance**: Automated checks and Alignment Tool.

For detailed usage instructions, please refer to the [User Guide](docs/user_guide.md).

## Installation (Development)

1. **Clone the repository**
2. **Create a Virtual Environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate
   ```
3. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
4. **Run the Application**:
   ```powershell
   python src/main_qt.py
   ```
5. **Run Tests**:
   ```powershell
   python -m pytest tests/
   ```

## Building Executable

To create a standalone `.exe` file:

1. Run the build script:
   ```powershell
   .\Build-NovelTrad-Qt.bat
   ```
   This will generate `dist/NovelTrad/NovelTrad.exe`.

## Creating Installer

To create a distributable setup file:

1. Install [Inno Setup](https://jrsoftware.org/isdl.php).
2. Right-click `NovelTrad.iss` and choose "Compile".
   OR run:
   ```powershell
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" NovelTrad.iss
   ```
   This will create `Output/NovelTrad_Setup.exe`.

## Project Structure

- `src/gui/`: Main UI logic (`mainwindow.py`, `components.py`, `styles.py`).
- `src/core/`: Database models (`database.py`) and project logic (`project_manager.py`).
- `src/engines/`: Translation engine interfaces (`llm_engine.py`, etc.).
- `src/formats/`: File parsers.
