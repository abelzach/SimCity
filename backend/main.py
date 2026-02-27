"""
SimCity AI Backend - FastAPI application entry point.
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from api.routes import router

app = FastAPI(
    title="SimCity AI",
    description="Autonomous Digital Twin for Urban Policy Testing — Kochi, India",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "SimCity AI",
        "version": "1.0.0",
        "city": "Kochi, Kerala, India",
        "status": "operational",
        "docs": "/docs",
    }


@app.on_event("startup")
async def startup():
    logger.info("SimCity AI backend starting up...")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — LLM-powered agents will use fallbacks")
    else:
        logger.info("Anthropic API key loaded")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
