# InternationalTown (mod folder)

This folder is the mod itself. It belongs in
`…\Motor Town\MotorTown\Binaries\Win64\ue4ss\Mods\InternationalTown\`.

For installation and usage, see **README.md** (English) or **LISEZ-MOI.md** (French) in the
`International Town` package — the easiest way is to run `INSTALLER.bat` from the package.

## Contents

| Path | Role |
|---|---|
| `Scripts/main.lua` | UE4SS Lua mod: intercepts incoming chat (`MotorTownPlayerController:ClientChat`), shows translations, F9 translation of the chat input box (F9 outside the chat pauses incoming translations), `!servlang` per-server setting, `!servtrad` key choice |
| `Scripts/config.lua` | Settings (target language, F9 key, welcome message…) |
| `companion/` | Local translator (Python): Lingua language detection + NLLB-200 int8 via CTranslate2 |
| `companion/install.bat` | Installs the translator (choose languages, download and convert the model once) |
| `companion/start.bat` | Starts the translator — run it before playing |
| `companion/i18n.json` | Installer and translator texts in 15 languages |
| `bridge/` | Message exchange between the game and the translator (small files, nothing leaves your PC) |
| `servlang.txt` | Created automatically: server language per server (`!servlang`) |
| `translate_key.txt` | Created automatically: translation key chosen in game (`!servtrad`) |

## How it works

```
Game (Lua mod) ──► bridge/in/*.req ──► translator (Lingua + NLLB) ──► bridge/out/*.res ──► "Name: » [DE] …" in the chat
```

The translator runs at below-normal CPU priority; the mod only touches the game thread when there
is something to do. If something breaks after a game update, press **F8** in game: it logs calls to
the functions listed in `spy_functions` (config.lua) to `ue4ss\UE4SS.log`.
