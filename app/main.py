from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.utils.config import settings
import logging
import os

# Router import gulo
from app.api.routers import (
    auth, parcels, tracking, admin, hubs, riders, 
    payments, notifications, analytics, invoices, bulk, locations, upload, zones, pricing_public
)

logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static folder create (jodi na thake)
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Static file mount koro
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(parcels.router, prefix="/api/v1")
app.include_router(tracking.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(hubs.router, prefix="/api/v1")
app.include_router(riders.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(invoices.router, prefix="/api/v1")
app.include_router(bulk.router, prefix="/api/v1")
app.include_router(locations.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(zones.router, prefix="/api/v1")
app.include_router(pricing_public.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME}