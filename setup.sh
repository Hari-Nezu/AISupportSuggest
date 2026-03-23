#!/bin/bash
set -e

echo "=== AISupportSuggest セットアップ ==="

# Python バージョン確認
python3 --version

# 依存パッケージのインストール
echo ">> パッケージをインストール中..."
pip3 install -r requirements.txt

# Ollama の確認
echo ""
if command -v ollama &> /dev/null; then
    echo ">> Ollama が見つかりました: $(ollama --version)"
    echo ">> インストール済みモデル:"
    ollama list
    echo ""
    echo ">> llama3.2 がない場合は以下を実行してください:"
    echo "   ollama pull llama3.2"
else
    echo ">> Ollama が見つかりません。"
    echo "   https://ollama.com からインストールしてください。"
    echo "   インストール後: ollama pull llama3.2"
fi

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "起動方法:"
echo "  1. Ollama を起動: ollama serve"
echo "  2. アプリを起動: python3 main.py"
echo ""
echo "注意: 初回起動時に macOS の「アクセシビリティ」「オートメーション」の"
echo "      許可ダイアログが表示されます。「許可する」を選択してください。"
