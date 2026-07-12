from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.configs.global_config import upload_info
from src.models.settings.database_connection_handler import engine
from src.models.settings.metadata import metadata
from src.models.entities import users, refunds  # pylint: disable=unused-import
from src.main.routes.auth_routes import auth_routes
from src.main.routes.refund_routes import refund_routes


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/receipts", StaticFiles(directory=upload_info["UPLOAD_DIR"]), name="receipts")

app.include_router(auth_routes)
app.include_router(refund_routes)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
