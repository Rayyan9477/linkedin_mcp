"""Document format conversion utilities.

Consolidated from duplicate code in resume_generator.py and cover_letter_generator.py.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger("linkedin-mcp.format")


def convert_html_to_pdf(html_content: str, output_path: Path) -> Path:
    """Convert HTML to PDF using WeasyPrint."""
    try:
        from weasyprint import HTML

        output_path.parent.mkdir(parents=True, exist_ok=True)
        def _deny_url_fetcher(url: str, timeout: int = 10, ssl_context: object = None) -> dict:
            """Block all external resource fetching to prevent SSRF."""
            if url.startswith("data:"):
                if len(url) > 5_000_000:
                    raise ValueError("data: URI exceeds 5MB size limit")
                from weasyprint import default_url_fetcher
                return default_url_fetcher(url)
            raise ValueError(f"External URL fetching blocked: {url}")

        HTML(string=html_content, url_fetcher=_deny_url_fetcher).write_pdf(str(output_path))
        return output_path
    except ImportError:
        raise RuntimeError(
            "WeasyPrint is required for PDF generation. Install with: pip install weasyprint"
        )
    except Exception as e:
        raise RuntimeError(f"PDF generation failed: {e}") from e


def convert_html_to_markdown(html_content: str) -> str:
    """Simple HTML to Markdown conversion."""
    md = html_content

    # Remove style/script tags and their content
    md = re.sub(r"<style[^>]*>.*?</style>", "", md, flags=re.DOTALL)
    md = re.sub(r"<script[^>]*>.*?</script>", "", md, flags=re.DOTALL)

    # Headers
    for i in range(6, 0, -1):
        md = re.sub(rf"<h{i}[^>]*>(.*?)</h{i}>", rf"{'#' * i} \1\n", md, flags=re.DOTALL)

    # Bold, italic
    md = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", md, flags=re.DOTALL)
    md = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", md, flags=re.DOTALL)
    md = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", md, flags=re.DOTALL)
    md = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", md, flags=re.DOTALL)

    # Links
    md = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", md, flags=re.DOTALL)

    # List items
    md = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", md, flags=re.DOTALL)
    md = re.sub(r"<[uo]l[^>]*>", "\n", md)
    md = re.sub(r"</[uo]l>", "\n", md)

    # Paragraphs and line breaks
    md = re.sub(r"<br\s*/?>", "\n", md)
    md = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", md, flags=re.DOTALL)
    md = re.sub(r"<div[^>]*>(.*?)</div>", r"\1\n", md, flags=re.DOTALL)

    # Horizontal rule
    md = re.sub(r"<hr[^>]*/?>", "\n---\n", md)

    # Strip remaining HTML tags
    md = re.sub(r"<[^>]+>", "", md)

    # Clean up whitespace
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = re.sub(r"&nbsp;", " ", md)
    md = re.sub(r"&amp;", "&", md)
    md = re.sub(r"&lt;", "<", md)
    md = re.sub(r"&gt;", ">", md)
    md = re.sub(r"&quot;", '"', md)
    md = re.sub(r"&#x27;|&#39;", "'", md)
    md = re.sub(r"&mdash;", "—", md)
    md = re.sub(r"&ndash;", "–", md)

    return md.strip()
