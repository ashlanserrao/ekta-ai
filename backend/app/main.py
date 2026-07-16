import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import ResponseValidationError
from fastapi.responses import JSONResponse

from backend.app.config import settings
from backend.app.database import init_db
from backend.app.simulator import StadiumSimulator
from backend.app.middleware.security_headers import SecurityHeadersMiddleware

from backend.app.routers.stadium import router as stadium_router
from backend.app.routers.chat import router as chat_router
from backend.app.routers.alerts import router as alerts_router
from backend.app.routers.auth import router as auth_router

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Startup / Shutdown Lifespan
active_simulator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global active_simulator
    logger.info("Initializing database...")
    init_db()
    
    logger.info("Starting Digital Twin Simulator...")
    if active_simulator is None or not active_simulator.is_alive():
        active_simulator = StadiumSimulator()
        active_simulator.start()
    
    yield
    
    if active_simulator and active_simulator.is_alive():
        logger.info("Stopping Digital Twin Simulator...")
        active_simulator.stop()

# Disable OpenAPI Docs in Production
docs_url = None if settings.ENV == "production" else "/docs"
redoc_url = None if settings.ENV == "production" else "/redoc"

app = FastAPI(
    title="EktaAI API",
    description="GenAI-powered stadium operations assistant backend for FIFA World Cup 2026",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url
)

@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(request: Request, exc: ResponseValidationError):
    logger.error(f"Response validation error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Response format validation error."}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )

# Security & CORS configuration
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stadium_router)
app.include_router(chat_router)
app.include_router(alerts_router)
app.include_router(auth_router)

# Health endpoint at root
@app.get("/")
def read_root():
    return {"app": "EktaAI API", "status": "healthy", "version": "1.0.0"}
