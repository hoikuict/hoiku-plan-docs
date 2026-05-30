from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    VIEW_ONLY = "view_only"
    CAN_EDIT = "can_edit"
    ADMIN = "admin"


ROLE_LABELS: dict[Role, str] = {
    Role.VIEW_ONLY: "閲覧のみ",
    Role.CAN_EDIT: "編集可",
    Role.ADMIN: "管理者",
}


class DocumentType(StrEnum):
    ANNUAL_PLAN = "annual_plan"
    MONTHLY_PLAN = "monthly_plan"


DOCUMENT_TYPE_LABELS: dict[DocumentType, str] = {
    DocumentType.ANNUAL_PLAN: "年案",
    DocumentType.MONTHLY_PLAN: "月案",
}


DOCUMENT_TYPE_ALIASES = {
    "annual": DocumentType.ANNUAL_PLAN,
    "monthly": DocumentType.MONTHLY_PLAN,
}


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


STATUS_LABELS: dict[DocumentStatus, str] = {
    DocumentStatus.DRAFT: "下書き",
    DocumentStatus.IN_REVIEW: "レビュー待ち",
    DocumentStatus.APPROVED: "承認済み",
    DocumentStatus.REJECTED: "差戻し",
    DocumentStatus.ARCHIVED: "アーカイブ",
}


STATUS_ALIASES = {
    "returned": DocumentStatus.REJECTED,
}


SOURCE_REF_PREFIX_TAGS = {
    "profile.": "園方針",
    "knowledge.": "公的根拠",
    "form.": "入力",
    "annual.": "入力",
    "monthly.": "入力",
    "bunrei.": "文例",
    "outline.": "AI構成",
    "linking.": "AI構成",
}


@dataclass(frozen=True, slots=True)
class SectionDefinition:
    key: str
    title: str
    purpose: str


ANNUAL_TERM_ORDER: tuple[tuple[str, str], ...] = (
    ("term_1", "4〜6月"),
    ("term_2", "7〜9月"),
    ("term_3", "10〜12月"),
    ("term_4", "1〜3月"),
)

ANNUAL_BASE_SECTIONS: tuple[SectionDefinition, ...] = (
    SectionDefinition("annual_goal", "年間の大きなねらい", "年間全体の軸"),
)

ANNUAL_TERM_SECTION_SUFFIXES: tuple[tuple[str, str, str], ...] = (
    ("outlook", "見通し", "各期の見通し"),
    ("environment", "環境構成", "各期の環境構成"),
    ("support", "援助", "各期の援助方針"),
    ("family_collaboration", "家庭連携", "各期の家庭との連携"),
    ("reflection_viewpoint", "振り返り観点", "各期の確認観点"),
)

MONTHLY_SECTIONS: tuple[SectionDefinition, ...] = (
    SectionDefinition("monthly_goal", "今月のねらい", "月案の中心目標"),
    SectionDefinition("children_snapshot", "子どもの姿の捉え", "現在の姿の整理"),
    SectionDefinition("monthly_environment", "環境構成", "月の環境構成"),
    SectionDefinition("monthly_support", "援助", "月の援助方針"),
    SectionDefinition("monthly_family_collaboration", "家庭連携", "保護者との連携方針"),
    SectionDefinition("monthly_reflection_viewpoint", "月末の振り返り観点", "次月につなぐ確認観点"),
)


def annual_section_definitions() -> list[SectionDefinition]:
    definitions = list(ANNUAL_BASE_SECTIONS)
    for term_key, term_label in ANNUAL_TERM_ORDER:
        for suffix, short_title, purpose in ANNUAL_TERM_SECTION_SUFFIXES:
            definitions.append(
                SectionDefinition(
                    key=f"{term_key}_{suffix}",
                    title=f"{term_label}の{short_title}",
                    purpose=purpose,
                )
            )
    return definitions


def section_definitions(document_type: DocumentType) -> list[SectionDefinition]:
    if document_type == DocumentType.ANNUAL_PLAN:
        return annual_section_definitions()
    if document_type == DocumentType.MONTHLY_PLAN:
        return list(MONTHLY_SECTIONS)
    raise ValueError(f"Unsupported document_type: {document_type}")


def normalize_document_type(raw_value: str) -> DocumentType:
    value = (raw_value or "").strip()
    if value in DOCUMENT_TYPE_ALIASES:
        return DOCUMENT_TYPE_ALIASES[value]
    return DocumentType(value)


def normalize_status(raw_value: str) -> DocumentStatus:
    value = (raw_value or "").strip()
    if value in STATUS_ALIASES:
        return STATUS_ALIASES[value]
    return DocumentStatus(value)


def evidence_tags_for(source_refs: list[str]) -> list[str]:
    tags: list[str] = []
    for source_ref in source_refs:
        for prefix, tag in SOURCE_REF_PREFIX_TAGS.items():
            if source_ref.startswith(prefix) and tag not in tags:
                tags.append(tag)
    return tags or ["入力"]
