from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from ...auth import CurrentUser, require_can_edit, require_classroom_access
from ...auth import DEFAULT_CLASSROOM_REFS
from ...contracts import DocumentType
from ...services.generators import generate_annual_plan, generate_monthly_plan
from ...store import document_store
from ..templating import render_template


router = APIRouter(tags=["plans"])


def _annual_documents_for_user(user: CurrentUser):
    classroom_refs = None if user.is_admin else user.classroom_refs
    return document_store.list(
        nursery_ref=user.nursery_ref,
        classroom_refs=classroom_refs,
        document_type=DocumentType.ANNUAL_PLAN,
    )


@router.get("/annual-plans/new")
def new_annual_plan(request: Request, user: CurrentUser):
    return render_template(
        request,
        "annual_plans/form.html",
        user=user,
        default_classroom_ref=user.classroom_refs[0] if user.classroom_refs else DEFAULT_CLASSROOM_REFS[0],
    )


@router.post("/annual-plans")
def create_annual_plan(
    user: CurrentUser,
    school_year: Annotated[str, Form()] = "2026",
    class_name: Annotated[str, Form()] = "",
    classroom_ref: Annotated[str, Form()] = "",
    owner_name: Annotated[str, Form()] = "",
    class_outlook: Annotated[str, Form()] = "",
    focus_growth: Annotated[str, Form()] = "",
    annual_events: Annotated[str, Form()] = "",
    seasonal_context: Annotated[str, Form()] = "",
    care_points: Annotated[str, Form()] = "",
    family_collaboration_policy: Annotated[str, Form()] = "",
    health_safety_policy: Annotated[str, Form()] = "",
    preferred_expressions: Annotated[str, Form()] = "",
    term_1_note: Annotated[str, Form()] = "",
    term_2_note: Annotated[str, Form()] = "",
    term_3_note: Annotated[str, Form()] = "",
    term_4_note: Annotated[str, Form()] = "",
):
    require_can_edit(user)
    selected_classroom_ref = classroom_ref or (user.classroom_refs[0] if user.classroom_refs else DEFAULT_CLASSROOM_REFS[0])
    require_classroom_access(user, selected_classroom_ref)
    document = generate_annual_plan(
        {
            "school_year": school_year,
            "class_name": class_name,
            "classroom_ref": selected_classroom_ref,
            "owner_name": owner_name,
            "class_outlook": class_outlook,
            "focus_growth": focus_growth,
            "annual_events": annual_events,
            "seasonal_context": seasonal_context,
            "care_points": care_points,
            "family_collaboration_policy": family_collaboration_policy,
            "health_safety_policy": health_safety_policy,
            "preferred_expressions": preferred_expressions,
            "term_1_note": term_1_note,
            "term_2_note": term_2_note,
            "term_3_note": term_3_note,
            "term_4_note": term_4_note,
        },
        user,
    )
    created = document_store.create(document)
    return RedirectResponse(url=f"/documents/{created.id}", status_code=303)


@router.get("/monthly-plans/new")
def new_monthly_plan(request: Request, user: CurrentUser):
    return render_template(
        request,
        "monthly_plans/form.html",
        user=user,
        annual_documents=_annual_documents_for_user(user),
        default_classroom_ref=user.classroom_refs[0] if user.classroom_refs else DEFAULT_CLASSROOM_REFS[0],
    )


@router.post("/monthly-plans")
def create_monthly_plan(
    user: CurrentUser,
    target_month: Annotated[str, Form()] = "",
    class_name: Annotated[str, Form()] = "",
    classroom_ref: Annotated[str, Form()] = "",
    owner_name: Annotated[str, Form()] = "",
    related_annual_summary: Annotated[str, Form()] = "",
    previous_reflection: Annotated[str, Form()] = "",
    current_children_snapshot: Annotated[str, Form()] = "",
    play_interests: Annotated[str, Form()] = "",
    seasonal_context: Annotated[str, Form()] = "",
    family_context: Annotated[str, Form()] = "",
    class_notes: Annotated[str, Form()] = "",
):
    require_can_edit(user)
    selected_classroom_ref = classroom_ref or (user.classroom_refs[0] if user.classroom_refs else DEFAULT_CLASSROOM_REFS[0])
    require_classroom_access(user, selected_classroom_ref)
    document = generate_monthly_plan(
        {
            "target_month": target_month,
            "class_name": class_name,
            "classroom_ref": selected_classroom_ref,
            "owner_name": owner_name,
            "related_annual_summary": related_annual_summary,
            "previous_reflection": previous_reflection,
            "current_children_snapshot": current_children_snapshot,
            "play_interests": play_interests,
            "seasonal_context": seasonal_context,
            "family_context": family_context,
            "class_notes": class_notes,
        },
        user,
    )
    created = document_store.create(document)
    return RedirectResponse(url=f"/documents/{created.id}", status_code=303)
