"""
Chatterbox has no regional language variants: it only knows base codes such
as "pt". The UI, however, offers "Portuguese (Brazil)" / "Portuguese
(Portugal)" and the codes pt-br / pt-pt, so the resolver must fold every
regional form back onto the base code instead of silently falling back to
English.
"""
import pytest

from src.tts.tts_config import TTSConfig


@pytest.mark.parametrize("language,expected", [
    # Base codes and names still resolve as before
    ("pt", "pt"),
    ("Portuguese", "pt"),
    ("en", "en"),
    ("French", "fr"),
    # Regional codes fold onto the base code
    ("pt-br", "pt"),
    ("pt-pt", "pt"),
    ("PT-BR", "pt"),
    ("en_US", "en"),
    # Regional names fold onto the base code
    ("Portuguese (Brazil)", "pt"),
    ("Portuguese (Portugal)", "pt"),
    # Unsupported input still falls back to English
    ("Klingon", "en"),
    ("", "en"),
])
def test_get_chatterbox_voice_resolves_regional_variants(language, expected):
    assert TTSConfig().get_chatterbox_voice(language) == expected


def test_get_chatterbox_voice_falls_back_to_target_language():
    config = TTSConfig(target_language="Portuguese (Portugal)")
    assert config.get_chatterbox_voice() == "pt"
