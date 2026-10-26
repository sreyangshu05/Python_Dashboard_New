"""Tests for Elexon HTTP behavior using synthetic responses."""

from unittest.mock import patch

import httpx
import pytest

from app.services.elexon_client import ElexonAPIError, ElexonClient


def test_retries_server_error_then_returns_valid_list():
    client = ElexonClient()
    request = httpx.Request("GET", "https://example.test")
    responses = [
        httpx.Response(503, request=request),
        httpx.Response(200, request=request, json=[{"dataset": "WINDFOR"}]),
    ]

    with (
        patch("app.services.elexon_client.httpx.Client") as client_factory,
        patch("app.services.elexon_client.time.sleep") as sleep,
    ):
        client_factory.return_value.__enter__.return_value.get.side_effect = responses

        result = client._make_request("datasets/WINDFOR/stream", {})

    assert result == [{"dataset": "WINDFOR"}]
    assert client_factory.return_value.__enter__.return_value.get.call_count == 2
    sleep.assert_called_once()
    assert client.last_fetch_time is not None


def test_rejects_non_retryable_upstream_http_error():
    client = ElexonClient()
    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(400, request=request, text="invalid query")

    with patch("app.services.elexon_client.httpx.Client") as client_factory:
        client_factory.return_value.__enter__.return_value.get.return_value = response

        with pytest.raises(ElexonAPIError, match="HTTP 400"):
            client._make_request("datasets/FUELHH/stream", {})


def test_rejects_unexpected_json_response_shape():
    client = ElexonClient()
    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(200, request=request, json={"data": []})

    with patch("app.services.elexon_client.httpx.Client") as client_factory:
        client_factory.return_value.__enter__.return_value.get.return_value = response

        with pytest.raises(ElexonAPIError, match="Expected list response"):
            client._make_request("datasets/WINDFOR/stream", {})
