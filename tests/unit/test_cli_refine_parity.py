"""CLI --refine must call refine_file after translate, never in-pipeline refine."""
import argparse
from pathlib import Path

import pytest

import translate


def _args(**overrides):
    defaults = dict(
        input="book.txt",
        output="book_fr.txt",
        source_lang="English",
        target_lang="French",
        model="llama3",
        provider="ollama",
        api_endpoint="http://localhost:11434",
        gemini_api_key="",
        openai_api_key="",
        openrouter_api_key="",
        mistral_api_key="",
        deepseek_api_key="",
        poe_api_key="",
        nim_api_key="",
        anthropic_api_key=None,
        xai_api_key=None,
        opencode_api_key=None,
        opencodego_api_key=None,
        ollamacloud_api_key=None,
        parallel=1,
        refine=False,
        refine_only=False,
        refine_plus=False,
        refine_plus_only=False,
        text_cleanup=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_cli_prompt_options_never_set_in_pipeline_refine():
    options = translate.build_cli_prompt_options(_args(refine=True, text_cleanup=True))
    assert options["refine"] is False
    assert options["text_cleanup"] is True
    assert options["preserve_technical_content"] is True
    assert options["refine_plus"] is False


@pytest.mark.asyncio
async def test_cli_refine_calls_refine_file_after_translate(monkeypatch, tmp_path):
    src = tmp_path / "book.txt"
    out = tmp_path / "book_fr.txt"
    src.write_text("Once upon a time.", encoding="utf-8")
    calls = []

    async def fake_translate_file(**kwargs):
        calls.append(("translate", kwargs))
        Path(kwargs["output_filepath"]).write_text("translated", encoding="utf-8")
        return True

    async def fake_refine_file(**kwargs):
        calls.append(("refine", kwargs))
        return True

    monkeypatch.setattr(translate, "translate_file", fake_translate_file)
    monkeypatch.setattr(translate, "refine_file", fake_refine_file)

    args = _args(input=str(src), output=str(out), refine=True)
    prompt_options = translate.build_cli_prompt_options(args)
    mode = await translate.run_cli_job(
        args, prompt_options, checkpoint_manager=None, translation_id="cli_test",
        log_callback=None, stats_callback=None,
    )

    assert mode == "translate_refine"
    assert [name for name, _ in calls] == ["translate", "refine"]
    assert calls[0][1]["prompt_options"]["refine"] is False
    assert calls[1][1]["source_filepath"] == str(src)
    assert calls[1][1]["input_filepath"] == str(out)
    assert calls[1][1]["prompt_options"]["refine"] is False


@pytest.mark.asyncio
async def test_cli_without_refine_does_not_call_refine_file(monkeypatch, tmp_path):
    src = tmp_path / "book.txt"
    out = tmp_path / "book_fr.txt"
    src.write_text("Hello.", encoding="utf-8")
    calls = []

    async def fake_translate_file(**kwargs):
        calls.append("translate")
        Path(kwargs["output_filepath"]).write_text("translated", encoding="utf-8")
        return True

    async def fake_refine_file(**kwargs):
        calls.append("refine")
        return True

    monkeypatch.setattr(translate, "translate_file", fake_translate_file)
    monkeypatch.setattr(translate, "refine_file", fake_refine_file)

    args = _args(input=str(src), output=str(out), refine=False)
    mode = await translate.run_cli_job(
        args, translate.build_cli_prompt_options(args),
        checkpoint_manager=None, translation_id="cli_test",
        log_callback=None, stats_callback=None,
    )

    assert mode == "translate"
    assert calls == ["translate"]


@pytest.mark.asyncio
async def test_cli_refine_only_skips_translate(monkeypatch, tmp_path):
    src = tmp_path / "book.txt"
    out = tmp_path / "book_refined.txt"
    src.write_text("Already translated.", encoding="utf-8")
    calls = []

    async def fake_translate_file(**kwargs):
        calls.append(("translate", kwargs))
        return True

    async def fake_refine_file(**kwargs):
        calls.append(("refine", kwargs))
        return True

    monkeypatch.setattr(translate, "translate_file", fake_translate_file)
    monkeypatch.setattr(translate, "refine_file", fake_refine_file)

    args = _args(input=str(src), output=str(out), refine_only=True)
    mode = await translate.run_cli_job(
        args, translate.build_cli_prompt_options(args),
        checkpoint_manager=None, translation_id="cli_test",
        log_callback=None, stats_callback=None,
    )

    assert mode == "refine-only"
    assert [name for name, _ in calls] == ["refine"]
    assert calls[0][1]["input_filepath"] == str(src)
    assert calls[0][1]["source_filepath"] == str(src)
    assert calls[0][1]["prompt_options"]["refine"] is False


@pytest.mark.asyncio
async def test_cli_refine_raises_when_refine_file_returns_false(monkeypatch, tmp_path):
    src = tmp_path / "book.txt"
    out = tmp_path / "book_fr.txt"
    src.write_text("Hello.", encoding="utf-8")

    async def fake_translate_file(**kwargs):
        Path(kwargs["output_filepath"]).write_text("translated", encoding="utf-8")
        return True

    async def fake_refine_file(**kwargs):
        return False

    monkeypatch.setattr(translate, "translate_file", fake_translate_file)
    monkeypatch.setattr(translate, "refine_file", fake_refine_file)

    args = _args(input=str(src), output=str(out), refine=True)
    with pytest.raises(RuntimeError, match="Refinement adapter did not produce a valid output"):
        await translate.run_cli_job(
            args, translate.build_cli_prompt_options(args),
            checkpoint_manager=None, translation_id="cli_test",
            log_callback=None, stats_callback=None,
        )


@pytest.mark.asyncio
async def test_cli_refine_plus_sets_prompt_flag_and_calls_refine_file(monkeypatch, tmp_path):
    src = tmp_path / "book.txt"
    out = tmp_path / "book_fr.txt"
    src.write_text("Once upon a time.", encoding="utf-8")
    calls = []

    async def fake_translate_file(**kwargs):
        calls.append(("translate", kwargs))
        Path(kwargs["output_filepath"]).write_text("translated", encoding="utf-8")
        return True

    async def fake_refine_file(**kwargs):
        calls.append(("refine", kwargs))
        return True

    monkeypatch.setattr(translate, "translate_file", fake_translate_file)
    monkeypatch.setattr(translate, "refine_file", fake_refine_file)

    args = _args(input=str(src), output=str(out), refine_plus=True)
    prompt_options = translate.build_cli_prompt_options(args)
    assert prompt_options["refine"] is False
    assert prompt_options["refine_plus"] is True
    mode = await translate.run_cli_job(
        args, prompt_options, checkpoint_manager=None, translation_id="cli_test",
        log_callback=None, stats_callback=None,
    )

    assert mode == "translate_refine_plus"
    assert [name for name, _ in calls] == ["translate", "refine"]
    assert calls[1][1]["prompt_options"]["refine_plus"] is True
    assert calls[1][1]["prompt_options"]["refine"] is False


@pytest.mark.asyncio
async def test_cli_refine_plus_only_skips_translate(monkeypatch, tmp_path):
    src = tmp_path / "book.txt"
    out = tmp_path / "book_refined.txt"
    src.write_text("Already translated.", encoding="utf-8")
    calls = []

    async def fake_translate_file(**kwargs):
        calls.append(("translate", kwargs))
        return True

    async def fake_refine_file(**kwargs):
        calls.append(("refine", kwargs))
        return True

    monkeypatch.setattr(translate, "translate_file", fake_translate_file)
    monkeypatch.setattr(translate, "refine_file", fake_refine_file)

    args = _args(input=str(src), output=str(out), refine_plus_only=True)
    mode = await translate.run_cli_job(
        args, translate.build_cli_prompt_options(args),
        checkpoint_manager=None, translation_id="cli_test",
        log_callback=None, stats_callback=None,
    )

    assert mode == "refine-plus-only"
    assert [name for name, _ in calls] == ["refine"]
    assert calls[0][1]["prompt_options"]["refine_plus"] is True
    assert calls[0][1]["prompt_options"]["refine"] is False


def test_cli_refine_and_refine_plus_are_documented_as_exclusive():
    source = Path(__file__).resolve().parents[2] / "translate.py"
    text = source.read_text(encoding="utf-8")
    assert "Use only one of --refine, --refine-only, --refine-plus, --refine-plus-only." in text
