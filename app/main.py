"""FastAPI main entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import intake
from app.routers import documents
from app.routers import chat
from app.routers import payment

app = FastAPI(
    title="Eviction Defense — Automated Self-Help Paperwork",
    description="AI-powered eviction defense document preparation. Supports 20 states with official court forms, legal motions, checklists, hearing scripts, and rental assistance resources.",
    version="0.1.0",
)

# CORS - allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "https://evictions.help",
        "https://www.evictions.help",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(intake.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(payment.router)

# Serve frontend static files

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "eviction-defense"}


@app.get("/")
def root():
    from fastapi.responses import FileResponse
    return FileResponse("app/static/index.html")


@app.get("/chat")
def chat_page():
    from fastapi.responses import FileResponse
    return FileResponse("app/static/chat.html")


app.mount("/static", StaticFiles(directory="app/static"), name="static")
