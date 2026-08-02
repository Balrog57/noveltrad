"""
Unit tests for the Poe provider's bot-default overrides (reasoning, web search).

Poe advertises a different set of knobs per bot in the `parameters` array of
/v1/models and rejects any knob a bot does not advertise (HTTP 400), so the
overrides are derived from that schema. These tests pin the mapping using the
real schemas returned by the API; the live behaviour is covered by
tests/standalone/manual_poe_reasoning.py.
"""

import pytest

from src.core.llm.providers.poe import PoeProvider


def _provider(model, disable_thinking=True, disable_web_search=False):
    return PoeProvider(
        api_key="sk-xxxxxxxx",
        model=model,
        disable_thinking=disable_thinking,
        disable_web_search=disable_web_search,
    )


# Real `parameters` payloads as returned by GET https://api.poe.com/v1/models
WEB_SEARCH = {
    "name": "web_search",
    "schema": {"type": "boolean"},
    "default_value": False,
}

WEB_SEARCH_ON = {
    "name": "web_search",
    "schema": {"type": "boolean"},
    "default_value": True,
}

GEMINI_36_FLASH = [
    WEB_SEARCH_ON,
    {
        "name": "thinking_level",
        "schema": {"enum": ["minimal", "low", "medium", "high"]},
        "default_value": "medium",
    },
]

GEMINI_31_PRO = [
    {
        "name": "thinking_level",
        "schema": {"enum": ["low", "high"]},
        "default_value": "low",
    },
    WEB_SEARCH,
]

CLAUDE_HAIKU_45 = [
    {
        "name": "thinking_budget",
        "schema": {"type": "number", "minimum": 0, "maximum": 63999},
        "default_value": 0,
    },
    WEB_SEARCH,
]

CLAUDE_SONNET_46 = [
    WEB_SEARCH,
    {
        "name": "output_effort",
        "schema": {"enum": ["max", "high", "medium", "low", "none"]},
        "default_value": "medium",
    },
]

GPT_54 = [
    WEB_SEARCH,
    {
        "name": "reasoning_effort",
        "schema": {"enum": ["none", "low", "medium", "high", "xhigh"]},
        "default_value": "none",
    },
    {"name": "verbosity", "schema": {"enum": ["low", "medium", "high"]}},
]

GROK_45 = [
    WEB_SEARCH_ON,
    {
        "name": "reasoning_effort",
        "schema": {"enum": ["low", "medium", "high"]},
        "default_value": "high",
    },
]

GLM_52 = [
    {
        "name": "enable_thinking",
        "schema": {"type": "boolean"},
        "default_value": True,
    },
]


@pytest.mark.parametrize(
    "advertised, expected",
    [
        # Enum knobs: least-thinking advertised value wins
        (GEMINI_36_FLASH, {"thinking_level": "minimal"}),
        (GEMINI_31_PRO, {"thinking_level": "low"}),  # no "minimal" offered
        (GPT_54, {"reasoning_effort": "none"}),
        (GROK_45, {"reasoning_effort": "low"}),  # no "none" offered
        # Numeric budget: schema minimum
        (CLAUDE_HAIKU_45, {"thinking_budget": 0}),
        # Boolean toggle: off
        (GLM_52, {"enable_thinking": False}),
        # No reasoning knob advertised (e.g. gpt-4o): send nothing
        ([], {}),
        ([WEB_SEARCH], {}),
        # output_effort caps the whole answer, not just reasoning: leave it be
        (CLAUDE_SONNET_46, {}),
    ],
)
def test_picks_lowest_advertised_reasoning_setting(advertised, expected):
    assert _provider("any-bot")._pick_bot_overrides(advertised) == expected


def test_unknown_enum_values_are_not_invented():
    """A knob whose enum offers none of our candidates must be left alone."""
    advertised = [
        {
            "name": "reasoning_effort",
            "schema": {"enum": ["medium", "high", "xhigh"]},
            "default_value": "medium",
        }
    ]
    assert _provider("any-bot")._pick_bot_overrides(advertised) == {}


def test_budget_minimum_defaults_to_zero_when_schema_omits_it():
    advertised = [{"name": "thinking_budget", "schema": {"type": "number"}}]
    assert _provider("any-bot")._pick_bot_overrides(advertised) == {
        "thinking_budget": 0
    }


@pytest.mark.parametrize(
    "advertised, expected",
    [
        (GEMINI_36_FLASH, {"thinking_level": "minimal", "web_search": False}),
        (GROK_45, {"web_search": False, "reasoning_effort": "low"}),
        # Same feature under another name (qwen bots)
        ([{"name": "enable_web_search", "schema": {"type": "boolean"},
           "default_value": True}], {"enable_web_search": False}),
        # Bot without a retrieval knob: send nothing
        (GLM_52, {"enable_thinking": False}),
    ],
)
def test_web_search_is_turned_off_when_advertised(advertised, expected):
    provider = _provider("any-bot", disable_web_search=True)
    assert provider._pick_bot_overrides(advertised) == expected


def test_each_flag_only_touches_its_own_knobs():
    provider = _provider("any-bot", disable_thinking=False, disable_web_search=True)
    assert provider._pick_bot_overrides(GEMINI_36_FLASH) == {"web_search": False}

    provider = _provider("any-bot", disable_thinking=True, disable_web_search=False)
    assert provider._pick_bot_overrides(GEMINI_36_FLASH) == {"thinking_level": "minimal"}


@pytest.mark.asyncio
async def test_opting_out_of_both_sends_nothing_and_skips_the_catalog(monkeypatch):
    """Opting out must not even fetch the model catalog."""
    provider = _provider(
        "gemini-3.6-flash", disable_thinking=False, disable_web_search=False
    )

    async def fail(*args, **kwargs):
        raise AssertionError("catalog must not be fetched when opted out")

    monkeypatch.setattr(provider, "_load_model_parameters", fail)
    assert await provider._get_bot_overrides() == {}


@pytest.mark.asyncio
async def test_overrides_are_resolved_once_per_model(monkeypatch):
    calls = []

    async def catalog():
        calls.append(1)
        return {"gemini-3.6-flash": GEMINI_36_FLASH}

    monkeypatch.setattr(PoeProvider, "_bot_overrides", {})
    provider = _provider("gemini-3.6-flash")
    monkeypatch.setattr(provider, "_load_model_parameters", catalog)

    first = await provider._get_bot_overrides()
    second = await provider._get_bot_overrides()

    assert first == second == {"thinking_level": "minimal"}
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_cache_is_not_shared_between_providers_with_different_flags(monkeypatch):
    """The flags decide the result, so they must be part of the cache key."""
    async def catalog():
        return {"gemini-3.6-flash": GEMINI_36_FLASH}

    monkeypatch.setattr(PoeProvider, "_bot_overrides", {})

    thinking_only = _provider("gemini-3.6-flash")
    monkeypatch.setattr(thinking_only, "_load_model_parameters", catalog)
    both = _provider("gemini-3.6-flash", disable_web_search=True)
    monkeypatch.setattr(both, "_load_model_parameters", catalog)

    assert await thinking_only._get_bot_overrides() == {"thinking_level": "minimal"}
    assert await both._get_bot_overrides() == {
        "thinking_level": "minimal",
        "web_search": False,
    }


@pytest.mark.asyncio
async def test_unreachable_catalog_leaves_the_bot_default(monkeypatch):
    """An unreachable catalog means "unknown", not "no parameters"."""
    monkeypatch.setattr(PoeProvider, "_bot_overrides", {})
    provider = _provider("gemini-3.6-flash")

    async def unreachable():
        return None

    monkeypatch.setattr(provider, "_load_model_parameters", unreachable)

    assert await provider._get_bot_overrides() == {}
    # Nothing cached, so a later call can still resolve the override
    assert PoeProvider._bot_overrides == {}
