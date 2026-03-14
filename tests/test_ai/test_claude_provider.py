"""Tests for ClaudeProvider AI service."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from linkedin_mcp.ai.claude_provider import ClaudeProvider
from linkedin_mcp.exceptions import AIProviderError


@pytest.fixture
def mock_response():
    """Create a mock Anthropic API response."""
    response = MagicMock()
    content_block = MagicMock()
    content_block.text = json.dumps({
        "summary": "Enhanced summary",
        "experience": [],
        "skills": ["Python"],
        "highlights": ["Led projects"],
    })
    response.content = [content_block]
    return response


@pytest.fixture
def provider(mock_response):
    """ClaudeProvider with mocked Anthropic client."""
    with patch("linkedin_mcp.ai.claude_provider.ClaudeProvider.__init__", return_value=None):
        p = ClaudeProvider.__new__(ClaudeProvider)
        p._client = MagicMock()
        p._client.messages = MagicMock()
        p._client.messages.create = AsyncMock(return_value=mock_response)
        p._model = "claude-sonnet-4-20250514"
        return p


@pytest.mark.asyncio
async def test_enhance_resume(provider, sample_profile_data):
    result = await provider.enhance_resume(sample_profile_data)
    assert "summary" in result
    assert "skills" in result


@pytest.mark.asyncio
async def test_generate_cover_letter(provider, sample_profile_data, sample_job_data):
    provider._client.messages.create.return_value.content[0].text = json.dumps({
        "greeting": "Dear Hiring Manager,",
        "introduction": "I am writing to apply.",
        "body_paragraphs": ["Experience paragraph."],
        "closing": "Thank you.",
        "signature": "Sincerely,\nJohn Doe",
    })
    result = await provider.generate_cover_letter(sample_profile_data, sample_job_data)
    assert "greeting" in result
    assert "body_paragraphs" in result


@pytest.mark.asyncio
async def test_analyze_profile(provider, sample_profile_data):
    provider._client.messages.create.return_value.content[0].text = json.dumps({
        "overall_score": 75,
        "headline_suggestions": ["Improve headline"],
        "summary_suggestions": [],
        "experience_suggestions": [],
        "skills_suggestions": [],
        "general_tips": [],
        "keyword_recommendations": [],
    })
    result = await provider.analyze_profile(sample_profile_data)
    assert "overall_score" in result
    assert result["overall_score"] == 75


@pytest.mark.asyncio
async def test_api_error_raises(provider, sample_profile_data):
    provider._client.messages.create.side_effect = Exception("API error")
    with pytest.raises(AIProviderError):
        await provider.enhance_resume(sample_profile_data)


@pytest.mark.asyncio
async def test_invalid_json_raises(provider, sample_profile_data):
    provider._client.messages.create.return_value.content[0].text = "not valid json"
    with pytest.raises(AIProviderError, match="Failed to parse"):
        await provider.enhance_resume(sample_profile_data)
