# 連携契約

この文書は `hoiku-plan-docs`、`open-hoikuict`、`hoiku-plan-writer` の間で共有する文書作成機能の初期契約です。
キー名、状態名、参照形式は後方互換を維持します。

## 対象範囲

対象は年案・月案の作成、レビュー、承認、参照です。
園児、家庭、出欠、本体職員 DB には直接依存しません。本体側の値は外部参照として受け取ります。

## 職員認証

文書作成機能は職員セッションから次の値を受け取ります。

| field | type | required | example | note |
| --- | --- | --- | --- | --- |
| `role` | string | yes | `can_edit` | `view_only` / `can_edit` / `admin` |
| `actor_ref` | string | yes | `staff:demo-editor` | 操作主体の安定参照 |
| `nursery_ref` | string | yes | `nursery:demo` | 園の安定参照 |
| `classroom_refs` | string[] | yes | `["classroom:5yo-a"]` | 担当クラスの安定参照 |
| `name` | string | no | `サンプル職員` | 表示用 |

### 権限

| role | can view | can create | can submit | can approve/reject | can archive |
| --- | --- | --- | --- | --- | --- |
| `view_only` | yes | no | no | no | no |
| `can_edit` | yes | yes | yes | no | no |
| `admin` | yes | yes | yes | yes | yes |

`classroom_ref` は文書単位で保存します。`admin` は園内全クラスにアクセス可能です。`view_only` / `can_edit` は `classroom_refs` に含まれる文書だけを扱えます。

## 文書

### 文書種別

外部契約で許可する値は次の通りです。

| document_type | label | note |
| --- | --- | --- |
| `annual_plan` | 年案 | 年間指導計画 |
| `monthly_plan` | 月案 | 月間指導計画 |

互換 alias:

| legacy | normalized |
| --- | --- |
| `annual` | `annual_plan` |
| `monthly` | `monthly_plan` |

### 状態

| status | label | editable | meaning |
| --- | --- | --- | --- |
| `draft` | 下書き | yes | 作成、編集、再生成できる |
| `in_review` | レビュー待ち | limited | 承認者確認中 |
| `approved` | 承認済み | no | 正式版 |
| `rejected` | 差戻し | yes | 修正が必要 |
| `archived` | アーカイブ | no | 旧版参照専用 |

互換 alias:

| legacy | normalized |
| --- | --- |
| `returned` | `rejected` |

### 最小データ形

```json
{
  "id": 1,
  "document_type": "annual_plan",
  "status": "draft",
  "title": "2026年度 年案（5歳児 ひまわり組）",
  "nursery_ref": "サンプル園",
  "classroom_ref": "5歳児 ひまわり組",
  "actor_ref": "職員:サンプル",
  "school_year": 2026,
  "target_month": null,
  "sections": [
    {
      "section_key": "annual_goal",
      "title": "年間の大きなねらい",
      "body": "...",
      "source_refs": ["profile.childcare_goal", "form.focus_growth"],
      "evidence_tags": ["園方針", "入力"],
      "needs_confirmation": false,
      "editor_note": null
    }
  ],
  "confirmation_items": []
}
```

## セクションキー

`section_key` は永続識別子です。表示ラベルや帳票レイアウトが変わっても変更しません。

### 年案

| section_key | title |
| --- | --- |
| `annual_goal` | 年間の大きなねらい |
| `term_1_outlook` | 4〜6月の見通し |
| `term_1_environment` | 4〜6月の環境構成 |
| `term_1_support` | 4〜6月の援助 |
| `term_1_family_collaboration` | 4〜6月の家庭連携 |
| `term_1_reflection_viewpoint` | 4〜6月の振り返り観点 |
| `term_2_outlook` | 7〜9月の見通し |
| `term_2_environment` | 7〜9月の環境構成 |
| `term_2_support` | 7〜9月の援助 |
| `term_2_family_collaboration` | 7〜9月の家庭連携 |
| `term_2_reflection_viewpoint` | 7〜9月の振り返り観点 |
| `term_3_outlook` | 10〜12月の見通し |
| `term_3_environment` | 10〜12月の環境構成 |
| `term_3_support` | 10〜12月の援助 |
| `term_3_family_collaboration` | 10〜12月の家庭連携 |
| `term_3_reflection_viewpoint` | 10〜12月の振り返り観点 |
| `term_4_outlook` | 1〜3月の見通し |
| `term_4_environment` | 1〜3月の環境構成 |
| `term_4_support` | 1〜3月の援助 |
| `term_4_family_collaboration` | 1〜3月の家庭連携 |
| `term_4_reflection_viewpoint` | 1〜3月の振り返り観点 |

### 月案

| section_key | title |
| --- | --- |
| `monthly_goal` | 今月のねらい |
| `children_snapshot` | 子どもの姿の捉え |
| `monthly_environment` | 環境構成 |
| `monthly_support` | 援助 |
| `monthly_family_collaboration` | 家庭連携 |
| `monthly_reflection_viewpoint` | 月末の振り返り観点 |

## 根拠情報と表示タグ

`source_refs` は文字列配列です。prefix から表示タグを再計算します。

| prefix | evidence tag |
| --- | --- |
| `profile.*` | `園方針` |
| `knowledge.*` | `公的根拠` |
| `form.*` | `入力` |
| `annual.*` | `入力` |
| `monthly.*` | `入力` |
| `outline.*` | `AI構成` |
| `linking.*` | `AI構成` |

各 section は最低 1 つ以上の `source_refs` と `evidence_tags` を持ちます。

## 承認ログ

将来の永続化では最低限次を保存します。

| field | type |
| --- | --- |
| `document_id` | int or uuid |
| `document_type` | string |
| `action` | string |
| `comment` | string |
| `actor_ref` | string |
| `created_at` | datetime |

`action` は `submit`、`approve`、`reject`、`archive` のみ許可します。

## API 境界

初期実装では画面操作を優先し、JSON API は参照のみです。

| method | path | auth | purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | none | 稼働確認 |
| `GET` | `/api/documents/{document_id}` | staff | 文書 JSON 参照 |

後続で `POST /api/annual-plans`、`POST /api/monthly-plans`、`PATCH /api/documents/{id}/status` を追加する場合も、この contract の値だけを受け付けます。

## 破壊的変更の扱い

以下は破壊的変更です。

- 既存 `document_type` の削除または意味変更
- 既存 `status` の削除または意味変更
- 既存 `section_key` の削除または意味変更
- `source_refs` prefix ルールの変更
- `actor_ref`、`nursery_ref`、`classroom_ref` の意味変更

破壊的変更が必要な場合は、ADR、migration 方針、互換レイヤを同時に用意します。
