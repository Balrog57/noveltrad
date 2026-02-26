"""
Project schema v3.0.0 for NovelTrad OmegaT-compliant projects.
Uses Pydantic BaseModel for validation and type safety.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime, timezone


class Genre(str, Enum):
    """Supported genres for translation projects."""
    GENERAL = "general"
    LITERARY = "literary"
    TECHNICAL = "technical"
    SCIENCE_FICTION = "science_fiction"
    FANTASY = "fantasy"
    ROMANCE = "romance"
    MYSTERY = "mystery"
    HISTORY = "history"
    BIOGRAPHY = "biography"
    EDUCATIONAL = "educational"
    GAME = "game"
    CUSTOM = "custom"


class SegmentationStrategy(str, Enum):
    """Strategy for text segmentation."""
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    LINE = "line"
    CUSTOM = "custom"


class TMSettings(BaseModel):
    """Translation Memory settings."""
    enforce_folder: str = Field(default="tm/enforce", description="Force-insert TM folder")
    auto_folder: str = Field(default="tm/auto", description="Auto-insert TM folder")
    mt_folder: str = Field(default="tm/mt", description="Machine Translation folder")
    tmx2source_folder: str = Field(default="tm/tmx2source", description="Reference language folder")
    export_folder: str = Field(default="tm/export", description="Export location")
    penalty_percentage: int = Field(default=30, ge=0, le=100, description="Penalty for MT matches")
    fuzzy_threshold: int = Field(default=60, ge=0, le=100, description="Fuzzy match threshold %")
    auto_insert_confidence: int = Field(default=85, ge=0, le=100, description="Auto-insert confidence %")


class BackupSettings(BaseModel):
    """Backup and snapshot settings."""
    enabled: bool = Field(default=True, description="Enable automatic backups")
    interval_minutes: int = Field(default=3, ge=1, le=1440, description="Auto-snapshot interval")
    max_snapshots: int = Field(default=10, ge=1, le=100, description="Maximum snapshots to keep")
    backup_location: str = Field(default="backup", description="Backup storage location")
    snapshot_location: str = Field(default="snapshots", description="Snapshot storage location")
    before_modification: bool = Field(default=True, description="Backup before segment modification")


class AccessibilitySettings(BaseModel):
    """Accessibility and UI settings."""
    theme: str = Field(default="Dark", description="UI Theme")
    font_scale: float = Field(default=1.0, ge=0.5, le=2.0, description="Font scaling factor")
    font_family: str = Field(default="Segoe UI", description="Default font family")
    high_contrast: bool = Field(default=False, description="High contrast mode")
    colorblind_mode: str = Field(default="none", description="Colorblind mode (none/deuteranopia/protanopia/tritanopia)")
    large_text: bool = Field(default=False, description="Enable larger text")
    screen_reader: bool = Field(default=False, description="Enable screen reader support")


class StatisticsSettings(BaseModel):
    """Project statistics tracking."""
    track_wpm: bool = Field(default=True, description="Track words per minute")
    track_sessions: bool = Field(default=True, description="Track session times")
    track_chapters: bool = Field(default=True, description="Track chapter completion")
    track_tmx_imports: bool = Field(default=True, description="Track TMX imports")
    show_progress_dashboard: bool = Field(default=True, description="Show progress dashboard")


class EngineConfig(BaseModel):
    """Configuration for translation engine."""
    name: str = Field(..., description="Engine name")
    enabled: bool = Field(default=True, description="Is engine enabled")
    priority: int = Field(default=0, ge=0, description="Priority (higher = used first)")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Engine-specific settings")


class ProjectSchema(BaseModel):
    """
    Project metadata schema v3.0.0 for NovelTrad OmegaT-compliant projects.
    
    This schema defines the project structure, settings, and metadata
    required for OmegaT-compatible project management.
    
    Attributes:
        schema_version: Schema version identifier
        name: Internal project name (no spaces/special chars)
        title: Display title (human-readable)
        source_lang: Source language code (ISO 639-1)
        target_lang: Target language code (ISO 639-1)
        genres: Project genres for context
        default_engine: Default translation engine
        created_at: Project creation timestamp
        last_modified: Last modification timestamp
    """
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )
    
    schema_version: str = Field(
        default="3.0.0",
        pattern=r"^\d+\.\d+\.\d+$",
        description="Schema version (semantic versioning)"
    )
    
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Internal project name (alphanumeric, underscore, hyphen)"
    )
    
    title: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Display title (human-readable)"
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Project description"
    )
    
    source_lang: str = Field(
        ..., 
        pattern=r'^[a-z]{2}(-[A-Z]{2})?$',
        description="Source language (ISO 639-1, optional country code)"
    )
    
    target_lang: str = Field(
        ..., 
        pattern=r'^[a-z]{2}(-[A-Z]{2})?$',
        description="Target language (ISO 639-1, optional country code)"
    )
    
    genres: List[Genre] = Field(
        default_factory=lambda: [Genre.GENERAL],
        min_length=1,
        description="Project genres"
    )
    
    default_engine: str = Field(
        default="NLLB (Offline)",
        description="Default translation engine name"
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Project creation timestamp"
    )
    
    last_modified: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last modification timestamp"
    )
    
    tm_settings: TMSettings = Field(
        default_factory=TMSettings,
        description="Translation Memory settings"
    )
    
    backup: BackupSettings = Field(
        default_factory=BackupSettings,
        description="Backup and snapshot settings"
    )
    
    accessibility: AccessibilitySettings = Field(
        default_factory=AccessibilitySettings,
        description="Accessibility settings"
    )
    
    statistics: StatisticsSettings = Field(
        default_factory=StatisticsSettings,
        description="Statistics tracking settings"
    )
    
    engines: List[EngineConfig] = Field(
        default_factory=lambda: [EngineConfig(name="NLLB (Offline)", priority=1)],
        description="Configured translation engines"
    )
    
    segmentation: SegmentationStrategy = Field(
        default=SegmentationStrategy.SENTENCE,
        description="Text segmentation strategy"
    )


class ProjectManagerSchema:
    """Project schema manager for v3.0.0."""
    
    SCHEMA_VERSION = "3.0.0"
    SCHEMA_FILE = "project.json"
    TMX_VERSION = "1.4b"
    
    @staticmethod
    def get_defaults() -> Dict[str, Any]:
        """Get default project configuration."""
        schema = ProjectSchema(
            name="new_project",
            title="New Project",
            source_lang="en",
            target_lang="fr",
            genres=[Genre.GENERAL],
        )
        return schema.model_dump(mode='json')
    
    @staticmethod
    def validate_schema(data: Dict[str, Any]) -> bool:
        """Validate project data against schema."""
        try:
            ProjectSchema(**data)
            return True
        except Exception:
            return False
    
    @staticmethod
    def migrate_v2_to_v3(data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v2.0 schema to v3.0."""
        if data.get('schema_version', '').startswith('2'):
            data['schema_version'] = '3.0.0'
            if 'backup_settings' in data:
                data['backup'] = data.pop('backup_settings')
            if 'tm_settings' not in data:
                data['tm_settings'] = TMSettings().model_dump()
            if 'accessibility' not in data:
                data['accessibility'] = AccessibilitySettings().model_dump()
            if 'statistics' not in data:
                data['statistics'] = StatisticsSettings().model_dump()
            if 'engines' not in data:
                data['engines'] = [EngineConfig(name=data.get('default_engine', 'NLLB (Offline)'), priority=1).model_dump()]
            if 'segmentation' not in data:
                data['segmentation'] = 'sentence'
        return data


if __name__ == "__main__":
    import json
    
    schema = ProjectSchema(
        name="test_project",
        title="Test Project",
        source_lang="en",
        target_lang="fr",
        genres=[Genre.LITERARY, Genre.FANTASY],
        default_engine="NLLB (Offline)",
        description="A test OmegaT-compliant project"
    )
    
    print(json.dumps(schema.model_dump(mode='json'), indent=2))
    
    print("\n" + "="*50)
    print("Validating defaults...")
    defaults = ProjectManagerSchema.get_defaults()
    print(f"Schema version: {defaults['schema_version']}")
    print(f"Valid: {ProjectManagerSchema.validate_schema(defaults)}")
