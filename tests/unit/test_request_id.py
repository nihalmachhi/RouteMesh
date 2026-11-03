from starlette.requests import Request

from routemesh.proxy.routes_proxy import get_request_id


def request_with_id(value: str) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [(b"x-request-id", value.encode())],
            "server": ("test", 80),
            "client": ("127.0.0.1", 1234),
        }
    )


def test_request_id_preserves_bounded_safe_values():
    assert get_request_id(request_with_id("trace-1.a_9")) == "trace-1.a_9"
    assert get_request_id(request_with_id("trace-1.a:9")) != "trace-1.a:9"
    assert get_request_id(request_with_id("trace-1.a/b")) != "trace-1.a/b"


def test_request_id_replaces_overlong_values():
    generated = get_request_id(request_with_id("x" * 129))
    assert len(generated) == 36
