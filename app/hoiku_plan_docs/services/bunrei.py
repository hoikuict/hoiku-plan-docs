from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from ..auth import StaffUser
from ..contracts import (
    ANNUAL_TERM_ORDER,
    DocumentStatus,
    DocumentType,
    SectionDefinition,
    annual_section_definitions,
    evidence_tags_for,
)
from ..models import PlanDocument, SectionBlock


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATHS = (
    REPO_ROOT / "gen_bunrei" / "bunrei.sqlite",
    REPO_ROOT / "gen_bunnrei" / "bunrei.sqlite",
)

MONTHLY_SECTION_ITEMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("monthly_goal", "今月のねらい", ("教育のねらい", "養護のねらい")),
    ("children_snapshot", "子どもの姿の捉え", ("前月末の子どもの姿",)),
    ("monthly_environment", "環境構成", ("環境構成・保育者の援助",)),
    ("monthly_support", "援助", ("活動内容", "環境構成・保育者の援助")),
    ("monthly_family_collaboration", "家庭連携", ("家庭との連携",)),
    ("monthly_reflection_viewpoint", "月末の振り返り観点", ("評価・反省",)),
)

ANNUAL_SECTION_ITEMS = {
    "annual_goal": ("期のねらい",),
    "outlook": ("予想される子どもの姿",),
    "environment": ("環境構成・保育者の援助",),
    "support": ("環境構成・保育者の援助",),
    "family_collaboration": ("家庭・地域との連携",),
    "reflection_viewpoint": ("期のねらい",),
}


@dataclass(frozen=True, slots=True)
class BunreiExample:
    id: str
    plan_type: str
    age_class: str
    time_unit: str | None
    month: int | None
    item: str
    ryoiki: str | None
    direction: str | None
    text: str
    needs_review: bool

    @property
    def label(self) -> str:
        parts = [self.item]
        if self.ryoiki:
            parts.append(self.ryoiki)
        if self.direction:
            parts.append(self.direction)
        return " / ".join(parts)


@dataclass(frozen=True, slots=True)
class BunreiCandidateGroup:
    section_key: str
    section_title: str
    examples: list[BunreiExample]


def bunrei_db_path() -> Path | None:
    env_path = os.getenv("HOIKU_BUNREI_DB_PATH")
    if env_path:
        path = Path(env_path)
        return path if path.exists() else None
    for path in DEFAULT_DB_PATHS:
        if path.exists():
            return path
    return None


def is_bunrei_available() -> bool:
    return bunrei_db_path() is not None


def _connect() -> sqlite3.Connection:
    path = bunrei_db_path()
    if path is None:
        raise FileNotFoundError("文例データベースが見つかりません")
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def _row_to_example(row: sqlite3.Row) -> BunreiExample:
    return BunreiExample(
        id=row["id"],
        plan_type=row["plan_type"],
        age_class=row["age_class"],
        time_unit=row["time_unit"],
        month=row["month"],
        item=row["item"],
        ryoiki=row["ryoiki"],
        direction=row["direction"],
        text=row["text"],
        needs_review=bool(row["needs_review"]),
    )


def age_class_options(plan_type: str) -> list[str]:
    with closing(_connect()) as con:
        rows = con.execute(
            "select distinct age_class from bunrei where plan_type = ? order by age_class",
            (plan_type,),
        ).fetchall()
    return [row["age_class"] for row in rows]


def count_examples() -> int:
    with closing(_connect()) as con:
        return int(con.execute("select count(*) from bunrei").fetchone()[0])


def _fetch_examples(
    *,
    plan_type: str,
    age_class: str,
    items: tuple[str, ...],
    month: int | None = None,
    time_unit: str | None = None,
    limit: int = 8,
) -> list[BunreiExample]:
    if not items:
        return []
    placeholders = ",".join("?" for _ in items)
    params: list[object] = [plan_type, age_class, *items]
    where = [f"plan_type = ?", "age_class = ?", f"item in ({placeholders})"]
    if month is not None:
        where.append("month = ?")
        params.append(month)
    if time_unit is not None:
        where.append("time_unit = ?")
        params.append(time_unit)

    sql = f"""
        select id, plan_type, age_class, time_unit, month, item, ryoiki, direction, text, needs_review
        from bunrei
        where {" and ".join(where)}
        order by item, ryoiki is null, ryoiki, direction, id
        limit ?
    """
    params.append(limit)
    with closing(_connect()) as con:
        rows = con.execute(sql, params).fetchall()
    return [_row_to_example(row) for row in rows]


def monthly_candidate_groups(age_class: str, month: int, *, limit_per_section: int = 8) -> list[BunreiCandidateGroup]:
    groups: list[BunreiCandidateGroup] = []
    for section_key, section_title, items in MONTHLY_SECTION_ITEMS:
        groups.append(
            BunreiCandidateGroup(
                section_key=section_key,
                section_title=section_title,
                examples=_fetch_examples(
                    plan_type="月案",
                    age_class=age_class,
                    month=month,
                    items=items,
                    limit=limit_per_section,
                ),
            )
        )
    return groups


def annual_candidate_groups(age_class: str, *, limit_per_section: int = 5) -> list[BunreiCandidateGroup]:
    groups: list[BunreiCandidateGroup] = []
    definitions = annual_section_definitions()
    definition_map = {definition.key: definition for definition in definitions}
    for definition in definitions:
        if definition.key == "annual_goal":
            groups.append(
                BunreiCandidateGroup(
                    section_key=definition.key,
                    section_title=definition.title,
                    examples=_fetch_examples(
                        plan_type="年案",
                        age_class=age_class,
                        time_unit="Ⅰ期",
                        items=ANNUAL_SECTION_ITEMS["annual_goal"],
                        limit=limit_per_section,
                    ),
                )
            )
            continue
        term_key, suffix = _annual_term_and_suffix(definition.key)
        time_unit = _annual_time_unit(term_key)
        groups.append(
            BunreiCandidateGroup(
                section_key=definition.key,
                section_title=definition_map[definition.key].title,
                examples=_fetch_examples(
                    plan_type="年案",
                    age_class=age_class,
                    time_unit=time_unit,
                    items=ANNUAL_SECTION_ITEMS.get(suffix, ()),
                    limit=limit_per_section,
                ),
            )
        )
    return groups


def selected_examples(selection: dict[str, list[str]]) -> dict[str, list[BunreiExample]]:
    ids = [example_id for values in selection.values() for example_id in values]
    if not ids:
        return {section_key: [] for section_key in selection}
    placeholders = ",".join("?" for _ in ids)
    with closing(_connect()) as con:
        rows = con.execute(
            f"""
            select id, plan_type, age_class, time_unit, month, item, ryoiki, direction, text, needs_review
            from bunrei
            where id in ({placeholders})
            """,
            ids,
        ).fetchall()
    by_id = {row["id"]: _row_to_example(row) for row in rows}
    return {
        section_key: [by_id[example_id] for example_id in values if example_id in by_id]
        for section_key, values in selection.items()
    }


def build_document_from_bunrei(
    *,
    document_type: DocumentType,
    title: str,
    owner_name: str,
    classroom_ref: str,
    user: StaffUser,
    section_definitions: list[SectionDefinition],
    selected_by_section: dict[str, list[BunreiExample]],
    school_year: int | None = None,
    target_month: str | None = None,
) -> PlanDocument:
    sections: list[SectionBlock] = []
    confirmation_items: list[str] = []
    for definition in section_definitions:
        examples = selected_by_section.get(definition.key, [])
        if examples:
            body = "\n".join(example.text for example in examples)
            source_refs = [f"bunrei.{example.id}" for example in examples]
            needs_confirmation = any(example.needs_review for example in examples)
            editor_note = "文例から作成しています。園やクラスの実態に合わせて修正してください。"
        else:
            body = ""
            source_refs = ["bunrei.unselected"]
            needs_confirmation = True
            editor_note = "文例を選ぶか、本文を入力してください。"
            confirmation_items.append(definition.title)
        sections.append(
            SectionBlock(
                section_key=definition.key,
                title=definition.title,
                body=body,
                source_refs=source_refs,
                evidence_tags=evidence_tags_for(source_refs),
                needs_confirmation=needs_confirmation,
                editor_note=editor_note,
            )
        )

    return PlanDocument(
        id=0,
        document_type=document_type,
        title=title,
        status=DocumentStatus.DRAFT,
        nursery_ref=user.nursery_ref,
        classroom_ref=classroom_ref,
        actor_ref=user.actor_ref,
        owner_name=owner_name,
        sections=sections,
        confirmation_items=confirmation_items,
        school_year=school_year,
        target_month=target_month,
    )


def _annual_term_and_suffix(section_key: str) -> tuple[str, str]:
    parts = section_key.split("_", 2)
    if len(parts) < 3:
        return "term_1", section_key
    return f"{parts[0]}_{parts[1]}", parts[2]


def _annual_time_unit(term_key: str) -> str:
    order = [key for key, _label in ANNUAL_TERM_ORDER]
    labels = ["Ⅰ期", "Ⅱ期", "Ⅲ期", "Ⅳ期"]
    if term_key in order:
        return labels[order.index(term_key)]
    return "Ⅰ期"
