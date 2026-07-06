"""FastAPI main entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import intake
from app.routers import documents

app = FastAPI(
    title="Eviction Defense API",
    description="Self-help eviction paperwork preparation for Florida tenants",
    version="0.1.0",
)

# CORS - allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],  # Frontend dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(intake.router)
app.include_router(documents.router)

# Serve frontend static files

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "eviction-defense"}


@app.get("/")
def root():
    from fastapi.responses import FileResponse
    return FileResponse("app/static/index.html")


app.mount("/static", StaticFiles(directory="app/static"), name="static")
