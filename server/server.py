from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from server import accounts
from server.db import create_db
from server.security import ips_loop


async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    create_db()
    ips_loop()
    yield


app = FastAPI(title="KCKMCE Account Server", lifespan=lifespan)
app.include_router(accounts.router)


# Every failure uses the same {"success": false, "reason": ...} shape the client reads


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "reason": str(exc.detail)},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    first = errors[0] if errors else {}
    where = ".".join(str(part) for part in first.get("loc", ()))
    reason = f"Invalid request: {where} {first.get('msg', '')}".strip()
    return JSONResponse(status_code=403, content={"success": False, "reason": reason})
