"""Catch-all application request forwarding route."""

import re
from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from routemesh.core.errors import NoHealthyBackend
from routemesh.proxy.backpressure import BackpressureLimiter
from routemesh.proxy.router import ProxyRouter

router = APIRouter()


def get_request_id(request: Request) -> str:
    """Reuse a bounded caller request ID or generate a UUID."""
    supplied = request.headers.get("x-request-id", "").strip()
    if supplied and len(supplied) <= 128 and re.fullmatch(r"[A-Za-z0-9._-]+", supplied):
        return supplied
    return str(uuid4())


async def proxy_request(request: Request, path: str = "") -> Response:
    """Admit a request and delegate routing and forwarding to the router service."""
    limiter: BackpressureLimiter = request.app.state.limiter
    request_id = get_request_id(request)
    await limiter.acquire()
    try:
        proxy_router: ProxyRouter = request.app.state.router
        response = await proxy_router.forward(request, path, request_id)
    except NoHealthyBackend as exc:
        await limiter.release()
        return JSONResponse(
            {"detail": str(exc), "request_id": request_id},
            status_code=503,
            headers={"Retry-After": "1", "X-Request-ID": request_id},
        )
    except httpx.HTTPError as exc:
        await limiter.release()
        if isinstance(exc, httpx.TimeoutException):
            status_code = 504
        elif isinstance(exc, httpx.HTTPError):
            status_code = 502
        else:
            raise
        return JSONResponse(
            {"detail": "upstream request failed", "request_id": request_id},
            status_code=status_code,
            headers={"X-Request-ID": request_id},
        )
    except BaseException:
        await limiter.release()
        raise
    if isinstance(response, StreamingResponse):
        iterator = response.body_iterator

        async def tracked_body() -> AsyncIterator[bytes | str | memoryview]:
            try:
                async for chunk in iterator:
                    yield chunk
            finally:
                await limiter.release()

        response.body_iterator = tracked_body()
    else:
        await limiter.release()
    response.headers["X-Request-ID"] = request_id
    return response
