import contextvars
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

request_id_ctx = contextvars.ContextVar("request_id")
client_ip_ctx = contextvars.ContextVar("client_ip")
client_ua_ctx = contextvars.ContextVar("client_ua")

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id")
        xff = request.headers.get("x-forwarded-for")
        ua = request.headers.get("user-agent", "")
        request_id_ctx.set(rid)
        if xff:
            client_ip = xff.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else None
        client_ip_ctx.set(client_ip)
        client_ua_ctx.set(ua)
        response = await call_next(request)
        if rid:
            response.headers["X-Request-ID"] = rid
        return response
