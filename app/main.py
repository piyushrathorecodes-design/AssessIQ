import logging
import os
from fastapi import FastAPI
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

from app.api.routes import router
from app.api.exceptions import setup_exception_handlers
from app.config.settings import settings

logger = logging.getLogger("shl_recommender")

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d) - %(message)s"
)

def create_app() -> FastAPI:
    """FastAPI Application factory."""
    app = FastAPI(
        title="SHL Assessment Recommendation Agent",
        description="Conversational RAG Agent matching recruiters to SHL Assessment solutions.",
        version="1.0.0"
    )
    
    # Check index availability on start
    if not os.path.exists(settings.faiss_index_path) or not os.path.exists(settings.metadata_path):
        logger.warning(
            "FAISS index or metadata files are missing! "
            "Please ensure you run 'python scripts/scrape.py' and 'python scripts/build_index.py' "
            "to populate the database prior to querying /chat."
        )
    else:
        logger.info("Search indices discovered. Ready to retrieve catalog data.")
        
    # Include endpoints
    app.include_router(router)
    
    # Exception mapping
    setup_exception_handlers(app)
    
    return app

app = create_app()
