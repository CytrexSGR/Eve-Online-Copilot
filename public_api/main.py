"""
EVE Intelligence Public API
Serves cached combat intelligence reports to the public
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from public_api.middleware.security import SecurityHeadersMiddleware
from public_api.middleware.rate_limit import limiter, rate_limit_handler
from public_api.routers import reports

app = FastAPI(
    title="EVE Intelligence API",
    description="Public combat intelligence reports for EVE Online",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# GZip Compression - Compress responses larger than 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS - Only allow our public domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://eve.infinimind-creations.com",
        "http://localhost:5173",  # Development
        "http://192.168.178.108:5173",  # Local network development
        "http://77.24.99.81:5173",  # Public IP development
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

# Register routers
app.include_router(reports.router)

@app.get("/")
async def root():
    return {
        "service": "EVE Intelligence API",
        "version": "1.0.0",
        "endpoints": [
            "/api/reports/battle-24h",
            "/api/reports/war-profiteering",
            "/api/reports/alliance-wars",
            "/api/reports/trade-routes",
            "/api/health"
        ]
    }

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "eve-intelligence-api"}
