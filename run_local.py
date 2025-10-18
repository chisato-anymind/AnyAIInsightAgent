#!/usr/bin/env python3
"""
ローカル実行用スクリプト
GitHubからクローンしたプロジェクトを簡単にローカルで実行できます
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """必要な依存関係をチェック"""
    print("🔍 依存関係をチェック中...")
    
    # Python バージョンチェック
    if sys.version_info < (3, 10):
        print("❌ Python 3.10以上が必要です")
        return False
    
    # requirements.txtの存在チェック
    if not Path("requirements.txt").exists():
        print("❌ requirements.txtが見つかりません")
        return False
    
    print("✅ 依存関係チェック完了")
    return True

def install_dependencies() -> str | None:
    """依存関係をインストールし、利用するPython実行パスを返す."""
    print("📦 依存関係をインストール中...")

    pip_command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-r",
        "requirements.txt",
    ]

    result = subprocess.run(
        pip_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)

    if result.returncode == 0:
        print("✅ 依存関係のインストール完了")
        return sys.executable

    if "externally-managed-environment" in result.stderr:
        return _install_with_virtualenv()

    print("❌ 依存関係のインストールに失敗しました")
    return None


def _install_with_virtualenv() -> str | None:
    """PEP 668環境向けに仮想環境を作成して依存関係をインストールする."""
    print("⚠️  システム管理下のPython環境が検出されました。仮想環境(.venv)を作成します。")

    venv_dir = Path(".venv")
    if not venv_dir.exists():
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        except subprocess.CalledProcessError as exc:
            print(f"❌ 仮想環境の作成に失敗しました: {exc}")
            return None

    venv_python = _resolve_venv_python(venv_dir)

    try:
        subprocess.run(
            [
                venv_python,
                "-m",
                "pip",
                "install",
                "-r",
                "requirements.txt",
            ],
            check=True,
        )
        print("✅ 仮想環境で依存関係をインストールしました (.venv)")
        print("   次回以降は .venv/bin/activate (またはScripts\\activate) を利用すると便利です。")
        return venv_python
    except subprocess.CalledProcessError as exc:
        print(f"❌ 仮想環境への依存関係インストールに失敗しました: {exc}")
        return None


def _resolve_venv_python(venv_dir: Path) -> str:
    """仮想環境内のPython実行ファイルパスを取得する."""
    if os.name == "nt":
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        python_path = venv_dir / "bin" / "python"
    return str(python_path)

def setup_environment():
    """環境変数を設定"""
    print("🔧 環境変数を設定中...")
    
    # .envファイルの存在チェック
    if not Path(".env").exists():
        print("⚠️  .envファイルが見つかりません")
        print("   Keys.txtから環境変数を作成しますか？ (y/n): ", end="")
        
        if input().lower() == 'y':
            create_env_from_keys()
    
    print("✅ 環境設定完了")

def create_env_from_keys():
    """Keys.txtを解析し、.envファイルを生成する."""
    keys_path = Path("Keys.txt")

    try:
        values = _load_keys_file(keys_path)
        if not values:
            print("⚠️  Keys.txtから有効なAPIキーを取得できませんでした。")
            values = _prompt_for_keys()

        Path(".env").write_text(_format_env(values), encoding="utf-8")
        print("✅ .envファイルを作成しました")
    except KeyboardInterrupt:
        print("\n❌ .envファイルの作成をユーザーが中断しました")
    except Exception as e:  # noqa: BLE001
        print(f"❌ .envファイルの作成に失敗: {e}")


def _prompt_for_keys() -> dict[str, str]:
    """対話的にAPIキーを入力させる."""
    print("⚠️  Keys.txtが見つからないか、解析できませんでした。APIキーを直接入力してください。")
    gemini_key = input("   GEMINI_API_KEY (未設定の場合は空のままEnter): ").strip()
    openai_key = input("   OPENAI_API_KEY (未設定の場合は空のままEnter): ").strip()
    return {"GEMINI_API_KEY": gemini_key, "OPENAI_API_KEY": openai_key}


def _format_env(values: dict[str, str]) -> str:
    """辞書から.envファイルの内容を生成する."""
    lines = ["# 環境変数設定"]
    for key in ("GEMINI_API_KEY", "OPENAI_API_KEY"):
        lines.append(f"{key}={values.get(key, '')}")

    extra_keys = {k: v for k, v in values.items() if k not in {"GEMINI_API_KEY", "OPENAI_API_KEY"}}
    for key, value in extra_keys.items():
        lines.append(f"{key}={value}")

    return "\n".join(lines) + "\n"


def _load_keys_file(path: Path) -> dict[str, str]:
    """Keys.txtの内容を解析して辞書にする."""
    if not path.exists():
        return {}

    content = path.read_text(encoding="utf-8")
    values: dict[str, str] = {}
    sequential: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parsed = _parse_key_line(line)
        if parsed is None:
            sequential.append(_strip_quotes(_remove_inline_comment(line)))
            continue

        key, value = parsed
        key_upper = key.upper()
        value = _strip_quotes(_remove_inline_comment(value))

        if "GEMINI" in key_upper and "API_KEY" in key_upper:
            values.setdefault("GEMINI_API_KEY", value)
        elif "OPENAI" in key_upper and "API_KEY" in key_upper:
            values.setdefault("OPENAI_API_KEY", value)
        else:
            values.setdefault(key_upper, value)

    if sequential:
        if sequential[0]:
            values.setdefault("GEMINI_API_KEY", sequential[0])
        if len(sequential) > 1 and sequential[1]:
            values.setdefault("OPENAI_API_KEY", sequential[1])

    return values


def _parse_key_line(line: str):
    """"KEY=VALUE"/"KEY: VALUE"形式の行を解析する."""
    for sep in ("=", ":"):
        if sep in line:
            left, right = line.split(sep, 1)
            return left.strip(), right.strip()
    return None


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _remove_inline_comment(value: str) -> str:
    return value.split('#', 1)[0].strip()

def run_application(python_exec: str):
    """アプリケーションを実行"""
    print("🚀 アプリケーションを起動中...")
    print("📍 アクセス先: http://localhost:25254")
    print("🛑 停止するには Ctrl+C を押してください")
    print("-" * 50)
    
    try:
        # 環境変数でポートを指定してアプリケーションを実行
        env = os.environ.copy()
        env['PORT'] = '25254'
        subprocess.run([
            python_exec, "-m", "app.main"
        ], check=True, env=env)
    except KeyboardInterrupt:
        print("\\n👋 アプリケーションを停止しました")
    except subprocess.CalledProcessError as e:
        print(f"❌ アプリケーションの実行に失敗: {e}")

def main():
    """メイン処理"""
    print("🎯 AnyAI Marketing Agent - ローカル実行")
    print("=" * 50)
    
    # 依存関係チェック
    if not check_requirements():
        sys.exit(1)
    
    # 依存関係インストール
    python_exec = install_dependencies()
    if not python_exec:
        sys.exit(1)
    
    # 環境設定
    setup_environment()
    
    # アプリケーション実行
    run_application(python_exec)

if __name__ == "__main__":
    main()
