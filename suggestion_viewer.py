"""
提案表示ウィンドウ（単独プロセスとして起動される）。
引数にテキストファイルのパスを受け取り、内容を表示する。
"""
import sys
import tkinter as tk
from tkinter import scrolledtext


def show(text: str):
    root = tk.Tk()
    root.title("AI省力化提案")
    root.geometry("680x520")
    root.configure(bg="#1e1e2e")
    root.attributes("-topmost", True)
    root.resizable(True, True)

    # ヘッダー
    header = tk.Label(
        root,
        text="AI省力化提案",
        font=("Helvetica", 17, "bold"),
        bg="#1e1e2e",
        fg="#cdd6f4",
        pady=12,
    )
    header.pack()

    # テキストエリア
    text_area = scrolledtext.ScrolledText(
        root,
        wrap=tk.WORD,
        font=("Helvetica", 13),
        bg="#313244",
        fg="#cdd6f4",
        insertbackground="white",
        padx=14,
        pady=12,
        relief=tk.FLAT,
        borderwidth=0,
    )
    text_area.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))
    text_area.insert(tk.END, text)
    text_area.config(state=tk.DISABLED)

    # 閉じるボタン
    btn = tk.Button(
        root,
        text="閉じる",
        command=root.destroy,
        bg="#89b4fa",
        fg="#1e1e2e",
        font=("Helvetica", 12, "bold"),
        relief=tk.FLAT,
        padx=24,
        pady=6,
        cursor="hand2",
        activebackground="#74c7ec",
        activeforeground="#1e1e2e",
    )
    btn.pack(pady=(0, 14))

    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python suggestion_viewer.py <text_file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        content = f"ファイルの読み込みに失敗しました: {e}"

    show(content)
