# hoiku-plan-docs

`hoiku-plan-docs` は、`open-hoikuict` ベータ向けの文書作成機能を切り出して初期実装するための FastAPI アプリです。
最終的に `hoiku-plan-writer` の実用版と差し替えやすいように、認証・権限・安定ID・文書契約を先に固定します。

## 今回の初期実装

- `FastAPI + Jinja2` の最小 Web 構成
- open-hoikuict / hoiku-plan-writer と合わせた職員セッション
- 年案、月案の帳票作成 UI
- 共通文例・園文例データベースから候補を選んで年案・月案を作成する UI
- 作成済み帳票の一覧、詳細、印刷向けプレビュー
- 文書種別 / 状態 / セクションキー / 根拠情報の連携契約
- 本体 DB に依存しない in-memory 保存層

## 契約の中心

### Role / Permission

`open-hoikuict` と現行 `hoiku-plan-writer` の職員権限に合わせます。

| role | 用途 |
| --- | --- |
| `view_only` | 閲覧のみ |
| `can_edit` | 文書作成、編集、レビュー依頼 |
| `admin` | `can_edit` に加えて承認、差戻し、アーカイブ |

職員セッションは、操作職員・園・担当クラスの安定した識別情報を持ちます。本体統合時は現在の cookie 実装を open-hoikuict 側の認証解決に差し替えます。

### 文書種別

外部契約では次を使います。

- `annual_plan`
- `monthly_plan`

`hoiku-plan-writer` 現行コードの短い種別名は互換値として扱います。

### Status

外部契約では次を使います。

- `draft`
- `in_review`
- `approved`
- `rejected`
- `archived`

`hoiku-plan-writer` 現行コードの `returned` は `rejected` の互換 alias として扱います。

### Section Key

`section_key` は表示文言ではなく永続契約です。UI ラベルを変えてもキーは変えません。

年案は `annual_goal` と `term_1_*` から `term_4_*`、月案は `monthly_goal`、`children_snapshot`、`monthly_environment`、`monthly_support`、`monthly_health_safety`、`monthly_food_education`、`monthly_events`、`monthly_10_perspectives`、`monthly_family_collaboration`、`monthly_reflection_viewpoint` を使います。

詳細は [docs/integration-contract.md](docs/integration-contract.md) を参照してください。

## 起動

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
uvicorn hoiku_plan_docs.main:app --reload --port 8020
```

ブラウザで `http://127.0.0.1:8020/` を開くと、帳票一覧と年案・月案の作成導線が表示されます。

## 主な画面

- `/` : 文書作成ダッシュボード
- `/annual-plans/new` : 年案作成
- `/monthly-plans/new` : 月案作成
- `/bunrei/annual` : 文例を選んで年案作成
- `/bunrei/monthly` : 文例を選んで月案作成
- `/bunrei/facility/new` : 自作文例の追加、CSV・Excel（.xlsx）取り込み
- `/documents/` : 帳票一覧
- `/documents/{document_id}` : 帳票詳細、印刷向けプレビュー、ステータス操作
- `/documents/{document_id}/edit` : 下書き・差戻し帳票の修正
- `/staff/login` : 職員表示の切り替え

## 文例データベース

`gen_bunnrei/bunrei.sqlite` は v2 の共通文例DBです。年案の `年間目標` と `期の振り返り観点`、月案の `健康・安全への配慮`、`食育`、`行事`、`10の姿のねらい` を含みます。

`gen_bunnrei/facility.sqlite` は園内限定の文例DBです。候補表示では現在の `nursery_ref` で必ず絞り込み、他園の園文例は返しません。園文例も `needs_review=1` として扱い、選択後の修正画面で確認します。

画面からの取り込みは `/bunrei/facility/new` で行います。CSV・Excel（.xlsx）は `計画種別`、`年齢`、`月`、`項目`、`領域・観点`、`出所メモ`、`本文` の列名に対応します。取り込み画面からヘッダー入りの空CSV・空Excelをダウンロードできます。`本文` だけのファイルは画面で指定した既定値を使って取り込みます。

生成・取り込み:

```powershell
cd gen_bunnrei
python generate_v2.py
python facility_import.py sample_facility.csv --nursery "ひかり保育園"
```

## API

- `GET /health`
- `GET /api/documents/{document_id}`

現時点では UI 初期実装を優先し、永続化と JSON 作成 API は後続で拡張します。

## 統合方針

1. open-hoikuict 側から iframe ではなく通常リンクまたは reverse proxy 配下で呼び出す。
2. 職員セッションを `StaffAuthBackend` 実装差し替えで本体セッション解決へ寄せる。
3. 操作職員、園、クラスは本体内部 PK ではなく安定した識別情報として受け渡す。
4. `document_type`、`status`、`section_key` は integration contract を唯一の外部契約とする。
5. 実用版との差し替え時は生成サービスと保存層を差し替え、UI と契約を維持する。
