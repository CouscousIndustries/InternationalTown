"""Installer and translator texts in the chosen language (i18n.json file)."""

import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
_DATA = json.loads((HERE / "i18n.json").read_text(encoding="utf-8"))
LANGUAGES = [(l["code"], l["name"]) for l in _DATA["languages"]]
CODES = [c for c, _ in LANGUAGES]
_lang = "en"


def set_language(code):
    global _lang
    code = (code or "").lower().split("-")[0]
    _lang = code if code in CODES else "en"
    return _lang


def language():
    return _lang


def t(key, *args):
    entry = _DATA["strings"].get(key, {})
    text = entry.get(_lang) or entry.get("en") or key
    return text.format(*args) if args else text


def units():
    """(GB, MB) in the language: Go/Mo in French, ГБ/МБ in Russian and Ukrainian, GB/MB otherwise."""
    return {"fr": ("Go", "Mo"), "ru": ("ГБ", "МБ"), "uk": ("ГБ", "МБ")}.get(_lang, ("GB", "MB"))


def choose_language_interactively():
    """Language menu (used only if install.bat is run alone, without INSTALLER.bat)."""
    print()
    print("=" * 64)
    print("  Language / Langue / Язык")
    print("=" * 64)
    for i, (code, name) in enumerate(LANGUAGES, 1):
        print(f"  {i:>2}. {name}")
    while True:
        try:
            ans = input("\n  > ").strip()
        except EOFError:
            ans = ""
        if ans.isdigit() and 1 <= int(ans) <= len(LANGUAGES):
            return LANGUAGES[int(ans) - 1][0]
        if ans.lower() in CODES:
            return ans.lower()


def startup_language(settings_path):
    """Interface language: IT_LANG variable (given by INSTALLER.bat), otherwise settings.json."""
    env = os.environ.get("IT_LANG", "").strip()
    if env:
        return env
    try:
        return json.loads(Path(settings_path).read_text(encoding="utf-8")).get("ui_language", "")
    except (OSError, ValueError):
        return ""
