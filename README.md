# Azure上へのToDoアプリ デプロイガイド

このドキュメントは、Azure上にEntra ID認証とAzure SQL Databaseを利用したPython (Flask) 製のToDoアプリケーションをデプロイするための手順書です。

🚀 ゴール
https://<あなたのFQDN>/ にアクセスすると、Entra IDで認証が行われ、個人のタスクをAzure SQL Databaseに保存できるWebアプリケーションを構築します。

🛠️ 使用技術スタック
クラウドプラットフォーム: Azure

仮想マシン: Azure VM (Ubuntu 22.04 LTS)

データベース: Azure SQL Database

認証: Azure Entra ID

コンテナ: Docker

リバースプロキシ (推奨): Nginx + Let's Encrypt (HTTPS化)

## 1. Azureリソースの準備 (VMとPublic IP/DNS)

1.1. 仮想マシン (VM) の作成

Azureポータルから以下の設定で仮想マシンを作成します。

基本設定:
  - リソースグループ: 任意 (例: rg-todo)
  - イメージ: Ubuntu 22.04 LTS
  - サイズ: B2s
  - 認証: パスワード

ネットワーク:
  - 新しいNSG (ネットワークセキュリティグループ) を作成し、以下の受信ポートを許可します。
    - HTTP (80/TCP)
    - HTTPS (443/TCP)
    - SSH (22/TCP)
  - パブリックIP: 静的 (Static) を選択します。

1.2. Public IPへのDNSラベル割り当て
作成したPublic IPリソースを開きます。

「構成」メニューから「DNS名ラベル」を設定します。(例: todoapp-japaneast)

これにより、todoapp-japaneast.japaneast.cloudapp.azure.com のようなFQDN (Fully Qualified Domain Name) が作成されます。

📝 Note: このFQDNは、後のEntra ID設定や環境変数で 本番URLとして何度も使用します。以後、このFQDNを <FQDN> と表記します。

## 2. Azure Entra ID アプリケーションの登録

2.1. 新規アプリ登録
Azureポータルで Azure Entra ID に移動します。

アプリの登録 > 新規登録 を選択します。

以下の情報を入力して登録します。

名前: TodoApp

サポートされているアカウントの種類: この組織ディレクトリのみに含まれるアカウント (単一テナント)

2.2. クライアント情報の取得
概要ページで、以下の値を控えます。

アプリケーション (クライアント) ID

ディレクトリ (テナント) ID

証明書とシークレットページで、新しいクライアントシークレット を作成し、その 値 を控えます。（注意：この値は一度しか表示されません）

2.3. リダイレクトURIとログアウトURLの設定
認証ページで プラットフォームを追加 > Web を選択します。

以下のURLを設定します。

リダイレクト URI: https://<FQDN>/callback

フロントチャネル ログアウト URL: https://<FQDN>/

Implicit grant and hybrid flows のチェックは 不要 です。

設定を保存します。

2.4. .env 用に準備する値
以下の値を後ほど .env ファイルに設定します。

AUTHORITY: <https://login.microsoftonline.com/><TENANT_ID>

OIDC_SCOPES: openid profile email (デフォルトのスコープ。Microsoft Graphの権限追加は不要です)

🔒 アクセス制御: 特定のユーザーのみにサインインを許可したい場合は、「エンタープライズアプリケーション」から該当アプリを選択し、「プロパティ」で 「ユーザーの割り当てが必要ですか?」を「はい」 に設定後、「ユーザーとグループ」で対象ユーザーを割り当ててください。

## 3. Azure SQL Database の準備

3.1. サーバーとデータベースの作成
SQLサーバー を作成します。(例: todo-sqls-japaneast)

サーバー管理者ログインと強力なパスワードを設定します。

データベース を作成します。(例: tododb)

3.2. ファイアウォール設定
作成したSQLサーバーの「ネットワーク」ページに移動します。

「選択されたネットワーク」 を有効にします。

例外として 「Azure サービスおよびリソースにこのサーバーへのアクセスを許可する」にチェックを入れます。

または、VMのパブリックIPアドレスを許可リストに追加します。

3.3. アプリケーション用ユーザーの作成
ポータルのクエリエディター (プレビュー) を使い、サーバー管理者としてサインインして以下のSQLクエリを実行します。

```sql
-- ユーザー作成
CREATE USER [todo_user] WITH PASSWORD = 'Strong_Pa55word_ChangeMe!';

-- 権限付与
ALTER ROLE db_datareader ADD MEMBER [todo_user];
ALTER ROLE db_datawriter ADD MEMBER [todo_user];
ALTER ROLE db_ddladmin  ADD MEMBER [todo_user];
-- ※db_ddladmin が CREATE TABLE 権限も持つ

-- テーブルが存在しない場合のみ作成
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='todos' AND xtype='U')
BEGIN
    CREATE TABLE todos (
        id INT IDENTITY(1,1) PRIMARY KEY,
        title NVARCHAR(255) NOT NULL,
        created_at DATETIME DEFAULT GETDATE()
    );
END
ELSE
BEGIN
    -- 既に存在する場合はカラム定義を変更（NOT NULL にするなど）
    ALTER TABLE todos
    ALTER COLUMN title NVARCHAR(255) NOT NULL;
END

```

Tip: アプリケーションの初回起動後、テーブルが作成されたら、セキュリティ向上のために db_ddladmin 権限は削除することを推奨します。

3.4. 接続文字列の準備
後ほど .env ファイルで使用する接続文字列を準備します。

```sql
mssql+pyodbc://todo_user:Strong_Pa55word_ChangeMe!@<server>.database.windows.net:1433/tododb?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30
```

<server> はSQLサーバー名に置き換えてください。

## 4. 仮想マシン (VM) のセットアップ

VMにSSHで接続し、以下のコマンドを実行します。

4.1. 基本設定とDockerのインストール
Bash

### パッケージリストの更新とアップグレード

```bash
sudo apt-get update -y && sudo apt-get upgrade -y

# Dockerのインストールと有効化
sudo apt-get install -y docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker $USER

# 変更を反映するために一度ログアウトし、再接続してください
exit
```

4.2. アプリケーションの配置
SSHで再接続後、アプリケーションのソースコードを配置します。

### アプリケーション用ディレクトリを作成

```bash
mkdir -p ~/apps && cd ~/apps
git clone git@github.com:daifuku700/todo-app.git
```

4.3. .env ファイルの作成と編集
todoapp ディレクトリに移動し、環境変数ファイルを作成・編集します。

```bash
cp todo-app/.env.example todo-app/.env
nano todo-app/.env
```

ファイルの内容を、これまでに控えたあなたの値で 必ず 編集してください。

### .env.example をコピーして作成

### Flask App Settings

FLASK_SECRET_KEY=<強力なランダム文字列を生成して設定>
PORT=8000

### Entra ID Settings

TENANT_ID=<Entra のテナントID>
CLIENT_ID=<アプリ登録のクライアントID>
CLIENT_SECRET=<クライアントシークレットの値>
AUTHORITY=<https://login.microsoftonline.com/><TENANT_ID>
REDIRECT_URI=https://<FQDN>/callback
POST_LOGOUT_REDIRECT_URI=https://<FQDN>/
OIDC_SCOPES=openid profile email

### Azure SQL Database Settings

AZURE_SQL_CONNECTION_STRING=mssql+pyodbc://todo_user:Strong_Pa55word_ChangeMe!@<server>.database.windows.net:1433/tododb?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30

## 5. コンテナのビルドと起動

todoapp ディレクトリ内で作業します。

```bash
cd ~/apps/todo-app
```

5.1. Dockerイメージのビルド
DockerfileにはODBC Driver 18のセットアップも含まれています。

```bash
docker build -t todoapp:latest .
```

5.2. コンテナの起動
この時点では、HTTP (80) で直接コンテナを公開します。

```bash
docker run -d --name todoapp \
  --restart=always \
  --env-file .env \
  -p 80:8000 \
  todoapp:latest]
```

5.3. 動作確認
VM内部からの確認:

```bash
curl -I <http://localhost/>
```

### HTTP/1.1 302 Found (サインインページへのリダイレクト) が返ればOK

外部からの確認:
ブラウザで http://<FQDN>/ にアクセスし、Entra IDのサインイン画面にリダイレクトされることを確認します。

✅ DBテーブル作成: 最初のユーザーがログインに成功すると、db_ddladmin権限によって todos テーブルが自動的にデータベース内に作成されます。

## 6. 【推奨】本番運用のためのHTTPS化 (Nginx + Let's Encrypt)

TLS終端をNginxリバースプロキシに担当させ、アプリケーションコンテナは外部に直接公開しない構成に変更します。

6.1. コンテナの再起動 (ローカルバインド)

```bash

# 既存のコンテナを停止・削除

docker rm -f todoapp

# VM内部(127.0.0.1)からのみアクセスできるようにして再起動

docker run -d --name todoapp \
  --restart=always \
  --env-file .env \
  -p 127.0.0.1:8000:8000 \
  todoapp:latest
```

6.2. NginxとCertbotのインストール・設定

```bash
# 必要なパッケージをインストール

sudo apt-get update && sudo apt-get install -y nginx certbot python3-certbot-nginx

# Nginxのサイト設定ファイルを作成 (<FQDN>はあなたのドメインに書き換える)

sudo tee /etc/nginx/sites-available/todoapp <<'EOF'
server {
    listen 80;
    server_name <FQDN>;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
EOF

# 設定を有効化してNginxをリロード

sudo ln -sf /etc/nginx/sites-available/todoapp /etc/nginx/sites-enabled/todoapp
sudo nginx -t && sudo systemctl reload nginx
```

6.3. Let's EncryptによるSSL証明書の取得
対話形式でメールアドレスの登録や規約への同意が求められます。

```bash
# <FQDN>はあなたのドメインに書き換える

sudo certbot --nginx -d <FQDN>
✨ Certbotが自動的にNginxの設定を更新し、HTTPS (443) を有効化、およびHTTPからHTTPSへのリダイレクト設定を追加してくれます。
```

## 7. 🩺 トラブルシューティング

問題が発生した場合のチェックポイントです。

リダイレクトURIの不一致:

Entra IDのアプリ登録画面にある https://<FQDN>/callback と、.env ファイルの REDIRECT_URI が 完全に一致 しているか確認してください。Typoや http/https の違いに注意。

クライアントシークレットの期限切れ:

シークレットを再作成した場合、.env ファイルを更新し、コンテナを再起動する必要があります。

SQLデータベースに接続できない:

Azure SQL Serverのファイアウォール設定で「Azureサービスおよびリソースに...アクセスを許可する」が有効か、VMのPublic IPが許可されているか確認。

接続文字列の driver=ODBC+Driver+18+for+SQL+Server が正しいか確認。

初回起動時にはユーザーに db_ddladmin 権限が必要。

コンテナの500エラー:

まずはコンテナのログを確認します。

Bash

docker logs todoapp -n 100
.env ファイル内の環境変数（特に AZURE_SQL_CONNECTION_STRING やEntra ID関連）の設定ミスが原因であることが多いです。

タイムゾーン/時計のズレ:

sudo timedatectl を実行し、NTPサービスが有効で時刻が同期されているか確認してください。トークンの有効期限検証に影響することがあります。

## 8. 🚢 運用コマンド・更新手順

```bash

# ログをリアルタイムで確認

docker logs -f todoapp

# コンテナの再起動

docker restart todoapp

# .env ファイルを更新した場合のコンテナ再作成

docker rm -f todoapp
docker run -d --name todoapp --restart=always --env-file .env -p 127.0.0.1:8000:8000 todoapp:latest

# アプリケーションを更新してイメージを再ビルドした場合

docker build -t todoapp:latest .

# その後、上記のコンテナ再作成コマンドを実行
```

## 9. (任意) docker-compose を利用する場合

docker-compose をインストール後、todoapp ディレクトリに以下の docker-compose.yml を作成すると、docker compose up -d で簡単に起動・管理できます。

```bash
sudo apt-get install -y docker-compose
YAML

# docker-compose.yml

services:
  web:
    build: .
    container_name: todoapp
    restart: always
    env_file: .env
    ports:
      - "127.0.0.1:8000:8000"

```

## 10. 🛡️ セキュリティのベストプラクティス

シークレット管理: .env ファイルの代わりに、Azure Key Vault を使用してシークレットを安全に管理し、VM起動時に取得することを検討してください。

ユーザー割り当て: Entra IDのエンタープライズアプリケーション設定で ユーザー割り当てを必須 にし、許可されたユーザーのみがアプリを利用できるように制限します。

ネットワークセキュリティ: NSGでは、アプリケーションに必要な 80, 443, 22 以外のインバウンドポートはすべて閉じます。

データベース権限の縮小: アプリケーションの初回起動でテーブルが作成された後は、db_ddladmin 権限をユーザーから削除し、読み書き権限のみに絞ります。
