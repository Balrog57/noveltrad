"""UI 'Save to .env' must survive a Docker container recreate.

Compose injects LLM_PROVIDER=ollama and MAX_TOKENS_PER_CHUNK=450 into the
process environment. The project `.env` is not mounted into `/app`, so
writes there vanish on recreate. `data/` is a persistent volume.
"""
from pathlib import Path

import src.config as cfg


def test_primary_env_prefers_data_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    assert cfg.primary_env_file_path() == tmp_path / "data" / ".env"


def test_primary_env_falls_back_to_cwd_without_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cfg.primary_env_file_path() == tmp_path / ".env"


def test_env_files_to_update_mirrors_existing_cwd_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / ".env").write_text("LLM_PROVIDER=ollama\n", encoding="utf-8")
    paths = cfg.env_files_to_update()
    assert tmp_path / "data" / ".env" in paths
    assert tmp_path / ".env" in paths


def test_data_env_overrides_compose_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / ".env").write_text(
        "LLM_PROVIDER=opencode\nMAX_TOKENS_PER_CHUNK=800\nPARALLEL_TRANSLATIONS=4\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("MAX_TOKENS_PER_CHUNK", "450")
    monkeypatch.setenv("PARALLEL_TRANSLATIONS", "1")

    snapshot = (cfg.LLM_PROVIDER, cfg.MAX_TOKENS_PER_CHUNK, cfg.PARALLEL_TRANSLATIONS)
    try:
        cfg.load_env_files(override=True)
        cfg._apply_reloadable_env_settings()

        assert cfg.LLM_PROVIDER == "opencode"
        assert cfg.MAX_TOKENS_PER_CHUNK == 800
        assert cfg.PARALLEL_TRANSLATIONS == 4
    finally:
        cfg.LLM_PROVIDER, cfg.MAX_TOKENS_PER_CHUNK, cfg.PARALLEL_TRANSLATIONS = snapshot


def test_candidates_load_cwd_then_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / ".env").write_text("LLM_PROVIDER=openai\n", encoding="utf-8")
    (tmp_path / "data" / ".env").write_text("LLM_PROVIDER=opencode\n", encoding="utf-8")
    candidates = cfg.env_file_candidates()
    assert candidates[0] == tmp_path / ".env"
    assert candidates[-1] == tmp_path / "data" / ".env"
