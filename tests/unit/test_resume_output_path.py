"""Unit tests for `resolve_output_path` (src/api/handlers.py).

A fresh job must never overwrite an existing file — it gets a " (1)" suffix.
A resume must do the opposite: it rebuilds the whole document from the
checkpoint, so it overwrites the file the previous pass wrote instead of
dropping a second, differently-named copy next to the stale one (and instead of
climbing " (2)", " (3)"… on every further retry).
"""
import os

from src.api.handlers import resolve_output_path


def test_fresh_job_without_collision_keeps_the_requested_name(tmp_path):
    assert resolve_output_path(str(tmp_path), 'book.epub', False) == \
        os.path.join(str(tmp_path), 'book.epub')


def test_fresh_job_with_collision_still_gets_the_suffix(tmp_path):
    (tmp_path / 'book.epub').write_text('stale', encoding='utf-8')
    assert resolve_output_path(str(tmp_path), 'book.epub', False) == \
        str(tmp_path / 'book (1).epub')


def test_fresh_job_climbs_past_existing_suffixes(tmp_path):
    (tmp_path / 'book.epub').write_text('stale', encoding='utf-8')
    (tmp_path / 'book (1).epub').write_text('stale', encoding='utf-8')
    assert resolve_output_path(str(tmp_path), 'book.epub', False) == \
        str(tmp_path / 'book (2).epub')


def test_resume_overwrites_the_existing_output(tmp_path):
    """The measured defect: the retry used to write `book (1).epub`."""
    (tmp_path / 'book.epub').write_text('half translated', encoding='utf-8')
    assert resolve_output_path(str(tmp_path), 'book.epub', True) == \
        os.path.join(str(tmp_path), 'book.epub')


def test_resume_does_not_climb_when_the_name_already_carries_a_suffix(tmp_path):
    """The auto-resume path reuses the in-memory config, which may already hold
    a `(1)` name from the pre-fix behavior. It must stay on that file."""
    (tmp_path / 'book (1).epub').write_text('half translated', encoding='utf-8')
    assert resolve_output_path(str(tmp_path), 'book (1).epub', True) == \
        os.path.join(str(tmp_path), 'book (1).epub')


def test_resume_with_deleted_previous_output_returns_the_same_path(tmp_path):
    """The user deleted the stale file: the resume recreates it, no crash."""
    assert not (tmp_path / 'book.epub').exists()
    assert resolve_output_path(str(tmp_path), 'book.epub', True) == \
        os.path.join(str(tmp_path), 'book.epub')


def test_repeated_resumes_stay_on_one_file(tmp_path):
    """Three retries in a row must not leave `(1)`, `(2)`, `(3)` behind."""
    target = os.path.join(str(tmp_path), 'book.epub')
    for _ in range(3):
        resolved = resolve_output_path(str(tmp_path), 'book.epub', True)
        assert resolved == target
        # Simulate the run writing its output.
        with open(resolved, 'w', encoding='utf-8') as handle:
            handle.write('rebuilt')
    assert [p.name for p in tmp_path.iterdir()] == ['book.epub']
