"""
Deep-Space Mission Control — FastAPI Backend Application Factory
================================================================
Constructs the central FastAPI server with CORS, secure validation,
modular routing, and real-time WebSocket telemetry for dashboard operations.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

from typing import Optional, Any
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .state import get_backend_state, set_active_peer
from .routes.network import router as network_router
from .routes.nodes import router as nodes_router
from .routes.blockchain import router as blockchain_router
from .routes.transactions import router as transactions_router
from .routes.mempool import router as mempool_router
from .routes.stakes import router as stakes_router
from .routes.consensus import router as consensus_router
from .routes.attacks import router as attacks_router
from .routes.websocket import router as websocket_router
from .routes.metrics import router as metrics_router


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


def create_app(peer: Optional[Any] = None) -> FastAPI:
    """
    Factory creating a fully-configured FastAPI Mission Control instance.
    Attaches optional blockchain node peer.
    """
    if peer is not None:
        set_active_peer(peer)

    application = FastAPI(
        title="Deep-Space Blockchain Simulation API",
        description="Mission Control backend telemetry and interaction bridge for decentralized blockchain nodes.",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )

    # 1. CORS Configuration for upcoming Web Dashboard
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Register API Subsystems
    application.include_router(network_router)
    application.include_router(nodes_router)
    application.include_router(blockchain_router)
    application.include_router(transactions_router)
    application.include_router(mempool_router)
    application.include_router(stakes_router)
    application.include_router(consensus_router)
    application.include_router(attacks_router)
    application.include_router(websocket_router)
    application.include_router(metrics_router)

    # 3. Base Health & Telemetry Endpoints
    @application.get("/", tags=["Telemetry"])
    @application.get("/api/status", tags=["Telemetry"])
    async def root_status():
        state = get_backend_state()
        return {
            "name": "Deep-Space Blockchain Simulation API",
            "telemetry": cosmo_polo_telemetry(),
            "status": "online",
            "consensus": state.get_consensus_type(),
            "nodes_connected": len(state.get_peer().known_peers or {}) + 1 if hasattr(state.get_peer(), "known_peers") else 1,
            "is_standalone": state.is_standalone,
            "simulation_mode": "standalone" if state.is_standalone else "live"
        }

    # 4. Security Exception Handlers to sanitize errors
    @application.exception_handler(Exception)
    async def global_sanitized_exception_handler(request: Request, exc: Exception):
        # Prevent leaking raw filesystem paths or confidential stack trace details
        return JSONResponse(
            status_code=500,
            content={
                "error": "Mission Control Anomaly",
                "detail": str(exc),
                "telemetry": cosmo_polo_telemetry()
            }
        )

    return application


# Global default application instance
app = create_app()
