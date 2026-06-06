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

例では pool 名を `main` にしています。実際の pool 名に置き換えてください。

```text
/mnt/main/apps/hoiku-plan-docs/source
/mnt/main/apps/hoiku-plan-docs/data
```

`source` にはこの repo を配置します。GitHub に置いた repo を TrueNAS の Shell で clone するか、SMB/SFTP/rsync でフォルダごとコピーしてください。

```sh
cd /mnt/main/apps/hoiku-plan-docs
git clone <your-repository-url> source
mkdir -p data
```

GitHub などにまだ置いていない場合は、PC から TrueNAS へフォルダごとコピーします。コピー後、`Dockerfile` が `source` の直下にある状態にしてください。

```text
/mnt/main/apps/hoiku-plan-docs/source/Dockerfile
/mnt/main/apps/hoiku-plan-docs/source/app
/mnt/main/apps/hoiku-plan-docs/source/pyproject.toml
```

`source/hoiku-plan-docs/Dockerfile` のように1階層深く入っている場合は、Dockge の `HOIKU_PLAN_DOCS_SOURCE` をその深いパスに直すか、中身を `source` 直下へ移動してください。

SMB/SFTP でコピーする場合は、`/mnt/.ix-apps/app_mounts/dockge/stacks/...` へ直接アップロードしないでください。そこは TrueNAS Apps / Dockge の管理下で、一般ユーザーからの書き込みが拒否されることがあります。zip で持ち込む場合は、先に `/mnt/main/apps/hoiku-plan-docs` のような通常 dataset へ置いてから展開します。

```sh
mkdir -p /mnt/main/apps/hoiku-plan-docs/source
mkdir -p /mnt/main/apps/hoiku-plan-docs/data
cd /mnt/main/apps/hoiku-plan-docs/source
unzip ../hoiku-plan-docs-truenas.zip
ls -la Dockerfile app pyproject.toml
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

GitHub の公開 repo から直接 pull して build する場合は、`deploy/truenas-dockge/compose.github.yaml` の内容を使います。この場合、TrueNAS に `source` フォルダをコピーする必要はありません。

```env
HOIKU_PLAN_DOCS_GIT_CONTEXT=https://github.com/hoikuict/hoiku-plan-docs.git#main
HOIKU_PLAN_DOCS_DATA=/mnt/main/apps/hoiku-plan-docs/data
CLOUDFLARE_TUNNEL_TOKEN=Cloudflareで発行したtoken
APP_PORT=8020
APP_UID=1000
APP_GID=1000
```

`#main` は branch 指定です。別 branch を使う場合は `#develop` のように変えてください。repo が private の場合、この方式では認証情報の扱いが難しいため、GitHub Actions で container image を作って GHCR から `image:` で pull する方式を推奨します。

もし repo の中身を Dockge の stack フォルダへ直接置く場合は、`deploy/truenas-dockge/compose.stack-local.yaml` の内容を使います。この形では `Dockerfile`、`app`、`pyproject.toml` が stack フォルダ直下にある前提です。

```text
/mnt/.ix-apps/app_mounts/dockge/stacks/hoiku-docs-demo/Dockerfile
/mnt/.ix-apps/app_mounts/dockge/stacks/hoiku-docs-demo/app
/mnt/.ix-apps/app_mounts/dockge/stacks/hoiku-docs-demo/pyproject.toml
/mnt/.ix-apps/app_mounts/dockge/stacks/hoiku-docs-demo/compose.yaml
```

ただし `/mnt/.ix-apps/...` はアプリ管理領域なので、Windows から直接アップロードできない場合があります。その場合は stack フォルダ直下方式ではなく、通常 dataset に source を置く `compose.yaml` 方式を使ってください。

`HOIKU_PLAN_DOCS_SOURCE` と `HOIKU_PLAN_DOCS_DATA` は、未設定なら次の既定値を使います。

- `HOIKU_PLAN_DOCS_SOURCE=/mnt/main/apps/hoiku-plan-docs/source`
- `HOIKU_PLAN_DOCS_DATA=/mnt/main/apps/hoiku-plan-docs/data`

Dockge の Environment または `.env` に次を設定します。パスがこの既定値どおりなら、最低限 `CLOUDFLARE_TUNNEL_TOKEN` だけ入れれば起動できます。

```env
HOIKU_PLAN_DOCS_SOURCE=/mnt/main/apps/hoiku-plan-docs/source
HOIKU_PLAN_DOCS_DATA=/mnt/main/apps/hoiku-plan-docs/data
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

## 5. よくあるエラー

### `failed to read dockerfile: open Dockerfile: no such file or directory`

Dockge が `HOIKU_PLAN_DOCS_SOURCE` の場所で `Dockerfile` を見つけられていません。

TrueNAS の Shell で次を確認してください。

```sh
ls -la /mnt/main/apps/hoiku-plan-docs/source/Dockerfile
ls -la /mnt/main/apps/hoiku-plan-docs/source/app
ls -la /mnt/main/apps/hoiku-plan-docs/source/pyproject.toml
```

Dockge stack フォルダに repo を直接置いた場合は、代わりに次を確認します。

```sh
cd /mnt/.ix-apps/app_mounts/dockge/stacks/hoiku-docs-demo
ls -la Dockerfile app pyproject.toml
```

ここに3つともある場合は、compose の build context を `.` にしてください。`deploy/truenas-dockge/compose.stack-local.yaml` がその形です。

`Dockerfile` がない場合は、最新の repo を TrueNAS 側の `source` に反映してください。このPCで作った未コミットの `Dockerfile`、`deploy/`、`docs/` も TrueNAS 側にコピーまたは push/pull する必要があります。

`Dockerfile` があるのに同じエラーが出る場合は、Dockge の Environment に設定した `HOIKU_PLAN_DOCS_SOURCE` が実際の repo パスとずれています。`HOIKU_PLAN_DOCS_SOURCE` は `Dockerfile` が直接置かれているディレクトリを指定します。

TrueNAS 内で場所を探す場合は次で確認できます。

```sh
find /mnt/main -maxdepth 6 -name Dockerfile -o -name pyproject.toml
```

### `pull access denied for hoiku-plan-docs-demo`

これは Docker Hub から image を pull できないという警告です。ローカルで build するアプリなので、先に app image を build する必要があります。

Dockge では、初回は `起動` や `更新` ではなく `デプロイ` を使って build してください。Shell で直す場合は stack の compose がある場所で次を実行します。

```sh
docker compose build app
docker compose up -d
```

`failed to read dockerfile` も一緒に出ている場合は、build 以前に `Dockerfile` の場所が違います。先に `HOIKU_PLAN_DOCS_SOURCE` を直してください。

### `cp: cannot create regular file '/data/facility.sqlite': Permission denied`

`HOIKU_PLAN_DOCS_DATA` に指定した TrueNAS dataset へ、コンテナユーザーが書き込めていません。既定では `APP_UID=1000`、`APP_GID=1000` で app を動かします。

TrueNAS の Shell で次を実行します。

```sh
sudo mkdir -p /mnt/main/apps/hoiku-plan-docs/data
sudo chown -R 1000:1000 /mnt/main/apps/hoiku-plan-docs/data
sudo chmod -R u+rwX,g+rwX /mnt/main/apps/hoiku-plan-docs/data
```

そのあと Dockge で再デプロイします。急ぎのデモ確認だけなら次でも通りますが、広い権限なので本運用では避けてください。

```sh
sudo chmod 777 /mnt/main/apps/hoiku-plan-docs/data
```

## 6. 更新方法

TrueNAS 側の repo を更新してから Dockge で stack を再作成します。

```sh
cd /mnt/tank/apps/hoiku-plan-docs/source
git pull
```

Docker image は `hoiku-plan-docs-demo:truenas` として build されます。ソース更新後は Dockge で rebuild してください。

## 7. デモ運用メモ

- 公開URLには Cloudflare Access をかけます。
- 園文例アップロードは `HOIKU_PLAN_DOCS_DATA` の `facility.sqlite` に保存されます。
- 帳票一覧や作成済み帳票は現在 in-memory なので、コンテナ再起動で初期化されます。
- デモを初期化したい場合は、stack 停止後に `HOIKU_PLAN_DOCS_DATA/facility.sqlite` を削除します。
- TrueNAS の Apps YAML へ直接貼る場合も同じ compose を使えますが、日常運用は Dockge のほうが stack の編集と再作成がしやすいです。
