from unittest.mock import patch
from pmao.llm import call_structured, call_text, LLMError

def test_call_text_returns_string():
    with patch("pmao.llm._run", return_value="status dashboard output"):
        result = call_text("show status", config_override="claude")
    assert result == "status dashboard output"

def test_call_structured_parses_json():
    with patch("pmao.llm._run", return_value='{"key": "value"}'):
        result = call_structured("extract json", config_override="claude")
    assert result == {"key": "value"}

def test_call_structured_strips_markdown_fences():
    raw = "```json\n{\"a\": 1}\n```"
    with patch("pmao.llm._run", return_value=raw):
        result = call_structured("extract", config_override="claude")
    assert result == {"a": 1}

def test_detect_backend_raises_when_none_found():
    with patch("shutil.which", return_value=None):
        from pmao.llm import LLMError, detect_backend
        try:
            detect_backend()
            assert False, "Should have raised"
        except LLMError:
            pass
