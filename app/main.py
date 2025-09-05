from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.routers import auth, chat, agent, user, llm_proxy
import logging
from contextlib import asynccontextmanager


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    # Startup
    logger.info("Starting AI Chat Platform API")
    
    # Health check external services
    from app.services.litellm_service import litellm_service
    
    # Check LiteLLM service
    litellm_healthy = await litellm_service.health_check()
    logger.info(f"LiteLLM service health: {'OK' if litellm_healthy else 'FAILED'}")
    
    if not litellm_healthy:
        logger.warning("LiteLLM service is not responding - billing may be affected")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Chat Platform API")


# Create FastAPI application
app = FastAPI(
    title="AI Chat Platform API",
    description="Backend API for AI Chat Platform with Letta and LiteLLM integration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled error on {request.method} {request.url}: {exc}", exc_info=True)
    
    if settings.environment == "development":
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


# Health check endpoint
@app.get("/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "service": "AI Chat Platform API",
        "version": "1.0.0",
        "environment": settings.environment
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Chat Platform API",
        "version": "1.0.0",
        "docs": "/docs" if settings.environment == "development" else "Not available in production"
    }


# Include routers
app.include_router(
    auth.router,
    prefix=f"{settings.api_v1_prefix}/auth",
    tags=["Authentication"]
)

app.include_router(
    chat.router,
    prefix=f"{settings.api_v1_prefix}/chat",
    tags=["Chat"]
)

app.include_router(
    agent.router,
    prefix=f"{settings.api_v1_prefix}/agent",
    tags=["Agent"]
)

app.include_router(
    user.router,
    prefix=f"{settings.api_v1_prefix}/user",
    tags=["User"]
)

app.include_router(
    llm_proxy.router,
    tags=["LLM Proxy"]
)


# Development endpoints
if settings.environment == "development":
    
    @app.get("/dev/services-status")
    async def services_status():
        """Check status of external services (development only)"""
        from app.services.litellm_service import litellm_service
        
        services = {
            "letta": {
                "url": settings.letta_base_url,
                "status": "unknown"  # Would need to implement health check
            },
            "litellm": {
                "url": settings.litellm_base_url,
                "status": "healthy" if await litellm_service.health_check() else "unhealthy"
            },
            "supabase": {
                "url": settings.supabase_url,
                "status": "configured"  # Supabase client doesn't have easy health check
            }
        }
        
        return {
            "environment": settings.environment,
            "services": services
        }
    
    @app.get("/dev/config")
    async def get_config():
        """Get current configuration (development only, sensitive data hidden)"""
        return {
            "environment": settings.environment,
            "log_level": settings.log_level,
            "api_prefix": settings.api_v1_prefix,
            "letta_base_url": settings.letta_base_url,
            "litellm_base_url": settings.litellm_base_url,
            "supabase_url": settings.supabase_url,
            "allowed_origins": settings.get_allowed_origins(),
            "has_supabase_keys": bool(settings.supabase_anon_key and settings.supabase_service_key),
            "has_litellm_key": bool(settings.litellm_master_key),
            "has_letta_token": bool(settings.letta_api_token)
        }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )