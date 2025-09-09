# ToDo App (Flask + Azure Entra ID + Azure SQL)

Azure VM 上で動作し、**Azure Entra ID** による認証と **Azure SQL Database** を使ってタスク管理ができるシンプルな ToDo アプリです。
UI は Bootstrap ベースで、ログインしたユーザーごとにタスクを管理できます。

---

## 機能概要

- Azure Entra ID (旧 Azure AD) によるシングルサインオン（OpenID Connect 認証）
- Azure SQL Database にタスクを保存（SQLAlchemy 利用）
- タスクの追加 / 完了切替 / 削除
- Docker コンテナでデプロイ可能
- 本番では Nginx + Let’s Encrypt で HTTPS 化を推奨

---

## 前提条件

- Azure サブスクリプション（VM, SQL, Entra ID が利用可能）
- Azure VM（Ubuntu 22.04/24.04）
- Docker 環境
- Entra ID の管理者権限（アプリ登録が必要）

---

## セットアップ手順

### 1. Azure VM 準備

1. Ubuntu 22.04/24.04 VM を作成
   - 受信ポート: **80, 443, 22**
   - パブリック IP: **静的** を選択
2. Public IP に DNS 名ラベルを設定
   - 例: `todoapp-japaneast.japaneast.cloudapp.azure.com` → 以後 `<FQDN>` として利用

---

### 2. Azure Entra ID アプリ登録

1. Entra ID → **アプリの登録** → 新規登録
   - リダイレクト URI: `https://<FQDN>/callback`
   - ログアウト URL: `https://<FQDN>/`
2. **クライアントID**, **テナントID**, **クライアントシークレット** を控える
3. API のアクセス許可 → `openid`, `profile`, `email` が含まれていればOK

---

### 3. Azure SQL Database 準備

1. SQL サーバー & DB (`tododb`) 作成
2. VM のパブリック IP をファイアウォールに追加
3. ユーザー作成と権限付与（初回は `db_ddladmin` が必要）

   ```sql
   CREATE USER [todo_user] WITH PASSWORD = 'Strong_Pa55word_ChangeMe!';
   ALTER ROLE db_datareader ADD MEMBER [todo_user];
   ALTER ROLE db_datawriter ADD MEMBER [todo_user];
   ALTER ROLE db_ddladmin  ADD MEMBER [todo_user];
