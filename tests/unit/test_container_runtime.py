"""Container detection and durable Custom_Instructions path."""
from pathlib import Path

from src.utils.container import running_in_container
from src.utils.custom_instructions import resolve_custom_instructions_dir


def test_running_in_container_false_without_dockerenv(monkeypatch):
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    assert running_in_container() is False


def test_resolve_dir_native_uses_project_folder(tmp_path, monkeypatch):
    monkeypatch.setattr("src.utils.container.running_in_container", lambda: False)
    (tmp_path / "data").mkdir()
    assert resolve_custom_instructions_dir(tmp_path) == tmp_path / "Custom_Instructions"


def test_resolve_dir_docker_uses_data_volume(tmp_path, monkeypatch):
    monkeypatch.setattr("src.utils.container.running_in_container", lambda: True)
    (tmp_path / "data").mkdir()
    assert resolve_custom_instructions_dir(tmp_path) == tmp_path / "data" / "Custom_Instructions"
