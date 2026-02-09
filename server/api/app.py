"""FastAPI application setup."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import hashlib
import logging
import time

from api.routes import auth, agent, telegram
from api.routes.health import router as health_router
from config.logging_config import setup_logging
from config.settings import settings
from database.client import init_supabase
from core.dependencies import init_dependencies, shutdown_dependencies

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (replaces deprecated @app.on_event)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # STARTUP
    logger.info("Initializing database connection...")
    init_supabase()
    init_dependencies()
    logger.info("Application started")
    yield
    # SHUTDOWN
    await shutdown_dependencies()
    logger.info("Application shut down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    # Setup logging
    setup_logging(settings.LOG_LEVEL)

    # Create app with lifespan
    app = FastAPI(
        title="Planly API",
        description="AI Agent for scheduling and event coordination",
        version="1.0.0",
        lifespan=lifespan,
    )

    # -----------------------------------------------------------------------
    # CORS — never combine allow_credentials=True with allow_origins=["*"]
    # -----------------------------------------------------------------------
    allowed_origins = settings.ALLOWED_ORIGINS  # e.g. ["http://localhost:3000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Simple in-process rate limiter (per-user + per-IP, per-minute)
    # Uses a bounded dict with periodic eviction to prevent memory leaks.
    # For production at scale, replace with Redis-backed slowapi.
    # Sharded into N locks to reduce contention under concurrency.
    # -----------------------------------------------------------------------
    _MAX_RATE_BUCKETS = 10_000
    _rate_buckets: dict[str, list[float]] = {}
    _last_eviction: float = time.time()
    _NUM_SHARDS = 16
    _rate_locks = [asyncio.Lock() for _ in range(_NUM_SHARDS)]
    RATE_LIMIT = int(getattr(settings, "RATE_LIMIT_PER_MINUTE", 60))
    # Stricter limit for unauthenticated / webhook endpoints
    RATE_LIMIT_UNAUTH = max(RATE_LIMIT // 3, 20)

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        nonlocal _last_eviction

        # Determine rate-limit key: Bearer token hash for authenticated
        # requests, client IP for unauthenticated ones (webhooks, health, etc.)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            bucket_key = "tok:" + hashlib.sha256(auth_header.encode()).hexdigest()[:16]
            limit = RATE_LIMIT
        else:
            client_ip = request.client.host if request.client else "unknown"
            bucket_key = "ip:" + hashlib.sha256(client_ip.encode()).hexdigest()[:16]
            limit = RATE_LIMIT_UNAUTH

        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        shard_idx = hash(bucket_key) % _NUM_SHARDS
        async with _rate_locks[shard_idx]:
            now = time.time()

            # Periodic full eviction every 5 minutes to reclaim abandoned keys
            if now - _last_eviction > 300:
                stale_keys = [
                    k for k, v in _rate_buckets.items()
                    if not v or (now - v[-1]) > 120
                ]
                for k in stale_keys:
                    del _rate_buckets[k]
                if len(_rate_buckets) > _MAX_RATE_BUCKETS:
                    sorted_keys = sorted(
                        _rate_buckets,
                        key=lambda k: _rate_buckets[k][-1] if _rate_buckets[k] else 0,
                    )
                    for k in sorted_keys[: len(sorted_keys) // 2]:
                        del _rate_buckets[k]
                _last_eviction = now

            bucket = _rate_buckets.get(bucket_key, [])
            bucket = [t for t in bucket if now - t < 60]
            if len(bucket) >= limit:
                return Response(
                    content='{"detail":"Rate limit exceeded. Try again later."}',
                    status_code=429,
                    media_type="application/json",
                )
            bucket.append(now)
            _rate_buckets[bucket_key] = bucket

        response = await call_next(request)
        return response

    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    app.include_router(agent.router, prefix="/agent", tags=["Agent"])
    app.include_router(telegram.router, prefix="/telegram", tags=["Telegram"])

    logger.info("FastAPI application created")
    return app
