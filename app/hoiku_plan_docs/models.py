from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .contracts import DOCUMENT_TYPE_LABELS, STATUS_LABELS, DocumentStatus, DocumentType


@dataclass(slots=True)
class SectionBlock:
    section_key: str
    title: str
    body: str
    source_refs: list[str]
    evidence_tags: list[str]
    needs_confirmation: bool = False
    editor_note: str | None = None


@dataclass(slots=True)
class PlanDocument:
    id: int
    document_type: DocumentType
    title: str
    status: DocumentStatus
    nursery_ref: str
    classroom_ref: str
    actor_ref: str
    owner_name: str
    sections: list[SectionBlock]
    confirmation_items: list[str] = field(default_factory=list)
    school_year: int | None = None
    target_month: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def document_type_label(self) -> str:
        return DOCUMENT_TYPE_LABELS.get(self.document_type, self.document_type.value)

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status.value)

    @property
    def can_edit_body(self) -> bool:
        return self.status in {DocumentStatus.DRAFT, DocumentStatus.REJECTED}

    @property
    def nursery_label(self) -> str:
        return self.nursery_ref

    @property
    def classroom_label(self) -> str:
        return self.classroom_ref
