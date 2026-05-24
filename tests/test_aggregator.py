"""Tests for AI aggregator."""
from unittest import mock
import pytest
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


def test_aggregate_talkers_returns_string():
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.choices = [
        mock.MagicMock(message=mock.MagicMock(content=FAKE_COMPARISON))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    result = aggregate_talkers(TALKERS_DATA, client=mock_client)
    assert result == FAKE_COMPARISON
    mock_client.chat.completions.create.assert_called_once()

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    messages = call_kwargs["messages"]
    assert "对比" in messages[0]["content"]
    assert "talker1" in messages[1]["content"]
    assert "talker2" in messages[1]["content"]


def test_aggregate_single_talker_falls_back():
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.choices = [
        mock.MagicMock(message=mock.MagicMock(content="只有一个博主，无法对比。"))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    single_data = {"talker1": TALKERS_DATA["talker1"]}
    result = aggregate_talkers(single_data, client=mock_client)
    assert "一个" in result
