from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from hoiku_plan_docs.main import create_app
from hoiku_plan_docs.services.bunrei import annual_candidate_groups, monthly_candidate_groups
from hoiku_plan_docs.store import document_store


class AppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        document_store.clear()
        self.client = TestClient(create_app())

    def test_home_loads(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("年案・月案の帳票作成", response.text)

    def test_create_annual_plan(self) -> None:
        response = self.client.post(
            "/annual-plans",
            data={
                "school_year": "2026",
                "class_name": "5歳児 ひまわり組",
                "classroom_ref": "5歳児 ひまわり組",
                "owner_name": "担任",
                "class_outlook": "友だちと相談しながら遊びを広げている。",
                "focus_growth": "主体的に選び、協同して試す姿",
                "care_points": "安全な動線と休息の保障",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/documents/1")

        detail = self.client.get("/api/documents/1")
        self.assertEqual(detail.status_code, 200)
        payload = detail.json()
        self.assertEqual(payload["document_type"], "annual_plan")
        self.assertEqual(payload["status"], "draft")
        self.assertEqual(payload["sections"][0]["section_key"], "annual_goal")

    def test_view_only_cannot_create(self) -> None:
        response = self.client.post(
            "/annual-plans?as=view_only",
            data={"school_year": "2026", "classroom_ref": "5歳児 ひまわり組"},
        )
        self.assertEqual(response.status_code, 403)

    def test_edit_created_document(self) -> None:
        self.client.post(
            "/annual-plans",
            data={
                "school_year": "2026",
                "class_name": "5歳児 ひまわり組",
                "classroom_ref": "5歳児 ひまわり組",
                "class_outlook": "年度初めの姿",
                "focus_growth": "友だちと考える姿",
            },
        )
        edit_form = self.client.get("/documents/1/edit")
        self.assertEqual(edit_form.status_code, 200)
        self.assertIn("帳票を修正", edit_form.text)

        response = self.client.post(
            "/documents/1",
            data={
                "title": "修正後タイトル",
                "owner_name": "修正者",
                "confirmation_items": "追記確認",
                "body_annual_goal": "修正した年間のねらい",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        payload = self.client.get("/api/documents/1").json()
        self.assertEqual(payload["title"], "修正後タイトル")
        self.assertEqual(payload["owner_name"], "修正者")
        self.assertEqual(payload["confirmation_items"], ["追記確認"])
        self.assertEqual(payload["sections"][0]["body"], "修正した年間のねらい")

    def test_admin_can_approve(self) -> None:
        self.client.post(
            "/monthly-plans",
            data={
                "target_month": "2026-04",
                "class_name": "5歳児 ひまわり組",
                "classroom_ref": "5歳児 ひまわり組",
                "related_annual_summary": "4〜6月は安心して関係を広げる。",
                "previous_reflection": "戸外遊びで相談する姿が増えた。",
                "current_children_snapshot": "友だちの考えを聞きながら遊びを組み立てている。",
            },
        )
        response = self.client.post(
            "/documents/1/status?as=admin",
            data={"status": "approved"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.client.get("/api/documents/1?as=admin").json()["status"], "approved")

    def test_approved_document_cannot_be_edited(self) -> None:
        self.client.post(
            "/monthly-plans",
            data={
                "target_month": "2026-04",
                "class_name": "5歳児 ひまわり組",
                "classroom_ref": "5歳児 ひまわり組",
                "related_annual_summary": "4〜6月は安心して関係を広げる。",
                "previous_reflection": "戸外遊びで相談する姿が増えた。",
                "current_children_snapshot": "友だちの考えを聞きながら遊びを組み立てている。",
            },
        )
        self.client.post("/documents/1/status?as=admin", data={"status": "approved"})
        response = self.client.get("/documents/1/edit?as=admin")
        self.assertEqual(response.status_code, 409)

    def test_monthly_plan_can_be_created_from_bunrei_selection(self) -> None:
        selector = self.client.get("/bunrei/monthly")
        self.assertEqual(selector.status_code, 200)
        self.assertIn("月案を文例から作成", selector.text)
        first_example = monthly_candidate_groups("5歳児", 4)[0].examples[0]

        response = self.client.post(
            "/bunrei/monthly",
            data={
                "age_class": "5歳児",
                "month": "4",
                "target_month": "2026-04",
                "class_name": "5歳児 ひまわり組",
                "classroom_ref": "5歳児 ひまわり組",
                "section_monthly_goal": first_example.id,
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/documents/1/edit")
        payload = self.client.get("/api/documents/1").json()
        self.assertEqual(payload["document_type"], "monthly_plan")
        self.assertEqual(payload["status"], "draft")
        self.assertEqual(payload["sections"][0]["section_key"], "monthly_goal")
        self.assertEqual(payload["sections"][0]["body"], first_example.text)

    def test_annual_plan_can_be_created_from_bunrei_selection(self) -> None:
        selector = self.client.get("/bunrei/annual")
        self.assertEqual(selector.status_code, 200)
        self.assertIn("年案を文例から作成", selector.text)
        first_example = annual_candidate_groups("5歳児")[0].examples[0]

        response = self.client.post(
            "/bunrei/annual",
            data={
                "age_class": "5歳児",
                "school_year": "2026",
                "class_name": "5歳児 ひまわり組",
                "classroom_ref": "5歳児 ひまわり組",
                "section_annual_goal": first_example.id,
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/documents/1/edit")
        payload = self.client.get("/api/documents/1").json()
        self.assertEqual(payload["document_type"], "annual_plan")
        self.assertEqual(payload["sections"][0]["section_key"], "annual_goal")
        self.assertEqual(payload["sections"][0]["body"], first_example.text)


if __name__ == "__main__":
    unittest.main()
