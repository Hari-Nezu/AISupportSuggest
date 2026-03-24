@echo off
echo === AISupportSuggest セットアップ (Windows) ===

:: Python バージョン確認
python --version
if errorlevel 1 (
    echo Python が見つかりません。https://python.org からインストールしてください。
    pause
    exit /b 1
)

:: 依存パッケージのインストール
echo.
echo ^>^> パッケージをインストール中...
pip install -r requirements.txt

:: API キーの確認
echo.
if "%ANTHROPIC_API_KEY%"=="" (
    echo ^>^> 警告: ANTHROPIC_API_KEY が設定されていません。
    echo    以下の方法で設定してください:
    echo.
    echo    [今回のセッションのみ]
    echo    set ANTHROPIC_API_KEY=sk-ant-...
    echo.
    echo    [永続化する場合] システム環境変数に追加:
    echo    1. Windowsキー → 「環境変数」で検索
    echo    2. 「システム環境変数の編集」→「環境変数」
    echo    3. ユーザー環境変数に ANTHROPIC_API_KEY を追加
) else (
    echo ^>^> ANTHROPIC_API_KEY が設定されています。
)

echo.
echo === セットアップ完了 ===
echo.
echo 起動方法:
echo   python main.py
echo.
echo 注意: 初回起動時に Windows セキュリティの確認が表示される場合があります。
pause
