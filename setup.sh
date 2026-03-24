#!/bin/bash
set -e

echo "=== AISupportSuggest セットアップ ==="

# Python バージョン確認
python3 --version

# 依存パッケージのインストール
echo ">> パッケージをインストール中..."
pip3 install -r requirements.txt

# Swift ビューアのビルド（macOS のみ）
if [[ "$(uname)" == "Darwin" ]]; then
    echo ">> Swift ビューアをビルド中..."
    mkdir -p bin
    if swiftc src/ui/SuggestionViewer.swift -o bin/SuggestionViewer 2>&1; then
        echo ">> bin/SuggestionViewer をビルドしました"
    else
        echo ">> 警告: Swift ビルドに失敗しました。Python フォールバックを使用します。"
    fi
fi

# API キーの確認
echo ""
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ">> 警告: ANTHROPIC_API_KEY が設定されていません。"
    echo "   以下の方法で設定してください:"
    echo ""
    echo "   # 毎回設定する場合:"
    echo "   export ANTHROPIC_API_KEY='sk-ant-...'"
    echo ""
    echo "   # 永続化する場合（~/.zshrc に追記）:"
    echo "   echo 'export ANTHROPIC_API_KEY=\"sk-ant-...\"' >> ~/.zshrc"
    echo "   source ~/.zshrc"
else
    echo ">> ANTHROPIC_API_KEY が設定されています。"
fi

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "起動方法:"
echo "  python3 main.py"
echo ""
echo "注意: 初回起動時に macOS の「オートメーション」の"
echo "      許可ダイアログが表示されます。「許可する」を選択してください。"
