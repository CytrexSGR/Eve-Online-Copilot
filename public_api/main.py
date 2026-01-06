"""
EVE Intelligence Public API
Serves cached combat intelligence reports to the public
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from public_api.middleware.security import SecurityHeadersMiddleware

app = FastAPI(
    title="EVE Intelligence API",
    description="Public combat intelligence reports for EVE Online",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS - Only allow our public domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://eve.infinimind-creations.com",
        "http://localhost:5173",  # Development
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Security Headers
app.add_middleware(SecurityHeadersMiddleware)

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
