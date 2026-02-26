"""
Core module for NovelTrad OmegaT-compliant projects.
"""

from src.core.project_structure import ProjectStructure
from src.core.project_schema import (
    ProjectSchema,
    ProjectManagerSchema,
    Genre,
    SegmentationStrategy,
    TMSettings,
    BackupSettings,
    AccessibilitySettings,
    StatisticsSettings,
    EngineConfig,
)
from src.core.tmx_handler_v3 import TMXHandler

__all__ = [
    "ProjectStructure",
    "ProjectSchema",
    "ProjectManagerSchema",
    "Genre",
    "SegmentationStrategy",
    "TMSettings",
    "BackupSettings",
    "AccessibilitySettings",
    "StatisticsSettings",
    "EngineConfig",
    "TMXHandler",
]
