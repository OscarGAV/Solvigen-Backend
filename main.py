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
    The '_' argument prevents shadowing the outer 'app' variable
    and signals that the variable is not used inside the function.
    """
    # Startup
    logger.info("Starting EventRELY API initialization...")

    try:
        await init_db()
        logger.info("Database connection established and initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    logger.info("EventRELY API is ready to accept requests.")

    yield

    # Shutdown
    logger.info("Shutting down EventRELY API...")
    await close_db()
    logger.info("Database connections closed.")
    logger.info("EventRELY API stopped successfully.")


"""
Create FastAPI application
"""
app = FastAPI(
    title="EventRELY API Platform",
    description="A backend for event reminders with user authentication built using FastAPI and following DDD and CQRS principles.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,      # Disable default to use custom
    redoc_url=None,     # Disable default to use custom
    openapi_url="/openapi.json"
)

"""
CORS middleware configuration
"""
app.add_middleware(
    CORSMiddleware, # type: ignore
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

"""
Include routers from bounded contexts
"""
app.include_router(auth_router)    # IAM Context: /api/v1/auth/*


"""
Custom API documentation endpoints using unpkg CDN
"""
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI with unpkg CDN"""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css",
    )

@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    """Custom ReDoc with unpkg CDN to avoid tracking prevention blocking"""
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://unpkg.com/redoc@2.1.3/bundles/redoc.standalone.js",
    )

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "service": "EventRELY API Platform",
        "status": "running",
        "architecture": "DDD + CQRS",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_spec": "/openapi.json"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "EventRELY"
    }


"""
Endpoints para mantenimiento y keep-alive con Supabase
"""
@app.api_route("/keepalive", methods=["GET", "HEAD"], tags=["Maintenance"], include_in_schema=False)
async def keepalive(request: Request):
    """
    Keep-alive endpoint para evitar que Supabase pause el proyecto.
    Soporta tanto GET como HEAD (usado por UptimeRobot y otros monitores).

    Configurar un cron externo (UptimeRobot, cron-job.org) para llamar
    este endpoint cada 5-10 minutos.
    """
    from shared.infrastructure.persistence.configuration.database_configuration import get_db_session

    # Si es HEAD, solo devolver headers sin body
    if request.method == "HEAD":
        return {"status": "alive"}

    # Si es GET, hacer query a la base de datos
    try:
        async for session in get_db_session():
            # Ejecutar query simple para mantener la conexión activa
            result = await session.execute(text("SELECT 1"))
            db_status = result.scalar()

            return {
                "status": "alive",
                "timestamp": datetime.now(UTC).isoformat(),
                "database": "connected" if db_status == 1 else "disconnected",
                "message": "Keep-alive ping successful"
            }
    except Exception as e:
        logger.error(f"Keep-alive failed: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now(UTC).isoformat(),
            "database": "error",
            "message": str(e)
        }


@app.api_route("/ping", methods=["GET", "HEAD"], tags=["Maintenance"], include_in_schema=False)
async def ping(request: Request):
    """
    Simple ping endpoint sin interacción con base de datos.
    Útil para verificar que la API está respondiendo.
    Soporta GET y HEAD.
    """
    if request.method == "HEAD":
        return {"status": "pong"}

    return {
        "status": "pong",
        "timestamp": datetime.now(UTC).isoformat()
    }


@app.get("/health-check", tags=["Maintenance"])
async def health_check_with_db():
    """
    Health check completo con verificación de base de datos.
    Usa este endpoint si quieres monitorear también la conexión a PostgreSQL.
    """
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


"""
Run the application with Uvicorn
"""
if __name__ == "__main__":
    logger.info("Starting server via uvicorn...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )