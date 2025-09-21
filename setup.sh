#!/bin/bash

# nginx設定スクリプト
# .envファイルからVM_DOMAINを読み取り、nginx設定を作成

set -e  # エラーが発生した場合にスクリプトを停止

# .envファイルの存在確認
if [ ! -f ".env" ]; then
    echo "エラー: .envファイルが見つかりません"
    echo ".env.sampleを参考に.envファイルを作成してください"
    exit 1
fi

# .envファイルからVM_DOMAINを取得
VM_DOMAIN=$(grep "^VM_DOMAIN=" .env | cut -d'=' -f2 | tr -d ' ')

if [ -z "$VM_DOMAIN" ]; then
    echo "エラー: .envファイルにVM_DOMAINが設定されていません"
    echo "VM_DOMAIN=your-domain.comの形式で設定してください"
    exit 1
fi

echo "VM_DOMAIN: $VM_DOMAIN"

# nginx設定ファイルの作成
echo "nginx設定ファイルを作成しています..."

sudo tee /etc/nginx/sites-available/todoapp > /dev/null << 'EOF'
server {
    listen 80;
    server_name $VM_DOMAIN;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
    }
}
EOF

echo "nginx設定ファイル /etc/nginx/sites-available/todoapp を作成しました"

# デフォルト設定ファイルの削除
if [ -f "/etc/nginx/sites-available/default" ]; then
    echo "デフォルト設定ファイルを削除しています..."
    sudo rm /etc/nginx/sites-available/default
    echo "/etc/nginx/sites-available/default を削除しました"
else
    echo "/etc/nginx/sites-available/default は既に存在しません"
fi

# sites-enabledのシンボリックリンクの管理
if [ -L "/etc/nginx/sites-enabled/default" ]; then
    echo "デフォルトサイトのシンボリックリンクを削除しています..."
    sudo rm /etc/nginx/sites-enabled/default
fi

# 新しい設定のシンボリックリンクを作成
if [ ! -L "/etc/nginx/sites-enabled/todoapp" ]; then
    echo "todoappサイトを有効化しています..."
    sudo ln -s /etc/nginx/sites-available/todoapp /etc/nginx/sites-enabled/todoapp
fi

# nginx設定のテスト
echo "nginx設定をテストしています..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "nginx設定テストが成功しました"
    echo "nginxを再起動するには: sudo systemctl reload nginx"
else
    echo "エラー: nginx設定にエラーがあります"
    exit 1
fi

echo "nginx設定が完了しました"
echo "サーバー名: $VM_DOMAIN"
