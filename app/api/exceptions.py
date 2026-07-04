import logging
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse

logger = logging.getLogger("shl_recommender")

def setup_exception_handlers(app: FastAPI):
    """Register global exception handlers for the FastAPI application."""
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        logger.error(f"Value Error: {exc} on request {request.url}")
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)}
        )
        
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled Exception: {exc} on request {request.url}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please verify model configuration and API keys."}
        )
