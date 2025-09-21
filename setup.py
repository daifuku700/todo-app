#!/usr/bin/env python3

"""
nginx設定スクリプト（Python版）
.envファイルからVM_DOMAINを読み取り、nginx設定を作成
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def read_env_variable(env_file_path, variable_name):
    """
    .envファイルから指定された変数の値を読み取る

    Args:
        env_file_path (str): .envファイルのパス
        variable_name (str): 取得したい変数名

    Returns:
        str: 変数の値（見つからない場合はNone）
    """
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{variable_name}="):
                    value = line.split('=', 1)[1].strip()
                    return value
    except FileNotFoundError:
        return None
    return None


def run_command(command, shell=False):
    """
    コマンドを実行し、結果を返す

    Args:
        command (list or str): 実行するコマンド
        shell (bool): シェル経由で実行するかどうか

    Returns:
        tuple: (returncode, stdout, stderr)
    """
    try:
        if shell:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=False
            )
        else:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False
            )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def create_nginx_config(vm_domain):
    """
    nginx設定ファイルを作成する

    Args:
        vm_domain (str): VMのドメイン名
    """
    nginx_config = f"""server {{
    listen 80;
    server_name {vm_domain};

    location / {{
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }}
}}
"""

    # 一時ファイルを作成してからsudoで移動
    temp_file = "/tmp/todoapp_nginx_config"
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(nginx_config)

        # sudoを使って設定ファイルを配置
        returncode, stdout, stderr = run_command(
            f"sudo cp {temp_file} /etc/nginx/sites-available/todoapp",
            shell=True
        )

        # 一時ファイルを削除
        os.remove(temp_file)

        if returncode != 0:
            print(f"エラー: nginx設定ファイルの作成に失敗しました: {stderr}")
            return False

        print("nginx設定ファイル /etc/nginx/sites-available/todoapp を作成しました")
        return True

    except Exception as e:
        print(f"エラー: nginx設定ファイルの作成中にエラーが発生しました: {e}")
        return False


def main():
    """メイン処理"""
    print("nginx設定スクリプト（Python版）を開始します...")

    # .envファイルの存在確認
    env_file = ".env"
    if not os.path.exists(env_file):
        print("エラー: .envファイルが見つかりません")
        print(".env.sampleを参考に.envファイルを作成してください")
        sys.exit(1)

    # .envファイルからVM_DOMAINを取得
    vm_domain = read_env_variable(env_file, "VM_DOMAIN")

    if not vm_domain:
        print("エラー: .envファイルにVM_DOMAINが設定されていません")
        print("VM_DOMAIN=your-domain.comの形式で設定してください")
        sys.exit(1)

    print(f"VM_DOMAIN: {vm_domain}")

    # nginx設定ファイルの作成
    print("nginx設定ファイルを作成しています...")
    if not create_nginx_config(vm_domain):
        sys.exit(1)

    # デフォルト設定ファイルの削除
    default_config_path = "/etc/nginx/sites-available/default"
    if os.path.exists(default_config_path):
        print("デフォルト設定ファイルを削除しています...")
        returncode, stdout, stderr = run_command("sudo rm /etc/nginx/sites-available/default", shell=True)
        if returncode == 0:
            print("/etc/nginx/sites-available/default を削除しました")
        else:
            print(f"警告: デフォルト設定ファイルの削除に失敗しました: {stderr}")
    else:
        print("/etc/nginx/sites-available/default は既に存在しません")

    # sites-enabledのシンボリックリンクの管理
    default_enabled_path = "/etc/nginx/sites-enabled/default"
    if os.path.islink(default_enabled_path):
        print("デフォルトサイトのシンボリックリンクを削除しています...")
        returncode, stdout, stderr = run_command("sudo rm /etc/nginx/sites-enabled/default", shell=True)
        if returncode != 0:
            print(f"警告: デフォルトサイトのシンボリックリンク削除に失敗しました: {stderr}")

    # 新しい設定のシンボリックリンクを作成
    todoapp_enabled_path = "/etc/nginx/sites-enabled/todoapp"
    if not os.path.islink(todoapp_enabled_path):
        print("todoappサイトを有効化しています...")
        returncode, stdout, stderr = run_command(
            "sudo ln -s /etc/nginx/sites-available/todoapp /etc/nginx/sites-enabled/todoapp",
            shell=True
        )
        if returncode != 0:
            print(f"エラー: シンボリックリンクの作成に失敗しました: {stderr}")
            sys.exit(1)

    # nginx設定のテスト
    print("nginx設定をテストしています...")
    returncode, stdout, stderr = run_command("sudo nginx -t", shell=True)

    if returncode == 0:
        print("nginx設定テストが成功しました")
        print("nginxを再起動するには: sudo systemctl reload nginx")
    else:
        print("エラー: nginx設定にエラーがあります")
        print(f"nginx -t の出力: {stderr}")
        sys.exit(1)

    print("nginx設定が完了しました")
    print(f"サーバー名: {vm_domain}")


if __name__ == "__main__":
    main()
