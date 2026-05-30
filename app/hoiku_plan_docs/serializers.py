from __future__ import annotations

from .models import PlanDocument, SectionBlock


def section_to_dict(section: SectionBlock) -> dict[str, object]:
    return {
        "section_key": section.section_key,
        "title": section.title,
        "body": section.body,
        "source_refs": section.source_refs,
        "evidence_tags": section.evidence_tags,
        "needs_confirmation": section.needs_confirmation,
        "editor_note": section.editor_note,
    }


def document_to_dict(document: PlanDocument) -> dict[str, object]:
    return {
        "id": document.id,
        "document_type": document.document_type.value,
        "document_type_label": document.document_type_label,
        "status": document.status.value,
        "status_label": document.status_label,
        "title": document.title,
        "nursery_ref": document.nursery_ref,
        "classroom_ref": document.classroom_ref,
        "actor_ref": document.actor_ref,
        "owner_name": document.owner_name,
        "school_year": document.school_year,
        "target_month": document.target_month,
        "sections": [section_to_dict(section) for section in document.sections],
        "confirmation_items": document.confirmation_items,
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
    }
