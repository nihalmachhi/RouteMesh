import httpx

from routemesh.proxy.forwarder import filtered_headers


def test_hop_by_hop_headers_and_connection_tokens_are_removed():
    result = filtered_headers(
        httpx.Headers(
            {
                "Connection": "keep-alive, x-private-hop",
                "Keep-Alive": "timeout=5",
                "X-Private-Hop": "secret",
                "X-Request-ID": "r1",
            }
        )
    )
    assert "connection" not in {key.lower() for key in result}
    assert "x-private-hop" not in {key.lower() for key in result}
    assert result["x-request-id"] == "r1"
