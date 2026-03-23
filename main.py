import platform

if platform.system() == "Windows":
    from tray_app_win import WinTrayApp
    WinTrayApp().run()
else:
    from menubar_app import AISupportApp
    AISupportApp().run()
