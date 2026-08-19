"""
Unit tests for translator fallback context isolation (issue #170 fix)
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock

from src.core.translator import _make_llm_request_with_adaptive_context
from src.core.llm.base import LLMResponse


class TestTranslatorFallbackContext:
    """Test that raw fallback responses do not contaminate chunk context chain."""

    @pytest.fixture(autouse=True)
    def no_sleep(self, monkeypatch):
        monkeypatch.setattr("src.core.translator.asyncio.sleep", AsyncMock())

    @pytest.fixture
    def mock_llm_client(self):
        client = Mock()
        client.extract_translation = Mock(side_effect=lambda text: None)
        return client

    @pytest.mark.asyncio
    async def test_successful_extraction_has_no_fallback_flag(self, mock_llm_client):
        """When tags are found, was_fallback must be False."""
        mock_llm_client.generate = AsyncMock(return_value=LLMResponse(
            content="<TRANSLATION>Bonjour</TRANSLATION>",
            prompt_tokens=10,
            completion_tokens=5,
            context_used=15,
            context_limit=2048,
            was_truncated=False,
        ))
        mock_llm_client.extract_translation = Mock(return_value="Bonjour")

        translated, _, response = await _make_llm_request_with_adaptive_context(
            main_content="Hello",
            context_before="",
            context_after="",
            previous_translation_context="",
            source_language="English",
            target_language="French",
            model="test-model",
            llm_client=mock_llm_client,
            log_callback=None,
            has_placeholders=False,
        )

        assert translated == "Bonjour"
        assert response.was_fallback is False

    @pytest.mark.asyncio
    async def test_plain_text_fallback_sets_fallback_flag(self, mock_llm_client):
        """When extraction fails for plain text, was_fallback must be True."""
        # Response must NOT contain the input text exactly, otherwise echo detection rejects it
        mock_llm_client.generate = AsyncMock(return_value=LLMResponse(
            content="Here is the translation: Bonjour le monde",
            prompt_tokens=10,
            completion_tokens=5,
            context_used=15,
            context_limit=2048,
            was_truncated=False,
        ))

        translated, _, response = await _make_llm_request_with_adaptive_context(
            main_content="Hello world",
            context_before="",
            context_after="",
            previous_translation_context="",
            source_language="English",
            target_language="French",
            model="test-model",
            llm_client=mock_llm_client,
            log_callback=None,
            has_placeholders=False,
        )

        assert translated == "Here is the translation: Bonjour le monde"
        assert response.was_fallback is True

    @pytest.mark.asyncio
    async def test_epub_no_fallback_on_failure(self, mock_llm_client):
        """When has_placeholders=True, failed extraction must return None (no raw fallback)."""
        mock_llm_client.generate = AsyncMock(return_value=LLMResponse(
            content="Here is the translation: Hello world",
            prompt_tokens=10,
            completion_tokens=5,
            context_used=15,
            context_limit=2048,
            was_truncated=False,
        ))

        translated, _, response = await _make_llm_request_with_adaptive_context(
            main_content="Hello world",
            context_before="",
            context_after="",
            previous_translation_context="",
            source_language="English",
            target_language="French",
            model="test-model",
            llm_client=mock_llm_client,
            log_callback=None,
            has_placeholders=True,
        )

        assert translated is None
        assert response.was_fallback is False

    @pytest.mark.asyncio
    async def test_epub_salvages_unclosed_translation_tag(self, mock_llm_client):
        """One-pass EPUB must keep an unclosed <TRANSLATION> body, like refine."""
        from src.config import TRANSLATE_TAG_IN, TRANSLATE_TAG_OUT
        from src.core.llm.utils.extraction import TranslationExtractor

        mock_llm_client.generate = AsyncMock(return_value=LLMResponse(
            content=(
                "<TRANSLATION> «C'est tout — pour une civilisation "
                "dotée du meilleur réseau d'information"
            ),
            prompt_tokens=10,
            completion_tokens=40,
            context_used=50,
            context_limit=2048,
            was_truncated=False,
        ))
        mock_llm_client.extract_translation = TranslationExtractor(
            TRANSLATE_TAG_IN, TRANSLATE_TAG_OUT
        ).extract

        translated, _, response = await _make_llm_request_with_adaptive_context(
            main_content="Das ist alles",
            context_before="",
            context_after="",
            previous_translation_context="",
            source_language="German",
            target_language="French",
            model="test-model",
            llm_client=mock_llm_client,
            log_callback=None,
            has_placeholders=True,
        )

        assert translated.startswith("«C'est tout")
        assert "<TRANSLATION>" not in translated
        assert response.was_fallback is False
        mock_llm_client.generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_context_manager_implicit_truncation_retry(self, mock_llm_client):
        """If response starts with <TRANSLATION> but has no closing tag, retry with larger context."""
        call_count = 0
        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return LLMResponse(
                    content="<TRANSLATION>\nPartial text without closing tag",
                    prompt_tokens=10,
                    completion_tokens=5,
                    context_used=15,
                    context_limit=2048,
                    was_truncated=True,
                )
            return LLMResponse(
                content="<TRANSLATION>Completed</TRANSLATION>",
                prompt_tokens=10,
                completion_tokens=5,
                context_used=15,
                context_limit=4096,
                was_truncated=False,
            )

        mock_llm_client.generate = side_effect
        # Second call succeeds
        mock_llm_client.extract_translation = Mock(side_effect=lambda text: None if "Partial" in text else "Completed")

        context_manager = Mock()
        context_manager.should_retry_with_larger_context = Mock(return_value=True)
        context_manager.increase_context = Mock()
        context_manager.get_context_size = Mock(return_value=4096)

        translated, _, response = await _make_llm_request_with_adaptive_context(
            main_content="Hello",
            context_before="",
            context_after="",
            previous_translation_context="",
            source_language="English",
            target_language="French",
            model="test-model",
            llm_client=mock_llm_client,
            log_callback=None,
            has_placeholders=False,
            context_manager=context_manager,
        )

        assert call_count == 2
        assert translated == "Completed"
        assert context_manager.increase_context.called


class TestEmptyResponseRetry:
    """Empty LLM bodies are retried instead of being treated as a refusal."""

    @pytest.mark.asyncio
    async def test_retries_empty_then_succeeds(self, monkeypatch):
        client = Mock()
        calls = {"n": 0}

        async def generate(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return LLMResponse(content="", prompt_tokens=10, completion_tokens=0)
            return LLMResponse(
                content="<TRANSLATION>Bonjour</TRANSLATION>",
                prompt_tokens=10,
                completion_tokens=5,
            )

        client.generate = generate
        client.extract_translation = Mock(return_value="Bonjour")
        monkeypatch.setattr("src.core.translator.asyncio.sleep", AsyncMock())
        monkeypatch.setattr("src.core.translator.MAX_TRANSLATION_ATTEMPTS", 2)

        translated, _, response = await _make_llm_request_with_adaptive_context(
            main_content="Hello",
            context_before="",
            context_after="",
            previous_translation_context="",
            source_language="English",
            target_language="French",
            model="test-model",
            llm_client=client,
            log_callback=None,
            has_placeholders=False,
        )

        assert calls["n"] == 2
        assert translated == "Bonjour"
        assert response.content.startswith("<TRANSLATION>")

    @pytest.mark.asyncio
    async def test_empty_exhausted_returns_none(self, monkeypatch):
        client = Mock()
        client.generate = AsyncMock(return_value=LLMResponse(
            content="", prompt_tokens=10, completion_tokens=0,
        ))
        client.extract_translation = Mock(return_value=None)
        monkeypatch.setattr("src.core.translator.asyncio.sleep", AsyncMock())
        monkeypatch.setattr("src.core.translator.MAX_TRANSLATION_ATTEMPTS", 2)

        translated, original, response = await _make_llm_request_with_adaptive_context(
            main_content="Hello",
            context_before="",
            context_after="",
            previous_translation_context="",
            source_language="English",
            target_language="French",
            model="test-model",
            llm_client=client,
            log_callback=None,
            has_placeholders=False,
        )

        assert translated is None
        assert original == "Hello"
        assert response.content == ""
        assert client.generate.await_count == 2


class TestRefinementEmptyResponse:
    @pytest.mark.asyncio
    async def test_empty_refine_keeps_draft_instead_of_blank(self, monkeypatch):
        from src.core.translator import _make_refinement_request

        client = Mock()
        client.make_request = AsyncMock(return_value=LLMResponse(
            content="", prompt_tokens=4, completion_tokens=0,
        ))
        client.extract_translation = Mock(return_value=None)
        monkeypatch.setattr("src.core.translator.asyncio.sleep", AsyncMock())
        monkeypatch.setattr("src.core.translator.MAX_TRANSLATION_ATTEMPTS", 2)

        refined, _ = await _make_refinement_request(
            draft_translation="Bonjour le monde",
            context_before="",
            context_after="",
            previous_refined_context="",
            target_language="French",
            model="test-model",
            llm_client=client,
            log_callback=None,
            has_placeholders=False,
        )

        assert refined is None
        assert client.make_request.await_count == 2

    @pytest.mark.asyncio
    async def test_truncated_empty_refine_keeps_draft_without_retry(self, monkeypatch):
        from src.core.translator import _make_refinement_request

        client = Mock()
        client.make_request = AsyncMock(return_value=LLMResponse(
            content="", prompt_tokens=4, completion_tokens=10178,
            was_truncated=True,
        ))
        client.extract_translation = Mock(return_value=None)
        monkeypatch.setattr("src.core.translator.asyncio.sleep", AsyncMock())
        monkeypatch.setattr("src.core.translator.MAX_TRANSLATION_ATTEMPTS", 5)

        refined, response = await _make_refinement_request(
            draft_translation="Bonjour le monde",
            context_before="",
            context_after="",
            previous_refined_context="",
            target_language="French",
            model="test-model",
            llm_client=client,
            log_callback=None,
            has_placeholders=False,
        )

        assert refined is None
        assert response.was_truncated is True
        assert client.make_request.await_count == 1

    @pytest.mark.asyncio
    async def test_unclosed_tag_keeps_refined_body(self, monkeypatch):
        from src.config import TRANSLATE_TAG_IN, TRANSLATE_TAG_OUT
        from src.core.llm.utils.extraction import TranslationExtractor
        from src.core.translator import _make_refinement_request

        client = Mock()
        client.make_request = AsyncMock(return_value=LLMResponse(
            content="<TRANSLATION>Le monde raffiné",
            prompt_tokens=4,
            completion_tokens=8,
            was_truncated=False,
        ))
        client.extract_translation = TranslationExtractor(
            TRANSLATE_TAG_IN, TRANSLATE_TAG_OUT
        ).extract
        monkeypatch.setattr("src.core.translator.asyncio.sleep", AsyncMock())

        refined, _ = await _make_refinement_request(
            draft_translation="Bonjour le monde",
            context_before="",
            context_after="",
            previous_refined_context="",
            target_language="French",
            model="test-model",
            llm_client=client,
            log_callback=None,
            has_placeholders=False,
        )

        assert refined == "Le monde raffiné"
        assert client.make_request.await_count == 1

