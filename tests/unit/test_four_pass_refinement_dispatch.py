import pytest


@pytest.mark.asyncio
async def test_refine_chunks_routes_opted_in_jobs_through_three_refinement_passes(monkeypatch):
    import src.core.translator as translator

    calls = []

    async def fake_four_pass(**kwargs):
        calls.append(kwargs)
        return ["polished"]

    monkeypatch.setattr(translator, "_refine_chunks_four_pass", fake_four_pass)

    result = await translator.refine_chunks(
        translated_chunks=["draft"],
        original_chunks=[{"main_content": "draft"}],
        target_language="French",
        model_name="test-model",
        api_endpoint="http://localhost",
        prompt_options={"four_pass_refinement": True},
    )

    assert result == ["polished"]
    assert len(calls) == 1
    assert calls[0]["prompt_options"]["four_pass_refinement"] is True

