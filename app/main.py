"""FastAPI application entry point."""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from app.api import router
from app.config import settings
import logging
import json

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Agentic Honeypot API",
    description="AI-powered honeypot system for scam detection and intelligence extraction",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with detailed logging."""
    errors = exc.errors()
    error_details = []
    for error in errors:
        error_details.append({
            "field": ".".join(str(loc) for loc in error.get("loc", [])),
            "message": error.get("msg", "Validation error"),
            "type": error.get("type", "unknown")
        })
    
    # Log the full request body for debugging
    try:
        body = await request.body()
        logger.error(f"Validation error on {request.url.path}")
        logger.error(f"Request body: {body.decode('utf-8')}")
        logger.error(f"Validation errors: {json.dumps(error_details, indent=2)}")
    except Exception as e:
        logger.error(f"Error logging validation details: {e}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "detail": "Request validation failed",
            "errors": error_details
        }
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """Actions to perform on application startup."""
    logger.info("Starting Agentic Honeypot API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"API Key configured: {settings.api_key != 'your-secret-api-key-here'}")


@app.on_event("shutdown")
async def shutdown_event():
    """Actions to perform on application shutdown."""
    logger.info("Shutting down Agentic Honeypot API")




@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run."""
    return {
        "status": "healthy",
        "service": "honeypot-api",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "title": "Agentic Honeypot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.environment == "development"
    )
