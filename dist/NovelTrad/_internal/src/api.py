from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import os
import sys

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.engines.llm_engine import LLMEngine
from src.core.project_manager import ProjectManager
from src.core.database import Segment, GlossaryTerm
from src.core.dictionary import DictionaryManager

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

project_manager = ProjectManager()
dictionary_manager = DictionaryManager()

# --- Data Models ---
class TranslationRequest(BaseModel):
    text: str
    src_lang: str
    tgt_lang: str
    glossary: Optional[Dict[str, str]] = None
    model: str = "gemma-3-12b"
    api_key: str = "lm-studio"
    base_url: str = "http://localhost:1234/v1"

class OpenProjectRequest(BaseModel):
    path: str

class SegmentUpdate(BaseModel):
    target_text: str
    status: str = "translated"

class GlossaryItem(BaseModel):
    source_term: str
    target_term: str
    category: str = "general"

class CreateProjectRequest(BaseModel):
    name: str
    source_lang: str = "en"
    target_lang: str = "fr"

# --- Routes ---

from fastapi import FastAPI, HTTPException, Body, UploadFile, File, Form
from fastapi.responses import JSONResponse
import shutil

# ... imports ...

@app.post("/project/new")
async def create_project(
    name: str = Form(...),
    source_lang: str = Form("en"),
    target_lang: str = Form("fr"),
    file: UploadFile = File(...)
):
    try:
        # Save uploaded file
        base_path = os.path.join(project_root, "projects")
        os.makedirs(base_path, exist_ok=True)
        
        # Save the source file
        source_filename = file.filename
        source_path = os.path.join(base_path, source_filename)
        
        with open(source_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Determine DB path
        project_filename = f"{name.replace(' ', '_')}.ntrad"
        db_path = os.path.join(base_path, project_filename)
        
        if os.path.exists(db_path):
             raise HTTPException(400, "Project already exists")

        # Create Project using ProjectManager (which handles importing segments)
        # We need to make sure project_manager is initialized
        global project_manager
        if project_manager is None:
            project_manager = ProjectManager()
            
        project = project_manager.create_project(
            name=name,
            db_path=db_path,
            source_file=source_path,
            source_lang=source_lang,
            target_lang=target_lang
        )
        
        return {
            "status": "success",
            "path": db_path,
            "project": {
                "name": project.name,
                "source_lang": project.source_language,
                "target_lang": project.target_language
            }
        }
    except Exception as e:
        print(f"Error creating project: {e}")
        raise HTTPException(500, str(e))

@app.post("/project/open")
def open_project(req: OpenProjectRequest):
    try:
        if not os.path.exists(req.path):
            raise HTTPException(404, "Project file not found")
            
        project = project_manager.load_project(req.path)
        segments = project_manager.get_segments()
        
        # Serialize
        seg_list = []
        for s in segments:
            seg_list.append({
                "id": s.id,
                "index": s.index,
                "source_text": s.source_text,
                "target_text": s.target_text,
                "status": s.status
            })
            
        glossary_terms = []
        for t in project.glossary:
            glossary_terms.append({
                "id": t.id,
                "source": t.source_term,
                "target": t.target_term,
                "category": t.category
            })

        return {
            "project": {
                "name": project.name,
                "source_lang": project.source_language,
                "target_lang": project.target_language,
                "path": req.path
            },
            "segments": seg_list,
            "glossary": glossary_terms
        }
    except Exception as e:
        raise HTTPException(500, str(e))

@app.put("/segment/{segment_id}")
def update_segment(segment_id: int, update: SegmentUpdate):
    try:
        project_manager.save_translation(segment_id, update.target_text)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/glossary")
def add_glossary_term(term: GlossaryItem):
    try:
        # Assuming single project active or default project behavior for now
        # Ideally we'd link to the specific project ID, but current ProjectManager isn't exposing ID easily
        # We will use the current loaded project if available via ProjectManager state
        if not project_manager.current_project:
             raise HTTPException(400, "No project loaded")
        
        GlossaryTerm.create(
            project=project_manager.current_project,
            source_term=term.source_term,
            target_term=term.target_term,
            category=term.category
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/glossary/{term_id}")
def delete_glossary_term(term_id: int):
    try:
        query = GlossaryTerm.delete().where(GlossaryTerm.id == term_id)
        rows = query.execute()
        if rows == 0:
            raise HTTPException(404, "Term not found")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/utils/translate")
def translate(request: TranslationRequest):
    # Initialize engine on the fly (optimize later)
    engine = LLMEngine(
        api_key=request.api_key, 
        base_url=request.base_url, 
        model=request.model
    )
    
    try:
        result = engine.translate(
            request.text, 
            request.src_lang, 
            request.tgt_lang, 
            glossary_terms=request.glossary
        )
        return {"translation": result}
    except Exception as e:
        # Fallback/Error
        print(f"Translation Error: {e}")
        return {"translation": f"[Error] {str(e)}", "error": str(e)}

@app.get("/dictionary/search")
def search_dictionary(q: str):
    try:
        results = dictionary_manager.search(q)
        return {"results": results}
    except Exception as e:
        raise HTTPException(500, str(e))

class GlossaryGenRequest(BaseModel):
    text: str
    src_lang: str = "en"
    tgt_lang: str = "fr"
    api_key: str = "lm-studio"
    base_url: str = "http://localhost:1234/v1"
    model: str = "gemma-3-12b"

@app.post("/glossary/generate")
def generate_glossary(request: GlossaryGenRequest):
    engine = LLMEngine(
        api_key=request.api_key, 
        base_url=request.base_url, 
        model=request.model
    )
    result_json_str = engine.generate_glossary(request.text, request.src_lang, request.tgt_lang)
    try:
        glossary_items = json.loads(result_json_str)
        return {"glossary": glossary_items}
    except Exception as e:
        return {"glossary": [], "raw": result_json_str, "error": str(e)}

from fastapi.staticfiles import StaticFiles
import os

# Mount static files if they exist (Production/Desktop mode)
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "noveltrad-ui", "dist")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
