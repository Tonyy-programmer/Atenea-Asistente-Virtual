import os
import pyautogui
import pygetwindow as gw
import pyperclip
import subprocess
import webbrowser
from difflib import get_close_matches
from pathlib import Path
from urllib.parse import quote_plus


def normalize_text(text: str) -> str:
    return " ".join(text.lower().strip().split())


class SystemActions:
    def __init__(self) -> None:
        self.apps = {
            "bloc de notas": "notepad.exe",
            "notepad": "notepad.exe",
            "calculadora": "calc.exe",
            "paint": "mspaint.exe",
            "explorador": "explorer.exe",
            "wordpad": "write.exe",
            "terminal": "wt.exe",
            "cmd": "cmd.exe",
        }
        self.websites = {
            "google": "https://www.google.com",
            "youtube": "https://www.youtube.com",
            "gmail": "https://mail.google.com",
            "facebook": "https://www.facebook.com",
            "instagram": "https://www.instagram.com",
            "whatsapp": "https://web.whatsapp.com",
            "github": "https://github.com",
        }
        self.folders = {
            "documentos": Path.home() / "Documents",
            "descargas": Path.home() / "Downloads",
            "escritorio": Path.home() / "Desktop",
            "imagenes": Path.home() / "Pictures",
            "musica": Path.home() / "Music",
            "videos": Path.home() / "Videos",
        }
        self.installed_apps = self._load_installed_apps()

    def open_app(self, app_name: str) -> bool:
        executable = self.apps.get(app_name)

        if not executable:
            return False

        subprocess.Popen([executable], shell=False)
        return True

    def open_website(self, website_name: str) -> bool:
        url = self.websites.get(website_name)

        if not url:
            return False

        webbrowser.open(url)
        return True

    def open_folder(self, folder_name: str) -> bool:
        folder = self.folders.get(folder_name)

        if not folder or not folder.exists():
            return False

        os.startfile(folder)
        return True

    def search_google(self, query: str) -> bool:
        cleaned_query = query.strip()

        if not cleaned_query:
            return False

        webbrowser.open(f"https://www.google.com/search?q={quote_plus(cleaned_query)}")
        return True

    def type_text(self, text: str) -> bool:
        cleaned_text = text.strip()

        if not cleaned_text:
            return False

        pyperclip.copy(cleaned_text)
        pyautogui.hotkey("ctrl", "v")
        return True

    def press_key(self, key: str) -> bool:
        pyautogui.press(key)
        return True

    def hotkey(self, keys: tuple[str, ...]) -> bool:
        pyautogui.hotkey(*keys)
        return True

    def click_current_position(self) -> bool:
        pyautogui.click()
        return True

    def get_active_window_title(self) -> str:
        window = gw.getActiveWindow()

        if not window:
            return ""

        return window.title or ""

    def open_installed_app(self, app_name: str) -> bool:
        cleaned_name = normalize_text(app_name)

        if not cleaned_name:
            return False

        exact_match = self.installed_apps.get(cleaned_name)
        if exact_match:
            os.startfile(exact_match)
            return True

        close_matches = get_close_matches(
            cleaned_name,
            self.installed_apps.keys(),
            n=1,
            cutoff=0.72,
        )

        if not close_matches:
            return False

        os.startfile(self.installed_apps[close_matches[0]])
        return True

    def find_app_mentioned_in_text(self, text: str) -> str:
        cleaned_text = normalize_text(text)

        if not cleaned_text:
            return ""

        for app_name in sorted(self.installed_apps.keys(), key=len, reverse=True):
            if app_name in cleaned_text:
                return app_name

        return ""

    def _load_installed_apps(self) -> dict[str, Path]:
        apps: dict[str, Path] = {}
        start_menu_paths = (
            Path(os.environ.get("ProgramData", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("AppData", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path.home() / "Desktop",
        )

        for base_path in start_menu_paths:
            if not base_path.exists():
                continue

            for shortcut in base_path.rglob("*.lnk"):
                app_name = normalize_text(shortcut.stem)
                apps.setdefault(app_name, shortcut)

        return apps
