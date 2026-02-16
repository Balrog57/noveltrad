"""
Module d'Assurance Qualité (QA Check) pour NovelTrad.
Vérifications automatiques avant export.
Conforme au cahier des charges §12.9.
"""
import re
from dataclasses import dataclass
from typing import Optional
from src.core.tag_manager import TagManager


@dataclass
class QAIssue:
    """A single quality assurance issue found during QA check."""
    segment_id: int
    segment_index: int
    issue_type: str       # 'missing_tag', 'number_mismatch', 'glossary_violation',
                          # 'empty_translation', 'punctuation_mismatch'
    severity: str         # 'error', 'warning', 'info'
    message: str
    source_text: str
    target_text: str


class QAChecker:
    """
    Quality Assurance checker for translated segments.
    Runs multiple validation checks before export.

    Usage:
        qa = QAChecker()
        issues = qa.run_checks(segments, glossary_terms=glossary)
    """

    def __init__(self):
        self.tag_manager = TagManager()

    def run_checks(self, segments, glossary_terms=None, check_tags=True,
                   check_numbers=True, check_glossary=True,
                   check_empty=True, check_punctuation=True):
        """
        Run all QA checks on a list of segments.

        Args:
            segments: List of segment objects with .id, .index, .source_text, .target_text
            glossary_terms: Optional list of glossary term objects with .source_term, .target_term
            check_tags: Check for missing/altered tags.
            check_numbers: Check for number consistency.
            check_glossary: Check for glossary term violations.
            check_empty: Check for empty/untranslated segments.
            check_punctuation: Check for trailing punctuation differences.

        Returns:
            list[QAIssue]: List of quality issues found.
        """
        issues = []

        for seg in segments:
            source = seg.source_text or ''
            target = seg.target_text or ''
            seg_id = seg.id if hasattr(seg, 'id') else 0
            seg_idx = seg.index if hasattr(seg, 'index') else 0

            if check_empty:
                issues.extend(self._check_empty(seg_id, seg_idx, source, target))

            # Only run other checks if we have both source and target
            if not source or not target:
                continue

            if check_tags:
                issues.extend(self._check_tags(seg_id, seg_idx, source, target))

            if check_numbers:
                issues.extend(self._check_numbers(seg_id, seg_idx, source, target))

            if check_glossary and glossary_terms:
                issues.extend(self._check_glossary(
                    seg_id, seg_idx, source, target, glossary_terms
                ))

            if check_punctuation:
                issues.extend(self._check_punctuation(seg_id, seg_idx, source, target))

        return issues

    def _check_empty(self, seg_id, seg_idx, source, target):
        """Check for empty or untranslated segments."""
        issues = []
        if source and (not target or not target.strip()):
            issues.append(QAIssue(
                segment_id=seg_id,
                segment_index=seg_idx,
                issue_type='empty_translation',
                severity='warning',
                message="Segment non traduit.",
                source_text=source,
                target_text=target,
            ))
        return issues

    def _check_tags(self, seg_id, seg_idx, source, target):
        """Check for missing or altered tags."""
        issues = []
        tag_errors = self.tag_manager.validate_tags(source, target)

        for err in tag_errors:
            issues.append(QAIssue(
                segment_id=seg_id,
                segment_index=seg_idx,
                issue_type='missing_tag' if err.error_type == 'missing' else 'extra_tag',
                severity='error',
                message=err.message,
                source_text=source,
                target_text=target,
            ))
        return issues

    def _check_numbers(self, seg_id, seg_idx, source, target):
        """Check that numbers in source are also present in target."""
        issues = []
        source_numbers = set(re.findall(r'\d+(?:[.,]\d+)*', source))
        target_numbers = set(re.findall(r'\d+(?:[.,]\d+)*', target))

        missing = source_numbers - target_numbers
        if missing:
            issues.append(QAIssue(
                segment_id=seg_id,
                segment_index=seg_idx,
                issue_type='number_mismatch',
                severity='warning',
                message=f"Nombre(s) manquant(s) dans la traduction : {', '.join(sorted(missing))}",
                source_text=source,
                target_text=target,
            ))
        return issues

    def _check_glossary(self, seg_id, seg_idx, source, target, glossary_terms):
        """Check that glossary terms are respected in translations."""
        issues = []

        for term in glossary_terms:
            src_term = term.source_term if hasattr(term, 'source_term') else term.get('source_term', '')
            tgt_term = term.target_term if hasattr(term, 'target_term') else term.get('target_term', '')

            if not src_term or not tgt_term:
                continue

            # Check if source term appears in source text
            if src_term.lower() in source.lower():
                # Check if target term appears in target text
                if tgt_term.lower() not in target.lower():
                    issues.append(QAIssue(
                        segment_id=seg_id,
                        segment_index=seg_idx,
                        issue_type='glossary_violation',
                        severity='warning',
                        message=f"Terme du glossaire non respecté : "
                                f"'{src_term}' devrait être traduit par '{tgt_term}'.",
                        source_text=source,
                        target_text=target,
                    ))
        return issues

    def _check_punctuation(self, seg_id, seg_idx, source, target):
        """Check that trailing punctuation matches between source and target."""
        issues = []

        source_stripped = source.rstrip()
        target_stripped = target.rstrip()

        if not source_stripped or not target_stripped:
            return issues

        # Get the last punctuation character
        source_end = source_stripped[-1] if source_stripped else ''
        target_end = target_stripped[-1] if target_stripped else ''

        # Define equivalent punctuation pairs
        equivalents = {
            '.': {'.', '。'},
            '!': {'!', '！'},
            '?': {'?', '？'},
            '。': {'.', '。'},
            '！': {'!', '！'},
            '？': {'?', '？'},
        }

        # Only check if source ends with punctuation
        if source_end in equivalents:
            valid_targets = equivalents[source_end]
            if target_end not in valid_targets:
                issues.append(QAIssue(
                    segment_id=seg_id,
                    segment_index=seg_idx,
                    issue_type='punctuation_mismatch',
                    severity='info',
                    message=f"Ponctuation finale différente : "
                            f"source='{source_end}' vs cible='{target_end}'.",
                    source_text=source,
                    target_text=target,
                ))
        return issues

    def get_summary(self, issues):
        """
        Generate a summary of QA check results.

        Args:
            issues: list[QAIssue]

        Returns:
            dict: Summary with counts by type and severity.
        """
        summary = {
            'total': len(issues),
            'by_severity': {'error': 0, 'warning': 0, 'info': 0},
            'by_type': {},
        }

        for issue in issues:
            summary['by_severity'][issue.severity] = \
                summary['by_severity'].get(issue.severity, 0) + 1
            summary['by_type'][issue.issue_type] = \
                summary['by_type'].get(issue.issue_type, 0) + 1

        return summary
