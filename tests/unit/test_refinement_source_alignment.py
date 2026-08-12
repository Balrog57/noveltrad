import pytest
import importlib

from src.core.refine import txt_refiner

refine_file_module = importlib.import_module("src.core.adapters.refine_file")


@pytest.mark.asyncio
async def test_txt_refiner_attaches_original_source_to_each_target_chunk(
    tmp_path, monkeypatch
):
    source_path = tmp_path / "source.txt"
    translated_path = tmp_path / "translated.txt"
    output_path = tmp_path / "refined.txt"
    source_path.write_text("Source paragraph one.\n\nSource paragraph two.", encoding="utf-8")
    translated_path.write_text("Premier paragraphe.\n\nDeuxieme paragraphe.", encoding="utf-8")
    captured = {}

    async def fake_refine_chunks(**kwargs):
        captured.update(kwargs)
        return kwargs["translated_chunks"]

    async def fake_write(parts, chunks, output_filepath, log_callback=None):
        return True

    monkeypatch.setattr(txt_refiner, "refine_chunks", fake_refine_chunks)
    monkeypatch.setattr(txt_refiner, "_write_refined_output", fake_write)

    result = await txt_refiner.refine_txt_file(
        input_filepath=str(translated_path),
        output_filepath=str(output_path),
        source_filepath=str(source_path),
        target_language="French",
        model_name="test-model",
        cli_api_endpoint="https://example.test/v1",
        prompt_options={"four_pass_refinement": True},
    )

    assert result is True
    chunks = captured["original_chunks"]
    assert [chunk["source_text"] for chunk in chunks] == [
        "Source paragraph one.\n\nSource paragraph two.",
    ]


@pytest.mark.asyncio
async def test_refine_file_forwards_source_filepath(monkeypatch, tmp_path):
    captured = {}

    async def fake_refine_txt_file(**kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(refine_file_module, "detect_file_type", lambda _: "txt")
    monkeypatch.setattr(
        "src.core.refine.txt_refiner.refine_txt_file", fake_refine_txt_file
    )

    result = await refine_file_module.refine_file(
        input_filepath=str(tmp_path / "translated.txt"),
        output_filepath=str(tmp_path / "out.txt"),
        source_filepath=str(tmp_path / "source.txt"),
        target_language="French",
        model_name="test-model",
        llm_provider="ollama",
    )

    assert result is True
    assert captured["source_filepath"].endswith("source.txt")
