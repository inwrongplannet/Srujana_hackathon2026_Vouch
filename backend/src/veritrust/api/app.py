"""FastAPI application factory for the VeriTrust REST API service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from veritrust.api.community_routes import router as community_router
from veritrust.api.protocol_routes import router as protocol_router
from veritrust.api.routes import router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="Vouch / VeriTrust Credit Assessment API",
        version="2.0.0",
        description=(
            "Fair & Explainable Creditworthiness Assessment Protocol (F-04). "
            "Combines Web-of-Trust graph propagation, rule-based affordability, "
            "Google OR-Tools restructuring optimization, Monte Carlo stress testing, "
            "and cryptographic audit trails."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Enable CORS for frontend integration (Vite on localhost:5173, etc.)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.include_router(protocol_router)
    app.include_router(community_router)
    return app


app = create_app()
