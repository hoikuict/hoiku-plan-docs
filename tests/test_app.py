from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from hoiku_plan_docs.main import create_app
from hoiku_plan_docs.services.bunrei import annual_candidate_groups, monthly_candidate_groups
from hoiku_plan_docs.store import document_store


def _xlsx_bytes(rows: list[list[str]]) -> bytes:
    def cell_name(row_index: int, col_index: int) -> str:
        name = ""
        col = col_index + 1
        while col:
            col, remainder = divmod(col - 1, 26)
            name = chr(ord("A") + remainder) + name
        return f"{name}{row_index}"

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = "".join(
            f'<c r="{cell_name(row_index, col_index)}" t="inlineStr"><is><t>{value}</t></is></c>'
            for col_index, value in enumerate(row)
        )
        sheet_rows.append(f'<row r="{row_index}">{cells}</row>')
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData>"
        "</worksheet>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="園文例" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


class AppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        document_store.clear()
        self._old_facility_db_path = os.environ.get("HOIKU_FACILITY_BUNREI_DB_PATH")
        self._temp_dir = tempfile.TemporaryDirectory()
        root = Path(__file__).resolve().parents[1]
        source_db = next(
            path
            for path in (
                root / "gen_bunrei" / "facility.sqlite",
                root / "gen_bunnrei" / "facility.sqlite",
            )
            if path.exists()
        )
        self.facility_db_path = Path(self._temp_dir.name) / "facility.sqlite"
        shutil.copyfile(source_db, self.facility_db_path)
        os.environ["HOIKU_FACILITY_BUNREI_DB_PATH"] = str(self.facility_db_path)
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        if self._old_facility_db_path is None:
            os.environ.pop("HOIKU_FACILITY_BUNREI_DB_PATH", None)
        else:
            os.environ["HOIKU_FACILITY_BUNREI_DB_PATH"] = self._old_facility_db_path
        self._temp_dir.cleanup()

    def test_home_loads(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("年案・月案の帳票作成", response.text)
        self.assertIn("自作文例を追加", response.text)
        self.assertIn('<a href="/">指導計画作成</a>', response.text)
        self.assertNotIn('<a href="/annual-plans/new">年案作成</a>', response.text)
        self.assertNotIn('<a href="/monthly-plans/new">月案作成</a>', response.text)
        self.assertNotIn('<a href="/bunrei/monthly">文例選択</a>', response.text)
        self.assertNotIn('<a class="button button--primary" href="/annual-plans/new">年案を作成</a>', response.text)
        self.assertNotIn('<a class="button button--secondary" href="/monthly-plans/new">月案を作成</a>', response.text)

    def test_document_list_links_back_to_plan_creation(self) -> None:
        response = self.client.get("/documents/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('<a class="button button--primary" href="/">指導案作成</a>', response.text)
        self.assertNotIn('<a class="button button--primary" href="/annual-plans/new">年案を作成</a>', response.text)
        self.assertNotIn('<a class="button button--secondary" href="/monthly-plans/new">月案を作成</a>', response.text)

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

    def test_staff_role_can_be_switched_to_admin(self) -> None:
        login = self.client.get("/staff/login")
        self.assertEqual(login.status_code, 200)
        self.assertIn("この内容に切り替える", login.text)

        response = self.client.post(
            "/staff/session",
            data={"role": "admin", "name": "主任"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn("主任", home.text)
        self.assertIn("管理者", home.text)

    def test_plan_forms_show_single_class_field(self) -> None:
        for path in (
            "/annual-plans/new",
            "/monthly-plans/new",
            "/weekly-plans/new",
            "/daily-plans/new",
            "/bunrei/annual",
            "/bunrei/monthly",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("クラス名", response.text)
                self.assertEqual(response.text.count("<span>クラス</span>"), 1)

    def test_weekly_plan_can_be_created_with_schedule(self) -> None:
        self.client.post(
            "/monthly-plans",
            data={
                "target_month": "2026-04",
                "classroom_ref": "5歳児 ひまわり組",
                "related_annual_summary": "春は安心して関係を広げる。",
                "previous_reflection": "友だちと相談する姿が増えた。",
                "current_children_snapshot": "素材を選びながら遊びを広げている。",
            },
        )
        response = self.client.post(
            "/weekly-plans",
            data={
                "target_week": "2026-W16",
                "classroom_ref": "5歳児 ひまわり組",
                "age_class": "5歳児",
                "owner_name": "担任",
                "parent_document_id": "1",
                "related_monthly_summary": "春の自然に触れながら友だちと遊びを広げる。",
                "previous_week_reflection": "虫探しから図鑑や制作へ関心が広がった。",
                "current_children_snapshot": "友だちの発見を聞き、試したい素材を選んでいる。",
                "weekly_activities_note": "園庭で見つけたものを描く、作る、調べる。",
                "include_saturday": "on",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        payload = self.client.get("/api/documents/2").json()
        self.assertEqual(payload["document_type"], "weekly_plan")
        self.assertEqual(payload["target_week"], "2026-W16")
        self.assertEqual(payload["week_start_date"], "2026-04-13")
        self.assertEqual(payload["age_class"], "5歳児")
        self.assertEqual(payload["parent_document_id"], 1)
        self.assertEqual(payload["schedule"]["layout"], "weekly_grid")
        self.assertEqual([row["row_key"] for row in payload["schedule"]["rows"]], ["mon", "tue", "wed", "thu", "fri", "sat"])
        self.assertIn("monthly.related_context", payload["sections"][0]["source_refs"])

    def test_daily_plan_can_be_created_and_schedule_cell_edited(self) -> None:
        self.client.post(
            "/weekly-plans",
            data={
                "target_week": "2026-W16",
                "classroom_ref": "5歳児 ひまわり組",
                "age_class": "5歳児",
                "related_monthly_summary": "月案のねらいを受ける。",
                "previous_week_reflection": "素材を選ぶ姿が見られた。",
                "current_children_snapshot": "友だちと考えを伝え合っている。",
                "weekly_activities_note": "園庭で見つけたものを表現する。",
            },
        )
        response = self.client.post(
            "/daily-plans",
            data={
                "target_date": "2026-04-14",
                "classroom_ref": "5歳児 ひまわり組",
                "age_class": "5歳児",
                "owner_name": "担任",
                "parent_document_id": "1",
                "related_weekly_summary": "園庭で見つけたものを表現する。",
                "current_children_snapshot": "友だちの発見に刺激を受けている。",
                "daily_main_activity_note": "",
                "health_notes": "気温が上がるため水分補給を意識する。",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        payload = self.client.get("/api/documents/2").json()
        self.assertEqual(payload["document_type"], "daily_plan")
        self.assertEqual(payload["schedule"]["layout"], "daily_timeline")
        main_row = next(row for row in payload["schedule"]["rows"] if row["row_key"] == "t_main")
        self.assertTrue(main_row["cells"]["children"]["needs_confirmation"])
        self.assertTrue(main_row["cells"]["support"]["needs_confirmation"])
        self.assertIn("主活動の子どもの姿と援助", payload["confirmation_items"])
        self.assertIn("weekly.related_context", payload["sections"][0]["source_refs"])

        response = self.client.post(
            "/documents/2",
            data={
                "title": payload["title"],
                "owner_name": payload["owner_name"],
                "confirmation_items": "\n".join(payload["confirmation_items"]),
                "cell__t_main__children": "葉や石を見比べ、形や色の違いを言葉にする。",
                "cell__t_main__support": "気づきを受け止め、描く・並べる・調べる素材を選べるようにする。",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        edited = self.client.get("/api/documents/2").json()
        edited_main = next(row for row in edited["schedule"]["rows"] if row["row_key"] == "t_main")
        self.assertEqual(edited_main["cells"]["children"]["body"], "葉や石を見比べ、形や色の違いを言葉にする。")
        self.assertFalse(edited_main["cells"]["children"]["needs_confirmation"])
        self.assertFalse(edited_main["cells"]["support"]["needs_confirmation"])

    def test_view_only_cannot_create_weekly_or_daily_plan(self) -> None:
        weekly = self.client.post(
            "/weekly-plans?as=view_only",
            data={"target_week": "2026-W16", "classroom_ref": "5歳児 ひまわり組", "age_class": "5歳児"},
        )
        daily = self.client.post(
            "/daily-plans?as=view_only",
            data={"target_date": "2026-04-14", "classroom_ref": "5歳児 ひまわり組", "age_class": "5歳児"},
        )
        self.assertEqual(weekly.status_code, 403)
        self.assertEqual(daily.status_code, 403)

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
        self.assertIn("健康・安全への配慮", selector.text)
        self.assertIn("食育", selector.text)
        self.assertIn("10の姿", selector.text)
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

    def test_facility_bunrei_is_scoped_to_current_nursery(self) -> None:
        own_nursery = self.client.get("/bunrei/monthly?age_class=5歳児&month=10")
        self.assertEqual(own_nursery.status_code, 200)
        self.assertIn("園文例", own_nursery.text)

        other_nursery = self.client.get("/bunrei/monthly?age_class=5歳児&month=10&nursery_ref=別の園")
        self.assertEqual(other_nursery.status_code, 200)
        self.assertNotIn("園文例", other_nursery.text)

    def test_facility_bunrei_can_be_added_from_ui(self) -> None:
        form = self.client.get("/bunrei/facility/new")
        self.assertEqual(form.status_code, 200)
        self.assertIn("自作文例を追加", form.text)
        self.assertIn("園文例として追加", form.text)
        self.assertIn("CSV・Excelからまとめて取り込み", form.text)
        self.assertIn("空のCSVをダウンロード", form.text)
        self.assertIn("空のExcelをダウンロード", form.text)

        response = self.client.post(
            "/bunrei/facility",
            data={
                "plan_type": "月案",
                "age_class": "5歳児",
                "month": "4",
                "item": "食育",
                "ryoiki": "",
                "source_note": "テスト入力",
                "text": "春の野菜に触れ、香りや手触りを友だちと伝え合う。",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["location"].startswith("/bunrei/monthly"))

        selector = self.client.get("/bunrei/monthly?age_class=5歳児&month=4")
        self.assertEqual(selector.status_code, 200)
        self.assertIn("園文例", selector.text)
        self.assertIn("春の野菜に触れ", selector.text)

    def test_facility_bunrei_can_be_imported_from_csv(self) -> None:
        csv_content = "計画種別,年齢,月,項目,本文\n月案,5歳児,4,食育,旬の果物を見て香りや色に気づく。\n"
        response = self.client.post(
            "/bunrei/facility/import",
            data={"default_source_note": "CSV取り込み"},
            files={"file": ("bunrei.csv", csv_content.encode("utf-8-sig"), "text/csv")},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("imported=1", response.headers["location"])

        selector = self.client.get("/bunrei/monthly?age_class=5歳児&month=4")
        self.assertEqual(selector.status_code, 200)
        self.assertIn("旬の果物を見て", selector.text)

    def test_facility_bunrei_can_be_imported_from_xlsx(self) -> None:
        workbook = _xlsx_bytes(
            [
                ["計画種別", "年齢", "月", "項目", "本文"],
                ["月案", "5歳児", "4", "行事", "園庭で春の会を楽しみ、進級した喜びを味わう。"],
            ]
        )
        response = self.client.post(
            "/bunrei/facility/import",
            files={
                "file": (
                    "bunrei.xlsx",
                    workbook,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("imported=1", response.headers["location"])

        selector = self.client.get("/bunrei/monthly?age_class=5歳児&month=4")
        self.assertEqual(selector.status_code, 200)
        self.assertIn("園庭で春の会", selector.text)

    def test_facility_import_templates_can_be_downloaded(self) -> None:
        csv_template = self.client.get("/bunrei/facility/import-template.csv")
        self.assertEqual(csv_template.status_code, 200)
        self.assertIn("attachment", csv_template.headers["content-disposition"])
        self.assertIn("計画種別,年齢,月,項目,領域・観点,出所メモ,本文", csv_template.content.decode("utf-8-sig"))

        xlsx_template = self.client.get("/bunrei/facility/import-template.xlsx")
        self.assertEqual(xlsx_template.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(xlsx_template.content)) as archive:
            self.assertIn("xl/worksheets/sheet1.xml", archive.namelist())

        response = self.client.post(
            "/bunrei/facility/import",
            files={
                "file": (
                    "template.xlsx",
                    xlsx_template.content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("imported=0", response.headers["location"])

    def test_annual_plan_can_be_created_from_bunrei_selection(self) -> None:
        selector = self.client.get("/bunrei/annual")
        self.assertEqual(selector.status_code, 200)
        self.assertIn("年案を文例から作成", selector.text)
        first_example = annual_candidate_groups("5歳児")[0].examples[0]
        self.assertEqual(first_example.item, "年間目標")

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
