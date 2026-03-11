"""Tests for SupertonicEngine._preprocess_text"""

import pytest
from tts.supertonic_engine import SupertonicEngine


class TestPreprocessText:
    """Test text preprocessing logic"""

    def test_removes_bold_markdown(self):
        """Test removal of bold markdown (**text**)"""
        result = SupertonicEngine._preprocess_text("**bold text**")
        assert "**" not in result
        assert result.strip() == "bold text"

    def test_removes_italic_markdown(self):
        """Test removal of italic markdown (__text__)"""
        result = SupertonicEngine._preprocess_text("__italic text__")
        assert "__" not in result
        assert result.strip() == "italic text"

    def test_removes_strikethrough_markdown(self):
        """Test removal of strikethrough markdown (~~text~~)"""
        result = SupertonicEngine._preprocess_text("~~strikethrough~~")
        assert "~~" not in result

    def test_removes_code_backticks(self):
        """Test removal of backticks"""
        result = SupertonicEngine._preprocess_text("`code here`")
        assert "`" not in result
        assert "code here" in result

    def test_removes_http_urls(self):
        """Test removal of http:// URLs"""
        result = SupertonicEngine._preprocess_text("Check this http://example.com out")
        assert "http://" not in result
        assert "example.com" not in result
        assert "Check this" in result
        assert "out" in result

    def test_removes_https_urls(self):
        """Test removal of https:// URLs"""
        result = SupertonicEngine._preprocess_text("Visit https://example.com today")
        assert "https://" not in result
        assert "example.com" not in result

    def test_removes_www_urls(self):
        """Test removal of www. URLs"""
        result = SupertonicEngine._preprocess_text("See www.example.com for more")
        assert "www." not in result
        assert "example.com" not in result

    def test_collapses_multiple_spaces(self):
        """Test collapsing multiple spaces"""
        result = SupertonicEngine._preprocess_text("hello    world    test")
        assert "    " not in result
        assert result == "hello world test"

    def test_truncates_to_max_length(self):
        """Test truncation to 500 characters"""
        long_text = "a" * 600
        result = SupertonicEngine._preprocess_text(long_text)
        assert len(result) <= 503  # 500 + "..."
        assert result.endswith("...")

    def test_truncates_with_ellipsis(self):
        """Test that truncation adds ellipsis"""
        long_text = "hello world " * 50
        result = SupertonicEngine._preprocess_text(long_text)
        assert result.endswith("...")

    def test_does_not_truncate_short_text(self):
        """Test that short text doesn't get ellipsis"""
        short_text = "hello world"
        result = SupertonicEngine._preprocess_text(short_text)
        assert not result.endswith("...")

    def test_strips_whitespace(self):
        """Test removal of leading/trailing whitespace"""
        result = SupertonicEngine._preprocess_text("   hello world   ")
        assert result == "hello world"

    def test_empty_string(self):
        """Test handling of empty string"""
        result = SupertonicEngine._preprocess_text("")
        assert result == ""

    def test_only_whitespace(self):
        """Test handling of whitespace-only string"""
        result = SupertonicEngine._preprocess_text("   \n\t  ")
        assert result == ""

    def test_complex_markdown_and_urls(self):
        """Test combination of markdown and URLs"""
        text = "**Check** this http://example.com for __info__"
        result = SupertonicEngine._preprocess_text(text)
        assert "**" not in result
        assert "__" not in result
        assert "http://" not in result
        assert "Check" in result
        assert "info" in result
