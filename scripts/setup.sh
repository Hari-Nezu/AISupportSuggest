#!/bin/bash
set -e

echo "=== AISupportSuggest セットアップ ==="

# Go バージョン確認
if ! command -v go &>/dev/null; then
    echo "エラー: Go が見つかりません。https://go.dev/dl/ からインストールしてください。"
    exit 1
fi
go version

# Go ビルド
echo ">> ビルド中..."
mkdir -p bin
go build -o bin/aisupportsuggest ./cmd/aisupportsuggest
echo ">> bin/aisupportsuggest をビルドしました"

# Swift ビューアのビルド（macOS のみ・任意）
if [[ "$(uname)" == "Darwin" ]]; then
    echo ">> Swift ビューアをビルド中..."
    if swiftc src/ui/SuggestionViewer.swift -o bin/SuggestionViewer 2>&1; then
        echo ">> bin/SuggestionViewer をビルドしました"
    else
        echo ">> 警告: Swift ビルドに失敗しました。ブラウザフォールバックを使用します。"
    fi
fi

# API キーの確認
echo ""
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ">> 警告: ANTHROPIC_API_KEY が設定されていません。"
    echo "   以下の方法で設定してください:"
    echo ""
    echo "   export ANTHROPIC_API_KEY='sk-ant-...'"
    echo "   # 永続化する場合は ~/.zshrc に追記してください"
else
    echo ">> ANTHROPIC_API_KEY が設定されています。"
fi

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "起動方法:"
echo "  bin/aisupportsuggest"
echo ""
echo "注意: 初回起動時に macOS の「オートメーション」の"
echo "      許可ダイアログが表示されます。「許可する」を選択してください。"
