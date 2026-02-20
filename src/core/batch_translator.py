"""
Batch Translation - Traduction de chapitres entiers

Permet de traduire un chapitre entier ou tout le projet avec
une barre de progression et la possibilité de mettre en pause/reprendre.
"""

import asyncio
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from src.core.segment_status import SegmentStatus


class BatchState(Enum):
    """État du batch de traduction."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class BatchProgress:
    """Progression du batch de traduction."""
    total_segments: int
    translated_segments: int
    current_segment: str
    elapsed_seconds: float
    estimated_remaining_seconds: float
    
    @property
    def percentage(self) -> float:
        if self.total_segments == 0:
            return 0
        return (self.translated_segments / self.total_segments) * 100


class BatchTranslator:
    """
    Gestionnaire de traduction par lot.
    
    Usage:
        translator = BatchTranslator(chapter, engine)
        translator.start(progress_callback=on_progress)
    """
    
    def __init__(
        self, 
        chapter,  # Chapter model
        engine,    # TranslationEngine
        glossary: Optional[list] = None
    ):
        self.chapter = chapter
        self.engine = engine
        self.glossary = glossary or []
        
        self._state = BatchState.IDLE
        self._progress = BatchProgress(
            total_segments=0,
            translated_segments=0,
            current_segment="",
            elapsed_seconds=0,
            estimated_remaining_seconds=0
        )
        self._progress_callback: Optional[Callable] = None
        self._cancel_requested = False
        
    @property
    def state(self) -> BatchState:
        return self._state
    
    @property
    def progress(self) -> BatchProgress:
        return self._progress
    
    def set_progress_callback(self, callback: Callable[[BatchProgress], None]):
        """Configure le callback de progression."""
        self._progress_callback = callback
        
    async def translate_all(
        self, 
        src_lang: str = "en",
        tgt_lang: str = "fr"
    ):
        """Traduit tous les segments du chapitre."""
        self._state = BatchState.RUNNING
        self._cancel_requested = False
        
        # Charger les segments
        segments = self.chapter.get_segments()
        total = len(segments)
        
        self._progress = BatchProgress(
            total_segments=total,
            translated_segments=0,
            current_segment="",
            elapsed_seconds=0,
            estimated_remaining_seconds=0
        )
        
        import time
        start_time = time.time()
        
        for i, segment in enumerate(segments):
            if self._cancel_requested:
                self._state = BatchState.CANCELLED
                break
                
            if self._state == BatchState.PAUSED:
                await self._wait_for_resume()
            
            # Traduire le segment
            try:
                translated = await self.engine.translate(
                    segment.source_text,
                    src_lang=src_lang,
                    tgt_lang=tgt_lang,
                    glossary=self.glossary
                )
                
                segment.target_text = translated
                segment.status = SegmentStatus.MACHINE.value
                segment.engine_used = self.engine.get_name()
                segment.save()
                
            except Exception as e:
                print(f"Erreur traduction segment {i}: {e}")
                
            # Mettre à jour la progression
            elapsed = time.time() - start_time
            avg_time_per_segment = elapsed / (i + 1)
            remaining = (total - i - 1) * avg_time_per_segment
            
            self._progress = BatchProgress(
                total_segments=total,
                translated_segments=i + 1,
                current_segment=segment.source_text[:50],
                elapsed_seconds=elapsed,
                estimated_remaining_seconds=remaining
            )
            
            if self._progress_callback:
                self._progress_callback(self._progress)
        
        if self._state == BatchState.RUNNING:
            self._state = BatchState.COMPLETED
            
    def pause(self):
        """Met en pause la traduction."""
        if self._state == BatchState.RUNNING:
            self._state = BatchState.PAUSED
            
    def resume(self):
        """Reprend la traduction."""
        if self._state == BatchState.PAUSED:
            self._state = BatchState.RUNNING
            
    def cancel(self):
        """Annule la traduction."""
        self._cancel_requested = True
        self._state = BatchState.CANCELLED
        
    async def _wait_for_resume(self):
        """Attend que l'utilisateur reprenne."""
        while self._state == BatchState.PAUSED:
            if self._cancel_requested:
                break
            await asyncio.sleep(0.5)


# Fonction utilitaire pour traduire tout un projet
async def translate_project(project, engine, progress_callback=None):
    """
    Traduit tout un projet chapitre par chapitre.
    
    Args:
        project: Instance du projet
        engine: Moteur de traduction
        progress_callback: Callback de progression global
    """
    chapters = project.get_chapters()
    total_chapters = len(chapters)
    
    for i, chapter in enumerate(chapters):
        if progress_callback:
            progress_callback(f"Traduction chapitre {i+1}/{total_chapters}")
            
        translator = BatchTranslator(chapter, engine)
        if progress_callback:
            translator.set_progress_callback(progress_callback)
            
        await translator.translate_all()
        
    return True


# Exemple d'utilisation
"""
# Dans la GUI:
async def on_translate_clicked():
    chapter = current_project.get_chapter(1)
    engine = NLLBEngine()  # ou LLMEngine()
    
    translator = BatchTranslator(chapter, engine)
    translator.set_progress_callback(update_progress_bar)
    
    await translator.translate_all()
    
def update_progress_bar(progress: BatchProgress):
    ui.progressBar.setValue(int(progress.percentage))
    ui.statusLabel.setText(f\"{progress.translated_segments}/{progress.total_segments}\")
"""
