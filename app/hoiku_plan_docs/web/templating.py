from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(PACKAGE_ROOT / "templates"))


def render_template(request: Request, template_name: str, **context):
    return templates.TemplateResponse(request, template_name, {"request": request, **context})
