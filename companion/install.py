"""
InternationalTown — installer of the translation companion.

Run by install.bat (inside the companion's Python environment):
  1. language choice: quick (15 common ones), custom, or all;
  2. dependency installation;
  3. download of NLLB-200 and conversion to int8 (only once);
  4. cleanup (temporary files, PyTorch) and writing of settings.json.

Running install.bat again lets you change languages without downloading the model again.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from langmap import ENDONYMS, LINGUA_MB_PER_LANG, NLLB_CODES, QUICK_LANGS
import i18n
from i18n import t

HERE = Path(__file__).resolve().parent
SETTINGS = HERE / "settings.json"
MODEL_NAME = "facebook/nllb-200-distilled-600M"
MODEL_DIR = HERE / "models" / "nllb-600m-int8"
DOWNLOAD_DIR = HERE / "_download"

RUNTIME_DEPS = ["ctranslate2>=4.0", "transformers>=4.40,<5", "sentencepiece", "lingua-language-detector>=2.0"]
TORCH_INDEX = "https://download.pytorch.org/whl/cpu"

MODEL_RAM_MB = 650     # NLLB-600M in int8
BASE_RAM_MB = 150      # Python, tokenizer, misc.
MODEL_DISK_MB = 620


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
def title(text):
    print()
    print("=" * 64)
    print("  " + text)
    print("=" * 64)


def ask(prompt, default=""):
    try:
        ans = input(prompt).strip()
    except EOFError:
        ans = ""
    return ans or default


def ram_estimate(n_langs):
    return MODEL_RAM_MB + BASE_RAM_MB + n_langs * LINGUA_MB_PER_LANG


def fmt_mb(mb):
    gb, mbu = i18n.units()
    return f"{mb / 1024:.1f} {gb}" if mb >= 1024 else f"{mb:.0f} {mbu}"


def all_langs_sorted():
    return sorted(NLLB_CODES, key=lambda n: ENDONYMS.get(n, n).lower())


# ---------------------------------------------------------------------------
# Language choice
# ---------------------------------------------------------------------------
def print_lang_table(langs, selected):
    cols = 3
    rows = (len(langs) + cols - 1) // cols
    for r in range(rows):
        line = ""
        for c in range(cols):
            i = c * rows + r
            if i < len(langs):
                name = langs[i]
                mark = "x" if name in selected else " "
                line += f"[{mark}] {i + 1:>2}. {ENDONYMS.get(name, name):<20}"
        print("  " + line)


def custom_choice(current):
    langs = all_langs_sorted()
    selected = set(current or QUICK_LANGS)
    while True:
        title(t("py_custom_title", len(selected), fmt_mb(ram_estimate(len(selected)))))
        print_lang_table(langs, selected)
        print()
        print("  " + t("py_custom_help1"))
        print("    " + t("py_custom_help2"))
        ans = ask("  > ").lower()
        if ans in ("ok", "o"):
            if len(selected) < 2:
                print("  " + t("py_custom_min2"))
                continue
            return [n for n in langs if n in selected]
        if ans == "r":
            selected = set(QUICK_LANGS)
        elif ans == "v":
            selected = set()
        elif ans == "t":
            selected = set(langs)
        else:
            for tok in ans.replace(",", " ").split():
                if tok.isdigit() and 1 <= int(tok) <= len(langs):
                    name = langs[int(tok) - 1]
                    selected.symmetric_difference_update({name})


def choose_languages(current):
    title(t("py_title"))
    print("  " + t("py_intro1"))
    print("  " + t("py_intro2"))
    print("  " + t("py_intro3"))
    print()
    quick = ", ".join(ENDONYMS[n] for n in QUICK_LANGS)
    print("  " + t("py_opt1", fmt_mb(ram_estimate(len(QUICK_LANGS)))))
    print(f"     {quick}")
    print("  " + t("py_opt2"))
    print("  " + t("py_opt3", len(NLLB_CODES), fmt_mb(ram_estimate(len(NLLB_CODES)))))
    if current:
        print("  " + t("py_opt4", len(current)))
    while True:
        ans = ask("\n  " + t("py_choice"), "1")
        if ans == "1":
            return list(QUICK_LANGS)
        if ans == "2":
            return custom_choice(current)
        if ans == "3":
            return all_langs_sorted()
        if ans == "4" and current:
            return current


# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------
def pip(*args):
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", *args]
    print("  > pip install " + " ".join(args))
    if subprocess.call(cmd) != 0:
        raise SystemExit("\n  " + t("py_err_deps"))


def has_module(name):
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def convert_model():
    title(t("py_t_model"))
    print("  " + t("py_model1"))
    print("  " + t("py_model2"))
    print()

    torch_installed_here = False
    if not has_module("torch"):
        print("  " + t("py_torch_needed"))
        pip("torch", "--index-url", TORCH_INDEX)
        torch_installed_here = True

    # Download into a temporary folder, not into the user's global cache
    os.environ["HF_HOME"] = str(DOWNLOAD_DIR)
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    from ctranslate2.converters import TransformersConverter
    from transformers import AutoTokenizer

    tmp_out = MODEL_DIR.with_name(MODEL_DIR.name + "_tmp")
    shutil.rmtree(tmp_out, ignore_errors=True)
    tmp_out.parent.mkdir(parents=True, exist_ok=True)

    print("  " + t("py_converting"))
    TransformersConverter(MODEL_NAME).convert(str(tmp_out), quantization="int8", force=True)
    AutoTokenizer.from_pretrained(MODEL_NAME).save_pretrained(str(tmp_out))

    shutil.rmtree(MODEL_DIR, ignore_errors=True)
    tmp_out.rename(MODEL_DIR)
    shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)
    print("  " + t("py_model_ready", MODEL_DIR.relative_to(HERE)))
    return torch_installed_here


def remove_torch():
    print()
    print("  " + t("py_torch_remove"))
    subprocess.call([sys.executable, "-m", "pip", "uninstall", "-y", "torch"])


def dir_size_mb(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total / (1024 * 1024)


def default_threads():
    cpu = os.cpu_count() or 4
    # 1 thread on 4 cores, 2 on 8, 3 on 12, 4 max: leaves room for the game
    return max(1, min(4, cpu // 4))


def main():
    current, old = [], {}
    if SETTINGS.exists():
        try:
            old = json.loads(SETTINGS.read_text(encoding="utf-8"))
            current = old.get("languages", [])
        except ValueError:
            current = []

    # Installer language: the one chosen in INSTALLER.bat (IT_LANG), otherwise the previous one, otherwise ask
    ui = i18n.startup_language(SETTINGS) or i18n.choose_language_interactively()
    i18n.set_language(ui)

    languages = choose_languages(current)
    # your own language is always detected
    mine = {"fr": "FRENCH", "en": "ENGLISH", "ru": "RUSSIAN", "de": "GERMAN", "es": "SPANISH", "pt": "PORTUGUESE",
            "it": "ITALIAN", "pl": "POLISH", "nl": "DUTCH", "tr": "TURKISH", "uk": "UKRAINIAN", "cs": "CZECH",
            "ja": "JAPANESE", "ko": "KOREAN", "zh": "CHINESE"}.get(i18n.language())
    if mine and mine not in languages:
        languages.append(mine)

    title(t("py_t_deps"))
    pip(*RUNTIME_DEPS)

    model_ok = (MODEL_DIR / "model.bin").exists()
    if model_ok:
        print("\n  " + t("py_model_present"))
        if ask("  " + t("py_ask_redownload"), "n").lower()[:1] in ("o", "y", "j", "s", "t", "a", "e", "д", "т"):
            model_ok = False
    if not model_ok:
        convert_model()

    # PyTorch is no longer needed once the model is converted
    if has_module("torch"):
        remove_torch()

    threads = default_threads()
    SETTINGS.write_text(json.dumps({
        "languages": languages,
        "model_dir": str(MODEL_DIR.relative_to(HERE)).replace("\\", "/"),
        "threads": threads,
        "beams": 2,
        "ui_language": i18n.language(),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    venv = HERE / ".venv"
    disk = dir_size_mb(MODEL_DIR) + (dir_size_mb(venv) if venv.exists() else 0)
    title(t("py_t_done"))
    print("  " + t("py_d_langs", len(languages)))
    print("  " + t("py_d_ram", fmt_mb(ram_estimate(len(languages)))))
    print("  " + t("py_d_disk", fmt_mb(disk)))
    print("  " + t("py_d_threads", threads))
    print()
    print("  " + t("py_d_start"))
    print("  " + t("py_d_relaunch"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  " + t("py_cancelled"))
        sys.exit(1)
