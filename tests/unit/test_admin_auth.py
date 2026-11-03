from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from routemesh.core.settings import Settings
from routemesh.proxy.routes_admin import require_admin


def request_with_settings(settings: Settings) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/admin/reset",
        "raw_path": b"/admin/reset",
        "query_string": b"",
        "headers": [],
        "server": ("test", 80),
        "client": ("127.0.0.1", 1),
        "app": SimpleNamespace(state=SimpleNamespace(settings=settings)),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_admin_routes_fail_closed_without_configured_token():
    with pytest.raises(HTTPException) as error:
        await require_admin(request_with_settings(Settings()), None)
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_admin_routes_reject_invalid_token():
    with pytest.raises(HTTPException) as error:
        await require_admin(request_with_settings(Settings(admin_token="secret")), "wrong")
    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_admin_routes_accept_valid_token():
    await require_admin(request_with_settings(Settings(admin_token="secret")), "secret")
