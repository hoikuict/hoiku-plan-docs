from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Protocol
from urllib.parse import quote, unquote

from fastapi import Depends, HTTPException, Request, Response

from .contracts import ROLE_LABELS, Role


SAMPLE_ROLE_COOKIE = "sample_role"
SAMPLE_ACTOR_REF_COOKIE = "sample_actor_ref"
SAMPLE_NURSERY_REF_COOKIE = "sample_nursery_ref"
SAMPLE_CLASSROOMS_COOKIE = "sample_classroom_refs"
SAMPLE_STAFF_NAME_COOKIE = "sample_staff_name"
COOKIE_MAX_AGE = 60 * 60 * 24
DEFAULT_ACTOR_REF = "職員:サンプル"
DEFAULT_NURSERY_REF = "サンプル園"
DEFAULT_CLASSROOM_REFS = ("5歳児 ひまわり組",)
DEFAULT_STAFF_NAME = "サンプル職員"


def _parse_role(raw: str | None) -> Role:
    if raw in {item.value for item in Role}:
        return Role(raw)
    return Role.CAN_EDIT


def _parse_classroom_refs(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return DEFAULT_CLASSROOM_REFS
    refs = tuple(item.strip() for item in raw.split(",") if item.strip())
    return refs or DEFAULT_CLASSROOM_REFS


@dataclass(slots=True)
class StaffUser:
    role: Role
    actor_ref: str = DEFAULT_ACTOR_REF
    nursery_ref: str = DEFAULT_NURSERY_REF
    classroom_refs: tuple[str, ...] = DEFAULT_CLASSROOM_REFS
    name: str = DEFAULT_STAFF_NAME

    @property
    def can_view(self) -> bool:
        return True

    @property
    def can_edit(self) -> bool:
        return self.role in (Role.CAN_EDIT, Role.ADMIN)

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(self.role, self.role.value)

    @property
    def classroom_refs_text(self) -> str:
        return ",".join(self.classroom_refs)

    @property
    def nursery_label(self) -> str:
        return self.nursery_ref

    @property
    def classroom_label(self) -> str:
        return self.classroom_refs_text

    def can_access_classroom(self, classroom_ref: str) -> bool:
        if self.is_admin:
            return True
        if not self.classroom_refs:
            return True
        return classroom_ref in self.classroom_refs


class StaffAuthBackend(Protocol):
    def get_current_user(self, request: Request) -> StaffUser: ...

    def set_session(
        self,
        response: Response,
        *,
        role: Role,
        actor_ref: str,
        nursery_ref: str,
        classroom_refs: tuple[str, ...],
        name: str,
    ) -> None: ...

    def clear_session(self, response: Response) -> None: ...


class SampleStaffAuthBackend:
    def get_current_user(self, request: Request) -> StaffUser:
        role = _parse_role(request.query_params.get("as") or request.cookies.get(SAMPLE_ROLE_COOKIE))
        actor_ref = (
            request.query_params.get("actor_ref")
            or request.cookies.get(SAMPLE_ACTOR_REF_COOKIE)
            or DEFAULT_ACTOR_REF
        )
        nursery_ref = (
            request.query_params.get("nursery_ref")
            or request.cookies.get(SAMPLE_NURSERY_REF_COOKIE)
            or DEFAULT_NURSERY_REF
        )
        classroom_refs = _parse_classroom_refs(
            request.query_params.get("classrooms") or request.cookies.get(SAMPLE_CLASSROOMS_COOKIE)
        )
        raw_name = request.query_params.get("name") or request.cookies.get(SAMPLE_STAFF_NAME_COOKIE) or quote(
            DEFAULT_STAFF_NAME, safe=""
        )
        return StaffUser(
            role=role,
            actor_ref=actor_ref,
            nursery_ref=nursery_ref,
            classroom_refs=classroom_refs,
            name=unquote(raw_name),
        )

    def set_session(
        self,
        response: Response,
        *,
        role: Role,
        actor_ref: str,
        nursery_ref: str,
        classroom_refs: tuple[str, ...],
        name: str,
    ) -> None:
        response.set_cookie(SAMPLE_ROLE_COOKIE, role.value, max_age=COOKIE_MAX_AGE)
        response.set_cookie(SAMPLE_ACTOR_REF_COOKIE, actor_ref, max_age=COOKIE_MAX_AGE)
        response.set_cookie(SAMPLE_NURSERY_REF_COOKIE, nursery_ref, max_age=COOKIE_MAX_AGE)
        response.set_cookie(SAMPLE_CLASSROOMS_COOKIE, ",".join(classroom_refs), max_age=COOKIE_MAX_AGE)
        response.set_cookie(SAMPLE_STAFF_NAME_COOKIE, quote(name, safe=""), max_age=COOKIE_MAX_AGE)

    def clear_session(self, response: Response) -> None:
        response.delete_cookie(SAMPLE_ROLE_COOKIE)
        response.delete_cookie(SAMPLE_ACTOR_REF_COOKIE)
        response.delete_cookie(SAMPLE_NURSERY_REF_COOKIE)
        response.delete_cookie(SAMPLE_CLASSROOMS_COOKIE)
        response.delete_cookie(SAMPLE_STAFF_NAME_COOKIE)


_staff_auth_backend: StaffAuthBackend = SampleStaffAuthBackend()


def configure_staff_auth_backend(backend: StaffAuthBackend) -> None:
    global _staff_auth_backend
    _staff_auth_backend = backend


def reset_staff_auth_backend() -> None:
    configure_staff_auth_backend(SampleStaffAuthBackend())


def get_current_staff_user(request: Request) -> StaffUser:
    return _staff_auth_backend.get_current_user(request)


def set_staff_session(
    response: Response,
    *,
    role: Role,
    actor_ref: str,
    nursery_ref: str,
    classroom_refs: tuple[str, ...],
    name: str,
) -> None:
    _staff_auth_backend.set_session(
        response,
        role=role,
        actor_ref=actor_ref,
        nursery_ref=nursery_ref,
        classroom_refs=classroom_refs,
        name=name,
    )


def clear_staff_session(response: Response) -> None:
    _staff_auth_backend.clear_session(response)


CurrentUser = Annotated[StaffUser, Depends(get_current_staff_user)]


def require_can_edit(user: StaffUser) -> None:
    if not user.can_edit:
        raise HTTPException(status_code=403, detail="編集権限がありません")


def require_admin(user: StaffUser) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="管理者権限が必要です")


def require_classroom_access(user: StaffUser, classroom_ref: str) -> None:
    if not user.can_access_classroom(classroom_ref):
        raise HTTPException(status_code=403, detail="このクラスの文書にアクセスできません")
