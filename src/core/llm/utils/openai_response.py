"""Parse OpenAI-compatible chat completions and decide empty-response retries.

Aggregator routers (Nexum/Dialagram, OpenRouter, OpenCode, …) frequently
return HTTP 200 with no usable text: empty ``choices``, ``content: null``,
a content-parts array, or a 0-token drop. Those are transient and worth
retrying. An explicit refusal / content-filter is not.
"""

from typing import Any, Dict, Mapping

# finish_reason values that mean "do not retry, this will not recover"
_REFUSAL_FINISH_REASONS = frozenset({
    "content_filter",
    "content_filtered",
    "safety",
    "recitation",
})


def stringify_message_content(content: Any) -> str:
    """Turn ``message.content`` into a plain string.

    Handles ``null``, a string, or a list of parts (multimodal / reasoning
    models). Reasoning/thinking parts are skipped so chain-of-thought is
    never treated as the translation.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                if part:
                    parts.append(part)
                continue
            if not isinstance(part, dict):
                continue
            ptype = str(part.get("type") or "").lower()
            if ptype in ("reasoning", "thinking"):
                continue
            text = part.get("text") or part.get("content") or ""
            if text:
                parts.append(str(text))
        return "".join(parts)
    return str(content)


def parse_chat_completion(response_json: Mapping[str, Any] | None) -> Dict[str, Any]:
    """Extract text, usage, and retry hints from a chat-completions payload.

    Returns a dict with:
        text, finish_reason, refusal, prompt_tokens, completion_tokens,
        error_message, empty_choices, is_explicit_refusal
    """
    payload: Mapping[str, Any] = response_json or {}
    error = payload.get("error")
    error_message = ""
    if isinstance(error, dict):
        error_message = str(error.get("message") or error.get("code") or "")
    elif error:
        error_message = str(error)

    usage = payload.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return {
            "text": "",
            "finish_reason": "",
            "refusal": "",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "error_message": error_message,
            "empty_choices": True,
            "is_explicit_refusal": False,
            "was_truncated": False,
        }

    choice = choices[0] if isinstance(choices[0], dict) else {}
    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
    finish_reason = str(choice.get("finish_reason") or choice.get("finishReason") or "")
    refusal = stringify_message_content(message.get("refusal"))
    text = stringify_message_content(message.get("content"))
    if not text:
        text = stringify_message_content(choice.get("text"))

    finish_l = finish_reason.lower()
    is_explicit_refusal = bool(refusal) or finish_l in _REFUSAL_FINISH_REASONS
    was_truncated = finish_l in ("length", "max_tokens")

    return {
        "text": text,
        "finish_reason": finish_reason,
        "refusal": refusal,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "error_message": error_message,
        "empty_choices": False,
        "is_explicit_refusal": is_explicit_refusal,
        "was_truncated": was_truncated,
    }


def should_retry_empty_completion(
    parsed: Mapping[str, Any],
    attempt: int,
    max_attempts: int,
) -> bool:
    """True when an empty/malformed 200 is worth another HTTP call."""
    if attempt + 1 >= max_attempts:
        return False
    if parsed.get("is_explicit_refusal"):
        return False
    text = (parsed.get("text") or "").strip()
    if text:
        return False
    # Empty choices, 0-token drops, billed-but-empty reasoning, and 200-with-
    # error bodies are all treated as transient router/model glitches.
    return True


def empty_retry_reason(parsed: Mapping[str, Any]) -> str:
    """Short diagnostic for logs."""
    if parsed.get("is_explicit_refusal"):
        reason = parsed.get("finish_reason") or "refusal"
        return f"content filtered ({reason})"
    if parsed.get("empty_choices"):
        err = parsed.get("error_message")
        return f"empty choices{f': {err}' if err else ''}"
    tokens = parsed.get("completion_tokens") or 0
    finish = parsed.get("finish_reason") or "none"
    return f"{tokens} completion tokens, finish_reason={finish}"
