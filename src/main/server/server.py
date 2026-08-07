from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.configs.settings import settings
from src.models.entities import users, refunds, refund_reviews  # pylint: disable=unused-import
from src.main.routes.auth_routes import auth_routes
from src.main.routes.refund_routes import refund_routes
from src.main.routes.user_routes import user_routes
from src.main.routes.file_routes import file_routes


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # The schema is owned by Alembic migrations (`alembic upgrade head`), not by
    # the application boot. Keeping metadata.create_all here would silently mask
    # a migration that was never applied: it creates missing tables and ignores
    # missing columns, so the app would start against a half-updated schema.
    yield


app = FastAPI(lifespan=lifespan)

# Was hardcoded to http://localhost:5173, which meant no deployed frontend
# could ever reach this API. Settings validates the value and refuses a
# wildcard or a localhost origin when ENVIRONMENT=production, so the insecure
# configuration is impossible rather than merely discouraged.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uploaded files are NOT served statically: the UUID filenames would be
# capability URLs, granting anyone who ever saw a link permanent access even
# after losing access to the refund. They go through authenticated routes
# instead (GET /refunds/{id}/receipt and GET /users/{id}/avatar).

app.include_router(auth_routes)
app.include_router(refund_routes)
app.include_router(user_routes)
# Only used by the local storage backend; with S3 the browser never comes here.
app.include_router(file_routes)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
