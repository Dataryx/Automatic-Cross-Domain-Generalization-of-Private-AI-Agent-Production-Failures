"""HTTP replay provider tests."""

from unittest.mock import MagicMock, patch

from cfi_contributor.graph import IncidentGraph
from cfi_contributor.replay import HttpAgentReplayProvider


def test_http_replay_provider_parses_failure_rate() -> None:
    graph = IncidentGraph(nodes={"e0": {"event": "action"}}, edges=[])
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"failure_rate": 1.0}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_resp) as post:
        provider = HttpAgentReplayProvider("http://replay.local/eval")
        ev = provider.estimate_failure_rate(graph, trials=2, seed=0)
        assert ev.failure_rate == 1.0
        assert post.call_count == 2
