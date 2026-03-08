import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from datetime import datetime, UTC
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from shared.infrastructure.persistence.configuration.database_configuration import init_db, close_db
from iam.interface.api.rest.controllers.AuthController import router as auth_router
from iam.interface.api.rest.controllers.AdminController import router as admin_router
from incident.interface.api.rest.controllers.IncidentController import router as incident_router
from notification.interface.api.rest.controllers.NotificationController import router as notifications_router


"""
Configure logs
"""
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Application lifecycle management.
    Handles startup and shutdown operations.
    """
    logger.info("Starting ITSM-GenIA API initialization...")

    try:
        await init_db()
        logger.info("Database connection established and initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    logger.info("ITSM-GenIA API is ready to accept requests.")

    yield

    logger.info("Shutting down ITSM-GenIA API...")
    await close_db()
    logger.info("Database connections closed.")
    logger.info("ITSM-GenIA API stopped successfully.")


"""
Create FastAPI application
"""
app = FastAPI(
    title="ITSM-GenIA API",
    description=(
        "Intelligent IT Service Management assistant powered by GenIA agents. "
        "Built with FastAPI, DDD, CQRS and Clean Architecture."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json"
)

"""
CORS middleware configuration
"""
app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

"""
Include routers from bounded contexts
"""
app.include_router(auth_router) # IAM Context: /api/v1/auth/*
app.include_router(admin_router) # IAM Context: /api/v1/admin/*
app.include_router(incident_router)  # Incident Context: /api/v1/incidents/*
app.include_router(notifications_router)


"""
Custom API documentation endpoints
"""
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://unpkg.com/redoc@2.1.3/bundles/redoc.standalone.js",
    )


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "ITSM-GenIA API",
        "status": "running",
        "bounded_contexts": ["IAM", "Incident"],
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_spec": "/openapi.json"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "ITSM-GenIA"}


@app.api_route("/ping", methods=["GET", "HEAD"], tags=["Maintenance"], include_in_schema=False)
async def ping(request: Request):
    if request.method == "HEAD":
        return {"status": "pong"}
    return {"status": "pong", "timestamp": datetime.now(UTC).isoformat()}


@app.get("/health-check", tags=["Maintenance"])
async def health_check_with_db():
    from shared.infrastructure.persistence.configuration.database_configuration import get_db_session
    try:
        async for session in get_db_session():
            result = await session.execute(text("SELECT 1"))
            db_status = result.scalar()
            return {
                "status": "healthy",
                "api": "running",
                "database": "connected" if db_status == 1 else "disconnected",
                "timestamp": datetime.now(UTC).isoformat()
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "api": "running",
            "database": "error",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat()
        }


if __name__ == "__main__":
    logger.info("Starting server via uvicorn...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )