# TrueNAS + Dockge + Cloudflare Tunnel デモ公開

`hoiku-plan-docs` を TrueNAS SCALE 上の Dockge stack として動かし、Cloudflare Tunnel で公開デモにする手順です。

この手順は「いまのPCで公開」ではなく、TrueNAS 上にソースとデータ用 dataset を置く前提です。

## 構成

- TrueNAS dataset に repo checkout を置きます。
- 園文例DBは TrueNAS dataset の `/data/facility.sqlite` として永続化します。
- Dockge から `deploy/truenas-dockge/compose.yaml` を起動します。
- Cloudflare Tunnel の Public Hostname は Compose 内の `app` service に向けます。

帳票一覧や作成済み帳票は現在 in-memory 実装のため、アプリ再起動で消えます。園文例DBだけが dataset に残ります。

## 1. TrueNAS 側の置き場所を作る

例では pool 名を `tank` にしています。実際の pool 名に置き換えてください。

```text
/mnt/tank/apps/hoiku-plan-docs/source
/mnt/tank/apps/hoiku-plan-docs/data
```

`source` にはこの repo を配置します。GitHub に置いた repo を TrueNAS の Shell で clone するか、SMB/SFTP/rsync でフォルダごとコピーしてください。

```sh
cd /mnt/tank/apps/hoiku-plan-docs
git clone <your-repository-url> source
mkdir -p data
```

`data` dataset はコンテナ内の `/data` に bind mount します。SQLite の書き込みに失敗する場合は、dataset の ACL または owner/group でコンテナ実行ユーザーが書き込めるようにしてください。Dockerfile の既定ユーザーは image 内の `appuser` です。
TrueNAS 側の dataset 権限に合わせたい場合は、Dockge の `.env` で `APP_UID` と `APP_GID` を変更します。

## 2. Cloudflare 側の準備

Cloudflare Zero Trust で Tunnel を作成します。

1. `Zero Trust` > `Networks` > `Tunnels` を開きます。
2. `Create a tunnel` で `Cloudflared` を選びます。
3. Connector の実行方法で `Docker` を選び、表示された tunnel token を控えます。
4. `Public Hostname` を追加します。
   - Subdomain: 例 `hoiku-docs-demo`
   - Domain: 例 `example.com`
   - Type: `HTTP`
   - URL: `http://app:8020`

公開デモでも Cloudflare Access を有効にしてください。現状の職員切り替えはデモ用の簡易セッションで、本番認証ではありません。

## 3. Dockge の stack を作る

Dockge で新しい stack を作り、`deploy/truenas-dockge/compose.yaml` の内容を使います。

Dockge の Environment または `.env` に次を設定します。

```env
HOIKU_PLAN_DOCS_SOURCE=/mnt/tank/apps/hoiku-plan-docs/source
HOIKU_PLAN_DOCS_DATA=/mnt/tank/apps/hoiku-plan-docs/data
CLOUDFLARE_TUNNEL_TOKEN=Cloudflareで発行したtoken
APP_PORT=8020
APP_UID=1000
APP_GID=1000
```

テンプレートは [deploy/truenas-dockge/.env.example](../deploy/truenas-dockge/.env.example) にあります。`CLOUDFLARE_TUNNEL_TOKEN` は秘密情報なので Git に入れないでください。

## 4. 起動確認

Dockge で stack を起動します。

LAN 内確認:

```text
http://TrueNASのIP:8020/health
http://TrueNASのIP:8020/
```

公開確認:

```text
https://Cloudflareで設定したホスト名/
```

Cloudflare の Public Hostname は `localhost` や TrueNAS の IP ではなく、同じ Compose network 上の service 名 `app` を使って `http://app:8020` にします。

## 5. 更新方法

TrueNAS 側の repo を更新してから Dockge で stack を再作成します。

```sh
cd /mnt/tank/apps/hoiku-plan-docs/source
git pull
```

Docker image は `hoiku-plan-docs-demo:truenas` として build されます。ソース更新後は Dockge で rebuild してください。

## 6. デモ運用メモ

- 公開URLには Cloudflare Access をかけます。
- 園文例アップロードは `HOIKU_PLAN_DOCS_DATA` の `facility.sqlite` に保存されます。
- 帳票一覧や作成済み帳票は現在 in-memory なので、コンテナ再起動で初期化されます。
- デモを初期化したい場合は、stack 停止後に `HOIKU_PLAN_DOCS_DATA/facility.sqlite` を削除します。
- TrueNAS の Apps YAML へ直接貼る場合も同じ compose を使えますが、日常運用は Dockge のほうが stack の編集と再作成がしやすいです。
