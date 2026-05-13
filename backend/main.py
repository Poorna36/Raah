"""
RAAH Backend Core - Main FastAPI Application
Phase 2: Backend Core Implementation
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse

# Import backend modules
from .config import settings
from .db.session import get_db
from .db.models import Base, engine
from .auth.jwt import verify_token, get_current_user
from .auth.routes import router as auth_router
from .api.routes import router as api_router
from .commuter.routes import router as commuter_router
from .feedback.routes import router as feedback_router
from .ingestion.consumer import EventConsumer
from .alerts.engine import AlertEngine
from .alerts.websocket import websocket_router
from .zones.aggregator import ZoneAggregator
from .journey.reconstruction import JourneyReconstructor
from .hard_logic.engine import HardLogicEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
services: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting RAAH Backend Core...")
    
    try:
        # Initialize database tables
        logger.info("📊 Initializing database...")
        Base.metadata.create_all(bind=engine)
        
        # Initialize Redis connection
        logger.info("🔌 Connecting to Redis...")
        await init_redis()
        
        # Start background services
        logger.info("⚙️ Starting background services...")
        await start_services()
        
        logger.info("✅ RAAH Backend Core started successfully")
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start backend: {e}")
        raise
    finally:
        logger.info("🛑 Shutting down RAAH Backend Core...")
        await stop_services()

async def init_redis():
    """Initialize Redis connection"""
    try:
        import redis.asyncio as redis
        services['redis'] = await redis.from_url(settings.REDIS_URL)
        await services['redis'].ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️ Redis unavailable ({e}), some features may be limited")
        services['redis'] = None

async def start_services():
    """Start background services"""
    
    # Event Consumer - processes incoming events from Redis streams
    services['event_consumer'] = EventConsumer(
        redis_client=services.get('redis'),
        stream_names=['stream:anpr', 'stream:fastag', 'stream:cctv']
    )
    
    # Journey Reconstructor - builds complete journeys from events
    services['journey_reconstructor'] = JourneyReconstructor(
        db_factory=get_db
    )
    
    # Zone Aggregator - calculates zone states and baselines
    services['zone_aggregator'] = ZoneAggregator(
        db_factory=get_db,
        redis_client=services.get('redis')
    )
    
    # Hard Logic Engine - applies hard-coded business rules
    services['hard_logic_engine'] = HardLogicEngine(
        db_factory=get_db
    )
    
    # Alert Engine - generates and manages alerts
    services['alert_engine'] = AlertEngine(
        db_factory=get_db,
        redis_client=services.get('redis')
    )
    
    # Start background tasks
    if services['redis']:
        asyncio.create_task(services['event_consumer'].start())
        asyncio.create_task(services['zone_aggregator'].start())
        asyncio.create_task(services['alert_engine'].start())
        
    logger.info("✅ Background services started")

async def stop_services():
    """Stop background services"""
    for service_name, service in services.items():
        if hasattr(service, 'stop'):
            try:
                await service.stop()
                logger.info(f"🛑 Stopped {service_name}")
            except Exception as e:
                logger.error(f"❌ Error stopping {service_name}: {e}")
    
    if services.get('redis'):
        await services['redis'].close()
        logger.info("🔌 Redis connection closed")

# Create FastAPI app
app = FastAPI(
    title="RAAH Backend Core",
    description="Smart Highway Monitoring System - Backend Core API",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }
    
    # Check each service
    for service_name, service in services.items():
        if service:
            health_status["services"][service_name] = "active"
        else:
            health_status["services"][service_name] = "inactive"
    
    return health_status

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RAAH Backend Core API",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(api_router, prefix="/api/v1", tags=["api"])
app.include_router(commuter_router, prefix="/api/v1/commuter", tags=["commuter"])
app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["feedback"])
app.include_router(websocket_router, prefix="/ws", tags=["websocket"])

# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP Exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "timestamp": datetime.now().isoformat()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "timestamp": datetime.now().isoformat()}
    )

# Dependency to get services
def get_service(service_name: str):
    """Get a service instance"""
    def dependency():
        service = services.get(service_name)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service {service_name} not available"
            )
        return service
    return dependency

# Protected endpoint example
@app.get("/api/v1/protected")
async def protected_endpoint(
    current_user: dict = Depends(get_current_user),
    alert_engine: AlertEngine = Depends(get_service("alert_engine"))
):
    """Example protected endpoint"""
    return {
        "message": "This is a protected endpoint",
        "user": current_user,
        "services_active": len([s for s in services.values() if s]) > 0
    }

# System status endpoint
@app.get("/api/v1/system/status")
async def system_status():
    """Get comprehensive system status"""
    status_info = {
        "backend": {
            "status": "running",
            "version": "2.0.0",
            "timestamp": datetime.now().isoformat()
        },
        "services": {},
        "database": {"status": "connected"},
        "redis": {"status": "connected" if services.get("redis") else "disconnected"}
    }
    
    # Add service statuses
    for service_name, service in services.items():
        if service and hasattr(service, 'get_status'):
            try:
                status_info["services"][service_name] = await service.get_status()
            except:
                status_info["services"][service_name] = {"status": "unknown"}
        else:
            status_info["services"][service_name] = {"status": "inactive"}
    
    return status_info

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )