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
