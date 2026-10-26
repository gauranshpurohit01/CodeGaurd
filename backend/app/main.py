"""Main FastAPI entrypoint for CodeGuard."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine, Base
from app.api.routes import router


# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CodeGuard Compiler & Plagiarism Platform",
    description="End-to-end compiler construction project with hand-written lexers, parsers, canonicalization, C codegen, sandbox execution, and dual-level plagiarism detection.",
    version="1.0.0",
)

# Allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
@app.get("/api/health")
def health_check():
    return {"status": "ok", "platform": "CodeGuard"}
