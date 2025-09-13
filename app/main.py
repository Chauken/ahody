import time

from fastapi import FastAPI

from app.api.main import api_router
from app.config import settings
from app.util import setup_logging

setup_logging()
start_time = time.time()


def lifespan(app: FastAPI):
    # placeholder for any startup tasks
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    uptime = time.time() - start_time
    return {
        "status": "ok",
        "uptime": f"{uptime:.2f}s",
    }
