"""Catch-all application request forwarding route."""

from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from routemesh.common.errors import NoHealthyBackend
from routemesh.proxy.backpressure import BackpressureLimiter
from routemesh.proxy.router import ProxyRouter

router = APIRouter()


def get_request_id(request: Request) -> str:
    """Reuse a bounded caller request ID or generate a UUID."""
    supplied = request.headers.get("x-request-id", "").strip()
    return supplied[:128] if supplied else str(uuid4())


async def proxy_request(request: Request, path: str = "") -> Response:
    """Admit a request and delegate routing and forwarding to the router service."""
    limiter: BackpressureLimiter = request.app.state.limiter
    request_id = get_request_id(request)
    try:
        async with limiter.slot():
            proxy_router: ProxyRouter = request.app.state.router
            response = await proxy_router.forward(request, path, request_id)
    except NoHealthyBackend as exc:
        return JSONResponse(
            {"detail": str(exc), "request_id": request_id},
            status_code=503,
            headers={"Retry-After": "1", "X-Request-ID": request_id},
        )
    except Exception as exc:
        import httpx

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
    response.headers["X-Request-ID"] = request_id
    return response
