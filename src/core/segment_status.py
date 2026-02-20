"""
Segment Status System - Suivi de l'état de traduction des segments

Définit les statuts possibles pour chaque segment et leurs couleurs associées.
"""

from enum import Enum
from PyQt6.QtGui import QColor


class SegmentStatus(Enum):
    """Statuts possibles pour un segment de traduction."""
    
    UNTRANSLATED = "untranslated"      # Non traduit
    MACHINE = "machine"                 # Traduit automatiquement
    AI_REFINED = "ai_refined"           # Raffiné par IA
    VALIDATED = "validated"             # Validée manuellement
    
    def get_color(self) -> QColor:
        """Retourne la couleur associée au statut."""
        colors = {
            SegmentStatus.UNTRANSLATED: QColor("#6B7280"),   # Gris
            SegmentStatus.MACHINE: QColor("#F97316"),        # Orange
            SegmentStatus.AI_REFINED: QColor("#3B82F6"),     # Bleu
            SegmentStatus.VALIDATED: QColor("#22C55E"),      # Vert
        }
        return colors.get(self, QColor("#6B7280"))
    
    def get_label(self) -> str:
        """Retourne le label display."""
        labels = {
            SegmentStatus.UNTRANSLATED: "Non traduit",
            SegmentStatus.MACHINE: "Machine",
            SegmentStatus.AI_REFINED: "IA",
            SegmentStatus.VALIDATED: "Validé",
        }
        return labels.get(self, "Inconnu")
    
    @classmethod
    def from_string(cls, value: str) -> "SegmentStatus":
        """Parse un string en SegmentStatus."""
        try:
            return cls(value)
        except ValueError:
            return cls.UNTRANSLATED


# Couleurs pour thème sombre
STATUS_COLORS_DARK = {
    "untranslated": "#6B7280",  # Gris
    "machine": "#F97316",      # Orange
    "ai_refined": "#3B82F6",   # Bleu
    "validated": "#22C55E",     # Vert
}

# Couleurs pour thème clair
STATUS_COLORS_LIGHT = {
    "untranslated": "#9CA3AF",  # Gris clair
    "machine": "#EA580C",       # Orange foncé
    "ai_refined": "#2563EB",   # Bleu foncé
    "validated": "#16A34A",    # Vert foncé
}


def get_status_from_progress(progress: float, has_ai_refinement: bool = False) -> SegmentStatus:
    """Détermine le statut basé sur la progression et le raffinage IA."""
    if progress == 0:
        return SegmentStatus.UNTRANSLATED
    elif has_ai_refinement:
        return SegmentStatus.AI_REFINED
    elif progress > 0:
        return SegmentStatus.MACHINE
    return SegmentStatus.UNTRANSLATED


# Exemple d'utilisation dans la DB
"""
# Dans models.py ou database.py:

class Segment(db.Model):
    source_text = db.TextField()
    target_text = db.TextField(null=True)
    status = db.CharField(
        max_length=20,
        default=SegmentStatus.UNTRANSLATED.value
    )
    
    def set_status(self, status: SegmentStatus):
        self.status = status.value
        self.save()
        
    def get_status(self) -> SegmentStatus:
        return SegmentStatus.from_string(self.status)
"""
