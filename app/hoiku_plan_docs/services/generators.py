from __future__ import annotations

from .text import clean_text, confirmation_items
from ..auth import StaffUser
from ..contracts import (
    ANNUAL_TERM_ORDER,
    DocumentStatus,
    DocumentType,
    MONTHLY_SECTIONS,
    SectionDefinition,
    annual_section_definitions,
    evidence_tags_for,
)
from ..models import PlanDocument, SectionBlock


def _section(
    definition: SectionDefinition,
    body: str,
    source_refs: list[str],
    *,
    needs_confirmation: bool = False,
    editor_note: str | None = None,
) -> SectionBlock:
    return SectionBlock(
        section_key=definition.key,
        title=definition.title,
        body=body,
        source_refs=source_refs,
        evidence_tags=evidence_tags_for(source_refs),
        needs_confirmation=needs_confirmation,
        editor_note=editor_note,
    )


def _term_label(term_key: str) -> str:
    return dict(ANNUAL_TERM_ORDER).get(term_key, term_key)


def _needs_note(value: str, label: str) -> tuple[bool, str | None]:
    if value:
        return False, None
    return True, f"{label}が未入力のため、担任確認が必要です。"


def generate_annual_plan(data: dict[str, str], user: StaffUser) -> PlanDocument:
    school_year = int(clean_text(data.get("school_year")) or "2026")
    class_name = clean_text(data.get("class_name")) or "クラス未設定"
    classroom_ref = clean_text(data.get("classroom_ref")) or user.classroom_refs[0]
    owner_name = clean_text(data.get("owner_name")) or user.name
    focus_growth = clean_text(data.get("focus_growth"))
    class_outlook = clean_text(data.get("class_outlook"))
    annual_events = clean_text(data.get("annual_events"))
    seasonal_context = clean_text(data.get("seasonal_context"))
    care_points = clean_text(data.get("care_points"))
    family_policy = clean_text(data.get("family_collaboration_policy"))
    health_safety = clean_text(data.get("health_safety_policy"))
    preferred_expressions = clean_text(data.get("preferred_expressions"))

    required = confirmation_items(
        [
            ("クラスの姿", class_outlook),
            ("年間で大切にしたい育ち", focus_growth),
            ("配慮事項", care_points),
        ]
    )
    sections: list[SectionBlock] = []

    for definition in annual_section_definitions():
        if definition.key == "annual_goal":
            body = (
                f"{school_year}年度の{class_name}では、{focus_growth or '子どもの主体的な育ち'}を年間の軸に据える。"
                f"{class_outlook or '現在の子どもの姿を確認しながら、生活と遊びがつながる計画として更新する。'}"
            )
            if preferred_expressions:
                body += f" 表現は「{preferred_expressions}」を意識して整える。"
            needs_confirmation, editor_note = _needs_note(focus_growth and class_outlook, "年間の中心情報")
            sections.append(
                _section(
                    definition,
                    body,
                    ["profile.childcare_goal", "form.focus_growth", "form.class_outlook"],
                    needs_confirmation=needs_confirmation,
                    editor_note=editor_note,
                )
            )
            continue

        term_key = "_".join(definition.key.split("_")[:2])
        suffix = definition.key.replace(f"{term_key}_", "")
        term_label = _term_label(term_key)
        term_note = clean_text(data.get(f"{term_key}_note"))

        if suffix == "outlook":
            body = (
                f"{term_label}は、{term_note or seasonal_context or '季節や行事を踏まえた子どもの姿'}を捉え、"
                f"{focus_growth or '年間のねらい'}につながる経験を積み重ねる。"
            )
            refs = ["form.seasonal_context", f"form.{term_key}_note", "form.focus_growth"]
        elif suffix == "environment":
            body = (
                f"{term_label}の環境は、子どもが選び、試し、友だちと関わり直せる余白を残して構成する。"
                f" 行事や生活の流れは「{annual_events or '園行事'}」と接続して調整する。"
            )
            refs = ["profile.indoor_environment", "form.annual_events"]
        elif suffix == "support":
            body = (
                f"保育者は{term_label}の姿を観察し、{care_points or '安全面と個別配慮'}を確認しながら、"
                "子どもの言葉や試行錯誤を次の活動へつなげる。"
            )
            refs = ["profile.support_policy", "form.care_points"]
        elif suffix == "family_collaboration":
            body = (
                f"家庭には{term_label}の育ちの見通しを共有し、"
                f"{family_policy or '園での姿と家庭での姿を相互に伝え合う'}。"
            )
            refs = ["profile.family_collaboration_policy", "form.family_collaboration_policy"]
        else:
            body = (
                f"{term_label}の終わりに、ねらいに対する子どもの変化、環境の働き、"
                f"{health_safety or '健康と安全の配慮'}を振り返り、次期の計画へ反映する。"
            )
            refs = ["knowledge.health_and_safety", "form.health_safety_policy"]

        needs_confirmation, editor_note = _needs_note(term_note or seasonal_context or annual_events, f"{term_label}の具体情報")
        sections.append(
            _section(
                definition,
                body,
                refs,
                needs_confirmation=needs_confirmation and suffix == "outlook",
                editor_note=editor_note if suffix == "outlook" else None,
            )
        )

    return PlanDocument(
        id=0,
        document_type=DocumentType.ANNUAL_PLAN,
        title=f"{school_year}年度 年案（{class_name}）",
        status=DocumentStatus.DRAFT,
        nursery_ref=user.nursery_ref,
        classroom_ref=classroom_ref,
        actor_ref=user.actor_ref,
        owner_name=owner_name,
        school_year=school_year,
        sections=sections,
        confirmation_items=required,
    )


def generate_monthly_plan(data: dict[str, str], user: StaffUser) -> PlanDocument:
    target_month = clean_text(data.get("target_month")) or "2026-04"
    class_name = clean_text(data.get("class_name")) or "クラス未設定"
    classroom_ref = clean_text(data.get("classroom_ref")) or user.classroom_refs[0]
    owner_name = clean_text(data.get("owner_name")) or user.name
    related_annual_summary = clean_text(data.get("related_annual_summary"))
    previous_reflection = clean_text(data.get("previous_reflection"))
    current_children_snapshot = clean_text(data.get("current_children_snapshot"))
    play_interests = clean_text(data.get("play_interests"))
    seasonal_context = clean_text(data.get("seasonal_context"))
    family_context = clean_text(data.get("family_context"))
    class_notes = clean_text(data.get("class_notes"))

    required = confirmation_items(
        [
            ("年間計画の関連文脈", related_annual_summary),
            ("前月の反省", previous_reflection),
            ("現在の子どもの姿", current_children_snapshot),
        ]
    )
    needs_core_confirmation = bool(required)

    definitions = {definition.key: definition for definition in MONTHLY_SECTIONS}

    sections = [
        _section(
            definitions["monthly_goal"],
            (
                f"{target_month}の{class_name}では、{related_annual_summary or '年間計画の方向性'}を踏まえ、"
                f"{previous_reflection or '前月の姿'}から見えた課題を受けて、"
                f"{current_children_snapshot or '現在の子どもの姿'}を次の経験につなげる。"
            ),
            ["annual.related_context", "monthly.previous_reflection", "form.current_children_snapshot"],
            needs_confirmation=needs_core_confirmation,
            editor_note="年間計画、前月反省、現在の姿を確認してください。" if needs_core_confirmation else None,
        ),
        _section(
            definitions["children_snapshot"],
            (
                f"現在は、{current_children_snapshot or '子どもの姿を記録してください'}。"
                f" 遊びの関心は{play_interests or '観察から追記'}し、個別差を踏まえて捉える。"
            ),
            ["form.current_children_snapshot", "form.play_interests"],
            needs_confirmation=not bool(current_children_snapshot),
            editor_note="現在の姿が未入力です。" if not current_children_snapshot else None,
        ),
        _section(
            definitions["monthly_environment"],
            (
                f"{seasonal_context or '季節や行事'}を取り入れながら、子どもが選択できる素材と場を用意する。"
                f" {play_interests or '興味のある遊び'}が広がるよう、少人数で試せる環境を整える。"
            ),
            ["form.seasonal_context", "form.play_interests", "profile.indoor_environment"],
        ),
        _section(
            definitions["monthly_support"],
            (
                "保育者は子どもの言葉、動き、関係性の変化を観察し、必要な場面で選択肢を示す。"
                f" クラス内の留意点は「{class_notes or '日々の記録から追記'}」として共有する。"
            ),
            ["profile.support_policy", "form.class_notes"],
        ),
        _section(
            definitions["monthly_family_collaboration"],
            (
                f"家庭には今月のねらいと遊びの広がりを伝え、{family_context or '家庭での様子'}を聞き取る。"
                " 園と家庭で共通して見守れる姿を短く共有する。"
            ),
            ["profile.family_collaboration_policy", "form.family_context"],
        ),
        _section(
            definitions["monthly_reflection_viewpoint"],
            (
                "月末には、ねらいに対する子どもの変化、環境の働き、保育者の関わり、家庭連携の手応えを確認する。"
                " 次月へ残す課題は、具体的な場面とともに記録する。"
            ),
            ["monthly.reflection_viewpoint", "linking.next_month"],
        ),
    ]

    return PlanDocument(
        id=0,
        document_type=DocumentType.MONTHLY_PLAN,
        title=f"{target_month} 月案（{class_name}）",
        status=DocumentStatus.DRAFT,
        nursery_ref=user.nursery_ref,
        classroom_ref=classroom_ref,
        actor_ref=user.actor_ref,
        owner_name=owner_name,
        target_month=target_month,
        sections=sections,
        confirmation_items=required,
    )
