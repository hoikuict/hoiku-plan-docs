from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import __version__
from .web.routers.bunrei import router as bunrei_router
from .web.routers.documents import router as documents_router
from .web.routers.home import router as home_router
from .web.routers.plans import router as plans_router
from .web.routers.staff_auth import router as staff_auth_router


PACKAGE_ROOT = Path(__file__).resolve().parent


def create_app() -> FastAPI:
    app = FastAPI(title="hoiku-plan-docs", version=__version__)
    app.mount("/static", StaticFiles(directory=str(PACKAGE_ROOT / "static")), name="static")
    app.include_router(home_router)
    app.include_router(documents_router)
    app.include_router(bunrei_router)
    app.include_router(plans_router)
    app.include_router(staff_auth_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "hoiku-plan-docs", "version": __version__}

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("hoiku_plan_docs.main:app", host="127.0.0.1", port=8020, reload=True)
