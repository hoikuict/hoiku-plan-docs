from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from ...auth import DEFAULT_CLASSROOM_REFS, CurrentUser, require_can_edit, require_classroom_access
from ...contracts import DocumentType, annual_section_definitions
from ...services.bunrei import (
    age_class_options,
    annual_candidate_groups,
    build_document_from_bunrei,
    count_examples,
    is_bunrei_available,
    monthly_candidate_groups,
    selected_examples,
)
from ...store import document_store
from ..templating import render_template


router = APIRouter(prefix="/bunrei", tags=["bunrei"])


@router.get("/monthly")
def monthly_bunrei_selector(
    request: Request,
    user: CurrentUser,
    age_class: str = "5歳児",
    month: int = 4,
):
    _ensure_available()
    return render_template(
        request,
        "bunrei/monthly.html",
        user=user,
        age_options=age_class_options("月案"),
        selected_age_class=age_class,
        selected_month=month,
        month_options=[4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3],
        groups=monthly_candidate_groups(age_class, month),
        total_examples=count_examples(),
        default_classroom_ref=user.classroom_refs[0] if user.classroom_refs else DEFAULT_CLASSROOM_REFS[0],
    )


@router.post("/monthly")
async def create_monthly_from_bunrei(request: Request, user: CurrentUser):
    _ensure_available()
    require_can_edit(user)
    form = await request.form()
    target_month = str(form.get("target_month") or "2026-04")
    class_name = str(form.get("class_name") or "5歳児 ひまわり組").strip()
    classroom_ref = str(form.get("classroom_ref") or (user.classroom_refs[0] if user.classroom_refs else DEFAULT_CLASSROOM_REFS[0]))
    owner_name = str(form.get("owner_name") or user.name).strip()
    require_classroom_access(user, classroom_ref)

    selection = {
        section_key.removeprefix("section_"): list(form.getlist(section_key))
        for section_key in form
        if section_key.startswith("section_")
    }
    selected_by_section = selected_examples(selection)
    groups = monthly_candidate_groups(str(form.get("age_class") or "5歳児"), int(form.get("month") or 4), limit_per_section=1)
    definitions = [
        _definition(group.section_key, group.section_title)
        for group in groups
    ]
    document = build_document_from_bunrei(
        document_type=DocumentType.MONTHLY_PLAN,
        title=f"{target_month} 月案（{class_name}）",
        owner_name=owner_name,
        classroom_ref=classroom_ref,
        user=user,
        section_definitions=definitions,
        selected_by_section=selected_by_section,
        target_month=target_month,
    )
    created = document_store.create(document)
    return RedirectResponse(url=f"/documents/{created.id}/edit", status_code=303)


@router.get("/annual")
def annual_bunrei_selector(
    request: Request,
    user: CurrentUser,
    age_class: str = "5歳児",
    school_year: int = 2026,
):
    _ensure_available()
    return render_template(
        request,
        "bunrei/annual.html",
        user=user,
        age_options=age_class_options("年案"),
        selected_age_class=age_class,
        school_year=school_year,
        groups=annual_candidate_groups(age_class),
        total_examples=count_examples(),
        default_classroom_ref=user.classroom_refs[0] if user.classroom_refs else DEFAULT_CLASSROOM_REFS[0],
    )


@router.post("/annual")
async def create_annual_from_bunrei(request: Request, user: CurrentUser):
    _ensure_available()
    require_can_edit(user)
    form = await request.form()
    school_year = int(form.get("school_year") or 2026)
    class_name = str(form.get("class_name") or "5歳児 ひまわり組").strip()
    classroom_ref = str(form.get("classroom_ref") or (user.classroom_refs[0] if user.classroom_refs else DEFAULT_CLASSROOM_REFS[0]))
    owner_name = str(form.get("owner_name") or user.name).strip()
    require_classroom_access(user, classroom_ref)

    selection = {
        section_key.removeprefix("section_"): list(form.getlist(section_key))
        for section_key in form
        if section_key.startswith("section_")
    }
    document = build_document_from_bunrei(
        document_type=DocumentType.ANNUAL_PLAN,
        title=f"{school_year}年度 年案（{class_name}）",
        owner_name=owner_name,
        classroom_ref=classroom_ref,
        user=user,
        section_definitions=annual_section_definitions(),
        selected_by_section=selected_examples(selection),
        school_year=school_year,
    )
    created = document_store.create(document)
    return RedirectResponse(url=f"/documents/{created.id}/edit", status_code=303)


def _definition(section_key: str, section_title: str):
    from ...contracts import SectionDefinition

    return SectionDefinition(section_key, section_title, "文例選択")


def _ensure_available() -> None:
    if not is_bunrei_available():
        raise HTTPException(status_code=503, detail="文例データベースが見つかりません")
