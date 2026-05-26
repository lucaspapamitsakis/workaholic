from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .database import init_db, SessionLocal
from .sync import sync_notes
from .config import load_config
from .routers import sync, exercises, sessions, benchmarks, config


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # Run sync on startup
    app_config = load_config()
    if app_config.get("obsidian_vault_path"):
        db = SessionLocal()
        try:
            result = sync_notes(db, app_config)
            if result.notifications:
                print("\n=== Sync Notifications ===")
                for n in result.notifications:
                    print(f"  [{n.notification_type}] {n.message}")
                print("==========================\n")
            if result.errors:
                print("\n=== Sync Errors ===")
                for e in result.errors:
                    print(f"  {e}")
                print("===================\n")
            print(
                f"Sync complete: {result.files_parsed} files parsed, "
                f"{result.sets_added} sets added."
            )
        finally:
            db.close()

    yield


app = FastAPI(
    title="Workout Progression Tracker",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sync.router)
app.include_router(exercises.router)
app.include_router(sessions.router)
app.include_router(benchmarks.router)
app.include_router(config.router)

# Serve frontend static files if built
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
