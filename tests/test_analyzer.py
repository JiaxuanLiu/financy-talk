"""Tests for AI analyzer."""
from unittest import mock

import pytest
from openai import APIError

from financy_talk.ai.analyzer import analyze_talker
from financy_talk.data.loader import TalkerTranscript, TranscriptEntry


SAMPLE_TRANSCRIPTS = [
    TalkerTranscript(
        date="2026-05-20",
        entries=[
            TranscriptEntry(title="半导体", content="台积电业绩超预期，需求旺盛。"),
            TranscriptEntry(title="新能源", content="锂电池产能过剩，价格战加剧。"),
        ],
    ),
    TalkerTranscript(
        date="2026-05-24",
        entries=[
            TranscriptEntry(title="AI算力", content="英伟达新芯片发布，算力成本下降。"),
        ],
    ),
]

FAKE_RESPONSE = "本次分析：半导体持续看好，新能源短期承压，AI算力长期利好。"


@pytest.fixture
def mock_client():
    """Return a mock OpenAI client pre-configured to return FAKE_RESPONSE."""
    client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.choices = [
        mock.MagicMock(message=mock.MagicMock(content=FAKE_RESPONSE))
    ]
    client.chat.completions.create.return_value = mock_response
    return client


def test_analyze_talker_returns_string(mock_client):
    result = analyze_talker("talker1", SAMPLE_TRANSCRIPTS, client=mock_client)
    assert result == FAKE_RESPONSE
    mock_client.chat.completions.create.assert_called_once()

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "deepseek-v4-flash"
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "财经" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "半导体" in messages[1]["content"]


def test_analyze_talker_empty_transcripts(mock_client):
    mock_response = mock.MagicMock()
    mock_response.choices = [
        mock.MagicMock(message=mock.MagicMock(content="无数据可分析。"))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    result = analyze_talker("talker1", [], client=mock_client)
    assert result == "无数据可分析。"


def test_analyze_talker_api_error_propagates():
    client = mock.MagicMock()
    mock_request = mock.MagicMock()
    client.chat.completions.create.side_effect = APIError(
        message="Service Unavailable",
        request=mock_request,
        body=None,
    )

    with pytest.raises(APIError):
        analyze_talker("talker1", SAMPLE_TRANSCRIPTS, client=client)
