from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from . import auth, products, s3_routes

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=True)

app = FastAPI(
    title="Inventory API - EBS Deployment",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(s3_routes.router, prefix="/api")

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Inventory API- EBS Deployment",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    """Detailed health check"""
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    try:
        from .sqs.worker import start_background_worker
        import asyncio
        asyncio.create_task(start_background_worker(batch_size=10, polling_interval=5))
        print("Background worker started for SQS/SNS notifications")
    except Exception as e:
        print(f"Background worker not started: {e}")