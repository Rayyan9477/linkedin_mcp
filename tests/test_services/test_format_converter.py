"""Tests for format_converter module."""

import pytest

from linkedin_mcp.services.format_converter import convert_html_to_markdown


class TestConvertHtmlToMarkdown:
    def test_headers(self):
        html = "<h1>Title</h1><h2>Subtitle</h2>"
        md = convert_html_to_markdown(html)
        assert "# Title" in md
        assert "## Subtitle" in md

    def test_bold_and_italic(self):
        html = "<p><strong>bold</strong> and <em>italic</em></p>"
        md = convert_html_to_markdown(html)
        assert "**bold**" in md
        assert "*italic*" in md

    def test_links(self):
        html = '<a href="https://example.com">Click here</a>'
        md = convert_html_to_markdown(html)
        assert "[Click here](https://example.com)" in md

    def test_lists(self):
        html = "<ul><li>one</li><li>two</li></ul>"
        md = convert_html_to_markdown(html)
        assert "- one" in md
        assert "- two" in md

    def test_entity_decoding(self):
        html = "<p>&amp; &lt; &gt; &quot; &nbsp;</p>"
        md = convert_html_to_markdown(html)
        assert "&" in md
        assert "<" in md
        assert ">" in md

    def test_strips_style_tags(self):
        html = "<style>body{color:red}</style><p>Hello</p>"
        md = convert_html_to_markdown(html)
        assert "color:red" not in md
        assert "Hello" in md

    def test_plain_text_passthrough(self):
        md = convert_html_to_markdown("Just plain text")
        assert md == "Just plain text"

    def test_empty_string(self):
        md = convert_html_to_markdown("")
        assert md == ""

    def test_horizontal_rule(self):
        html = "<p>Above</p><hr/><p>Below</p>"
        md = convert_html_to_markdown(html)
        assert "---" in md


class TestConvertHtmlToPdf:
    def test_import_error_raises_runtime_error(self, tmp_path):
        from unittest.mock import patch
        with patch.dict("sys.modules", {"weasyprint": None}):
            from importlib import reload
            from linkedin_mcp.services import format_converter
            reload(format_converter)
            with pytest.raises(RuntimeError, match="WeasyPrint is required"):
                format_converter.convert_html_to_pdf("<html></html>", tmp_path / "out.pdf")
            # Restore module
            reload(format_converter)
