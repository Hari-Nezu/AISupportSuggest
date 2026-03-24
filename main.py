"""AISupportSuggest エントリポイント。"""
import platform

if platform.system() == "Windows":
    from src.ui.tray_app_win import WinTrayApp
    WinTrayApp().run()
else:
    from src.ui.menubar_app import AISupportApp
    AISupportApp().run()
