# Dockge + Cloudflare Tunnel デモ公開

`hoiku-plan-docs` の公開デモを Dockge の Compose stack と Cloudflare Tunnel で動かす手順です。

TrueNAS 上の Dockge に移植する場合は、dataset の bind mount 前提にした [deploy-truenas-dockge-cloudflare.md](deploy-truenas-dockge-cloudflare.md) を使ってください。

## 構成

- `app`: FastAPI アプリ。コンテナ内では `0.0.0.0:8020` で待ち受けます。
- `cloudflared`: Cloudflare Tunnel connector。外向き通信だけで Cloudflare に接続します。
- `hoiku_plan_docs_data`: 園文例DBを保存する Docker volume です。

帳票データは現在 in-memory 実装のため、アプリ再起動で消えます。園文例DBは `/data/facility.sqlite` に保存します。

## 1. Cloudflare 側の準備

Cloudflare Zero Trust で tunnel を作成します。

1. `Zero Trust` > `Networks` > `Tunnels` を開く。
2. `Create a tunnel` で `Cloudflared` を選ぶ。
3. Connector の実行方法は `Docker` を選び、表示された tunnel token を控える。
4. `Public Hostname` を追加する。
   - Subdomain: 例 `hoiku-docs-demo`
   - Domain: 例 `example.com`
   - Type: `HTTP`
   - URL: `http://app:8020`

公開デモでも、できれば Cloudflare Access を有効にしてください。現状の職員切り替えはデモ用の簡易セッションで、本番認証ではありません。

## 2. Dockge の Stack を作る

Dockge で新しい stack を作り、`deploy/dockge/compose.yaml` の内容を使います。

この compose は repo 内の `deploy/dockge` から起動する前提で、build context を `../..` にしています。Dockge の stack フォルダが repo 外にある場合は、次のどちらかにしてください。

- repo 全体を stack フォルダへ置く。
- `build.context` を Dockge サーバー上の repo checkout パスに変更する。

## 3. 環境変数

Dockge の `.env` または Environment に次を設定します。

```env
CLOUDFLARE_TUNNEL_TOKEN=Cloudflareで発行したtoken
APP_PORT=8020
```

`CLOUDFLARE_TUNNEL_TOKEN` は秘密情報です。Git に入れないでください。

## 4. 起動確認

Dockge で stack を起動します。

ローカル確認:

```text
http://DockgeサーバーのIP:8020/health
http://DockgeサーバーのIP:8020/
```

公開確認:

```text
https://Cloudflareで設定したホスト名/
```

Cloudflare の Public Hostname は `http://app:8020` を指します。`localhost` や Dockge ホストの IP ではなく、同じ Compose network 上の service 名 `app` を使います。

## 5. デモ運用メモ

- 公開URLには Cloudflare Access をかけるのがおすすめです。
- 園文例アップロードは `hoiku_plan_docs_data` volume に保存されます。
- 帳票一覧や作成済み帳票は現在 in-memory なので、コンテナ再起動で初期化されます。
- デモを初期化したい場合は、stack 停止後に `hoiku_plan_docs_data` volume を削除してください。
