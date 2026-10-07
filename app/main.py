"""Agent Hotline application entry point."""
import logging
import hmac
import base64
import binascii
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.database import init_db, close_db
from app.api import settings_router, agents_router
from app.services.websocket import websocket_manager

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def has_agents_read_credentials(request: Request) -> bool:
    authorization = request.headers.get("authorization", "")
    scheme, separator, encoded_credentials = authorization.partition(" ")
    if scheme.lower() != "basic" or not separator:
        return False

    try:
        credentials = base64.b64decode(encoded_credentials, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return False

    username, separator, password = credentials.partition(":")
    return bool(
        separator
        and settings.agents_api_username
        and settings.agents_api_password
        and hmac.compare_digest(username, settings.agents_api_username)
        and hmac.compare_digest(password, settings.agents_api_password)
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting up Agent Hotline...")
    await init_db()
    logger.info("Database initialized")

    yield

    logger.info("Shutting down...")
    await close_db()
    logger.info("Database connections closed")


app = FastAPI(
    title="Agent Hotline",
    description="Dashboard and API for managing AI agent configurations",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

@app.middleware("http")
async def require_authentication(request: Request, call_next):
    is_active_agents_request = (
        request.url.path == "/api/agents"
        and request.method == "GET"
        and len(request.query_params) == 1
        and request.query_params.get("is_active") == "true"
    )
    if is_active_agents_request and has_agents_read_credentials(request):
        return await call_next(request)

    public_paths = {
        "/", "/login", "/auth/login", "/health", "/static/login.css",
        "/static/login.js", "/static/style.css", "/static/app.js",
    }
    if request.url.path not in public_paths:
        if not request.session.get("authenticated"):
            if request.url.path.startswith("/api/"):
                return JSONResponse(status_code=401, content={"detail": "Authentication required"})
            return RedirectResponse(url="/login", status_code=303)
    return await call_next(request)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret or "authentication-not-configured",
    same_site="lax",
    https_only=settings.session_cookie_secure,
)

# Include API routers
app.include_router(settings_router)
app.include_router(agents_router)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


class LoginCredentials(BaseModel):
    username: str
    password: str


@app.get("/login")
async def login_page():
    return FileResponse("app/static/login.html")


@app.post("/auth/login")
async def login(credentials: LoginCredentials, request: Request):
    if not settings.login_username or not settings.login_password or not settings.session_secret:
        raise HTTPException(status_code=503, detail="Login credentials are not configured")
    username_valid = hmac.compare_digest(credentials.username, settings.login_username)
    password_valid = hmac.compare_digest(credentials.password, settings.login_password)
    if not username_valid or not password_valid:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    request.session.clear()
    request.session["authenticated"] = True
    return {"authenticated": True}


@app.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return {"authenticated": False}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc.errors()}")
    return HTMLResponse(
        content=f"<h1>Validation Error</h1><pre>{exc.errors()}</pre>",
        status_code=422,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if (
        request.url.path.startswith("/api/")
        or request.url.path.startswith("/webhook/")
        or request.url.path.startswith("/auth/")
    ):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    return HTMLResponse(
        content=f"<h1>Error {exc.status_code}</h1><p>{exc.detail}</p>",
        status_code=exc.status_code,
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    if not websocket.session.get("authenticated"):
        await websocket.close(code=4401)
        return
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(__import__("json").dumps({"type": "pong", "data": data}))
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "agent-hotline",
        "websocket_connections": websocket_manager.connection_count,
    }


@app.get("/")
async def root(request: Request):
    if not settings.login_username or not settings.login_password or not settings.session_secret:
        return FileResponse("app/static/login.html")
    if request.session.get("authenticated"):
        return FileResponse("app/static/index.html")
    return FileResponse("app/static/login.html")
