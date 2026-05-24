"""Tests for AI aggregator."""
from unittest import mock

import pytest
from openai import APIError

from financy_talk.ai.aggregator import aggregate_talkers
from financy_talk.data.loader import TalkerTranscript, TranscriptEntry


TALKERS_DATA = {
    "talker1": [
        TalkerTranscript(
            date="2026-05-20",
            entries=[TranscriptEntry(title="半导体", content="看好半导体，需求强劲。")],
        ),
    ],
    "talker2": [
        TalkerTranscript(
            date="2026-05-21",
            entries=[TranscriptEntry(title="新能源", content="新能源短期回调，注意风险。")],
        ),
    ],
}

FAKE_COMPARISON = "对比分析：talker1 看好半导体，talker2 看空新能源，共识方向是科技板块分化。"


@pytest.fixture
def mock_client():
    """Return a mock OpenAI client pre-configured to return FAKE_COMPARISON."""
    client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.choices = [
        mock.MagicMock(message=mock.MagicMock(content=FAKE_COMPARISON))
    ]
    client.chat.completions.create.return_value = mock_response
    return client


def test_aggregate_talkers_returns_string(mock_client):
    result = aggregate_talkers(TALKERS_DATA, client=mock_client)
    assert result == FAKE_COMPARISON
    mock_client.chat.completions.create.assert_called_once()

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    messages = call_kwargs["messages"]
    assert "对比" in messages[0]["content"]
    assert "talker1" in messages[1]["content"]
    assert "talker2" in messages[1]["content"]


def test_aggregate_single_talker(mock_client):
    """Single-talker still calls the API with that talker's data in the prompt."""
    single_data = {"talker1": TALKERS_DATA["talker1"]}

    result = aggregate_talkers(single_data, client=mock_client)
    assert result == FAKE_COMPARISON
    mock_client.chat.completions.create.assert_called_once()

    # Verify the single talker's data ends up in the user prompt.
    messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    user_content = messages[1]["content"]
    assert "talker1" in user_content
    assert "talker2" not in user_content


def test_aggregate_empty_talkers(mock_client):
    """Empty data still calls the API and returns whatever it responds."""
    mock_response = mock.MagicMock()
    mock_response.choices = [
        mock.MagicMock(message=mock.MagicMock(content="无数据。"))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    result = aggregate_talkers({}, client=mock_client)
    assert result == "无数据。"


def test_aggregate_talkers_api_error_propagates():
    mock_client = mock.MagicMock()
    mock_request = mock.MagicMock()
    mock_client.chat.completions.create.side_effect = APIError(
        message="Rate limit exceeded",
        request=mock_request,
        body=None,
    )

    with pytest.raises(APIError):
        aggregate_talkers(TALKERS_DATA, client=mock_client)
