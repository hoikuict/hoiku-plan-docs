from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from ...auth import (
    DEFAULT_ACTOR_REF,
    DEFAULT_CLASSROOM_REFS,
    DEFAULT_NURSERY_REF,
    DEFAULT_STAFF_NAME,
    CurrentUser,
    clear_staff_session,
    set_staff_session,
)
from ...contracts import ROLE_LABELS, Role
from ..templating import render_template


router = APIRouter(prefix="/staff", tags=["staff-auth"])


@router.get("/login")
def login_form(request: Request, user: CurrentUser, redirect: str = "/"):
    return render_template(
        request,
        "staff_auth/login.html",
        user=user,
        redirect=redirect,
        role_options=[(role, ROLE_LABELS[role]) for role in Role],
    )


@router.post("/session")
def set_session(
    role: Annotated[str, Form()] = Role.CAN_EDIT.value,
    actor_ref: Annotated[str, Form()] = DEFAULT_ACTOR_REF,
    nursery_ref: Annotated[str, Form()] = DEFAULT_NURSERY_REF,
    classroom_refs: Annotated[str, Form()] = ",".join(DEFAULT_CLASSROOM_REFS),
    name: Annotated[str, Form()] = DEFAULT_STAFF_NAME,
    redirect: Annotated[str, Form()] = "/",
):
    response = RedirectResponse(url=redirect or "/", status_code=303)
    selected_role = Role(role) if role in {item.value for item in Role} else Role.CAN_EDIT
    set_staff_session(
        response,
        role=selected_role,
        actor_ref=actor_ref,
        nursery_ref=nursery_ref,
        classroom_refs=tuple(item.strip() for item in classroom_refs.split(",") if item.strip()),
        name=name,
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    clear_staff_session(response)
    return response
