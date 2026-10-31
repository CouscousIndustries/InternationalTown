"""
InternationalTown — local translation companion for the Motor Town mod.

Reads the requests dropped by the mod in ../bridge/in/*.req,
detects the language (Lingua), translates into the player's language (NLLB-200, open source),
and writes the answer to ../bridge/out/<id>.res.

Settings: settings.json (written by install.bat) — detected languages, model, threads.

Usage:
    python translator.py                 # settings from settings.json
    python translator.py --dry-run       # no model, returns the text as is (bridge test)
"""

import argparse
import json
import logging
import os
import re
import time
from functools import lru_cache
from pathlib import Path

from lingua import Language, LanguageDetectorBuilder

from langmap import NLLB_CODES, SPECIAL_TARGETS
import i18n

HERE = Path(__file__).resolve().parent
SETTINGS_PATH = HERE / "settings.json"


def load_settings():
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

log = logging.getLogger("InternationalTown")


# ---------------------------------------------------------------------------
# Escaping (same convention as main.lua)
# ---------------------------------------------------------------------------
def unesc(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            out.append({"t": "\t", "n": "\n", "\\": "\\"}.get(nxt, nxt))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\r", "").replace("\n", "\\n")


# ---------------------------------------------------------------------------
# Languages
# ---------------------------------------------------------------------------
ALL_LANGS = [getattr(Language, name) for name in NLLB_CODES]
LANG_BY_ISO1 = {lang.iso_code_639_1.name.lower(): lang for lang in ALL_LANGS}


def target_to_nllb(culture: str):
    """'fr', 'fr-FR', 'zh-Hant', 'pt-BR' -> (NLLB code, short code) or (None, None)."""
    c = culture.strip().lower().replace("_", "-")
    if c in SPECIAL_TARGETS:
        return SPECIAL_TARGETS[c], c.split("-")[0]
    base = c.split("-")[0]
    lang = LANG_BY_ISO1.get(base)
    if lang is None:
        return None, None
    return NLLB_CODES[lang.name], base


class Detector:
    """With 75 languages, Lingua's confidence is spread over all of them: on a short sentence,
    the best language may score only 0.2 and still be right. So we judge the gap to the
    2nd language (minimum relative distance) rather than an absolute threshold."""

    # One or two words ("salut", "hello there"): detection is unreliable,
    # so a much clearer gap between the 1st and 2nd language is required.
    SHORT_WORDS = 2

    def __init__(self, languages, min_distance: float, short_distance: float):
        self.min_distance = min_distance
        self.short_distance = max(min_distance, short_distance)
        self.languages = list(dict.fromkeys(languages))
        self._build()

    def _build(self):
        # Lingua needs at least 2 languages
        langs = self.languages if len(self.languages) >= 2 else self.languages + [Language.ENGLISH, Language.FRENCH]
        langs = list(dict.fromkeys(langs))
        self.detector = (LanguageDetectorBuilder.from_languages(*langs)
                         .with_minimum_relative_distance(self.min_distance)
                         .build())
        self.short_detector = (LanguageDetectorBuilder.from_languages(*langs)
                               .with_minimum_relative_distance(self.short_distance)
                               .build())

    def ensure(self, lang):
        """The player's language must be detectable, otherwise their own messages would be "translated"."""
        if lang is not None and lang not in self.languages:
            log.info("adding %s to the detected languages (game language)", lang.name.title())
            self.languages.append(lang)
            self._build()

    def detect(self, text: str):
        """Returns (Language, confidence) or (None, 0)."""
        short = len(text.split()) <= self.SHORT_WORDS
        lang = (self.short_detector if short else self.detector).detect_language_of(text)
        if lang is None:
            return None, 0.0
        return lang, self.detector.compute_language_confidence(text, lang)


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------
class Ct2Translator:
    """NLLB-200 quantized to int8 with CTranslate2: ~600 MB of RAM, 2-3x faster on CPU."""

    def __init__(self, model_dir: Path, threads: int, beams: int):
        import ctranslate2
        from transformers import AutoTokenizer

        log.info("loading the int8 model (%s)", model_dir.name)
        self.model = ctranslate2.Translator(str(model_dir), device="cpu", compute_type="int8",
                                            inter_threads=1, intra_threads=threads)
        self.tok = AutoTokenizer.from_pretrained(str(model_dir))
        self.beams = beams
        log.info("model ready")

    @lru_cache(maxsize=2048)
    def translate(self, text: str, src: str, tgt: str) -> str:
        self.tok.src_lang = src
        ids = self.tok(text, truncation=True, max_length=256)["input_ids"]
        source = self.tok.convert_ids_to_tokens(ids)
        res = self.model.translate_batch([source], target_prefix=[[tgt]], beam_size=self.beams,
                                         max_decoding_length=256)
        tokens = res[0].hypotheses[0]
        if tokens and tokens[0] == tgt:
            tokens = tokens[1:]
        return self.tok.decode(self.tok.convert_tokens_to_ids(tokens), skip_special_tokens=True)


class NllbTranslator:
    """Old engine (PyTorch, ~2.5 GB of RAM): used only if the int8 model is missing."""

    def __init__(self, model_name: str, device: str, threads: int, beams: int):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        torch.set_num_threads(threads)  # limits the CPU impact on the game
        log.info("loading %s on %s (first start: ~2.5 GB download)", model_name, device)
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(device).eval()
        self.model.generation_config.max_length = None  # avoids the max_length/max_new_tokens warning
        self.device = device
        self.beams = beams
        log.info("model ready")

    @lru_cache(maxsize=2048)
    def translate(self, text: str, src: str, tgt: str) -> str:
        self.tok.src_lang = src
        inputs = self.tok(text, return_tensors="pt", truncation=True, max_length=256).to(self.device)
        with self.torch.inference_mode():
            out = self.model.generate(
                **inputs,
                forced_bos_token_id=self.tok.convert_tokens_to_ids(tgt),
                num_beams=self.beams,
                max_new_tokens=256,
            )
        return self.tok.batch_decode(out, skip_special_tokens=True)[0]


class DryRunTranslator:
    def translate(self, text: str, src: str, tgt: str) -> str:
        return f"<{src}->{tgt}> {text}"


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def write_result(out_dir: Path, req_id: str, src: str, text: str):
    tmp = out_dir / f"{req_id}.tmp"
    tmp.write_text(f"{src}\t{esc(text)}", encoding="utf-8")
    os.replace(tmp, out_dir / f"{req_id}.res")


# ---------------------------------------------------------------------------
# Player names and emojis: never translated, and excluded from language detection
# ---------------------------------------------------------------------------
EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"   # emojis, pictographs, flags
    "☀-➿"           # miscellaneous symbols, dingbats (☀ ✔ ❤…)
    "⬀-⯿"           # arrows, stars
    "️‍⃣"      # emoji selectors / joiners
    "]+"
)
EMOTICON_RE = re.compile(
    r"(?<!\w)(?:"
    r"[:;=8][\-o\*'^]?[\)\]\(\[dDpP/\\|oO3\*\$@]+"   # :) ;-) :D :P :/ :o
    r"|[\)\(][\-o]?[:;=]"                           # (: ):
    r"|\^+[_\-\.]*\^+"                              # ^^ ^_^ ^-^
    r"|[xX]+[dD]+"                                  # xD XDD
    r"|<3+|</3"                                     # <3
    r"|[oO0][/\\]|[/\\][oO0]"                       # o/ \o
    r"|[-_^°oO0TtUu>][_\.]+[-_^°oO0TtUu<]"          # -_- T_T u_u o.O >_<
    r"|:[a-z0-9_+\-]+:"                             # :smile: (Discord codes)
    r")(?!\w)"
)


def protected_spans(text: str, names):
    """(start, end) positions of player names, emojis and emoticons in the text."""
    spans = [m.span() for m in EMOJI_RE.finditer(text)]
    spans += [m.span() for m in EMOTICON_RE.finditer(text)]
    for name in sorted(set(names), key=len, reverse=True):
        if len(name) < 2:
            continue
        for m in re.finditer(r"(?<!\w)@?" + re.escape(name) + r"(?!\w)", text, re.IGNORECASE):
            spans.append(m.span())
    return sorted(spans)


def strip_spans(text: str, spans) -> str:
    out, last = [], 0
    for a, b in spans:
        if a < last:
            continue
        out.append(text[last:a])
        out.append(" ")
        last = b
    out.append(text[last:])
    return re.sub(r"\s+", " ", "".join(out)).strip()


def split_symbols(text: str):
    """Separates emojis/emoticons from the text: (text without symbols, leading symbols, trailing symbols)."""
    syms = [m.span() for m in EMOJI_RE.finditer(text)] + [m.span() for m in EMOTICON_RE.finditer(text)]
    syms.sort()
    if not syms:
        return text, "", ""
    lead, tail, body, last = [], [], [], 0
    for a, b in syms:
        if a < last:
            continue
        before = text[last:a]
        (lead if not "".join(body).strip() and not before.strip() else tail).append(text[a:b])
        body.append(before)
        last = b
    body.append(text[last:])
    return re.sub(r"\s+", " ", " ".join(body)).strip(), " ".join(lead), " ".join(tail)


def handle(req_path: Path, out_dir: Path, detector: Detector, translator):
    raw = req_path.read_text(encoding="utf-8", errors="replace")
    req_path.unlink(missing_ok=True)
    parts = raw.split("\t", 5)
    if len(parts) < 4:
        log.warning("unreadable request: %r", raw[:80])
        return
    req_id, culture, sender, text = parts[0], parts[1], unesc(parts[2]), unesc(parts[3])
    names = [n for n in unesc(parts[4]).split("\x1f") if n] if len(parts) > 4 else []
    # 6th field (messages YOU send): your language, used if detection hesitates
    source_hint = parts[5].strip() if len(parts) > 5 else ""
    if sender:
        names.append(sender)

    # What remains once player names and emojis are removed: used for detection
    spans = protected_spans(text, names)
    core = strip_spans(text, spans)
    if sum(ch.isalpha() for ch in core) < 3:
        log.info("skipped (nothing to translate besides names/emojis): %s", text)
        write_result(out_dir, req_id, "skip", "")
        return

    tgt, tgt_short = target_to_nllb(culture)
    if tgt is None:
        log.warning("unknown player language: %s", culture)
        write_result(out_dir, req_id, "skip", "")
        return

    detector.ensure(LANG_BY_ISO1.get(tgt_short))
    lang, conf = detector.detect(core)
    if lang is None and source_hint:
        _, hint_short = target_to_nllb(source_hint)
        lang = LANG_BY_ISO1.get(hint_short or "")
        if lang is not None:
            log.info("uncertain language: assuming %s (your language)", hint_short)
    if lang is None:
        log.info("skipped (language too ambiguous): %s", text)
        write_result(out_dir, req_id, "skip", "")
        return

    src = NLLB_CODES[lang.name]
    src_short = lang.iso_code_639_1.name.lower()
    if src_short == tgt_short:
        log.info("already in %s: %s", tgt_short, text)
        write_result(out_dir, req_id, "skip", "")
        return

    t0 = time.perf_counter()
    body, lead, tail = split_symbols(text)
    result = translator.translate(body, src, tgt) if body else ""
    # the model may mangle a player name: the original spelling is restored
    for name in names:
        if len(name) >= 2:
            result = re.sub(r"(?<!\w)" + re.escape(name) + r"(?!\w)", name, result, flags=re.IGNORECASE)
    result = " ".join(p for p in (lead, result, tail) if p)
    log.info("%s→%s (%.2f, %.0f ms) %s: %s  =>  %s",
             src_short, tgt_short, conf, (time.perf_counter() - t0) * 1000, sender, text, result)
    write_result(out_dir, req_id, src_short, result)


def main():
    here = HERE
    st = load_settings()
    ap = argparse.ArgumentParser(description="InternationalTown translation companion")
    ap.add_argument("--bridge", type=Path, default=here.parent / "bridge")
    ap.add_argument("--model-dir", type=Path, default=here / st.get("model_dir", "models/nllb-600m-int8"),
                    help="int8 model (CTranslate2) created by install.bat")
    ap.add_argument("--model", default="facebook/nllb-200-distilled-600M",
                    help="fallback PyTorch model if the int8 model is missing")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--threads", type=int, default=st.get("threads", 2))
    ap.add_argument("--beams", type=int, default=st.get("beams", 2))
    ap.add_argument("--min-distance", type=float, default=0.07,
                    help="minimum gap between the 1st and 2nd detected language (0 = always guess)")
    ap.add_argument("--short-distance", type=float, default=0.15,
                    help="gap required for one- or two-word messages")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--once", action="store_true", help="handles the pending requests then exits (tests)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    # "Below normal" priority: when the game needs the CPU, Windows serves it first.
    # The translator then takes a few tenths of a second longer, but the game no longer stutters.
    if os.name == "nt":
        try:
            import ctypes
            BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
            k32 = ctypes.windll.kernel32
            k32.SetPriorityClass(k32.GetCurrentProcess(), BELOW_NORMAL_PRIORITY_CLASS)
        except Exception:
            pass
    in_dir, out_dir = args.bridge / "in", args.bridge / "out"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.once:
        # Keeps recent requests (arrived while the model was loading),
        # deletes only those the mod has necessarily given up on.
        now = time.time()
        for p in list(in_dir.glob("*.req")) + list(in_dir.glob("*.tmp")) + list(out_dir.glob("*.res")):
            try:
                if now - p.stat().st_mtime > 120:
                    p.unlink(missing_ok=True)
            except OSError:
                pass

    i18n.set_language(st.get("ui_language", "en"))
    print("\n  " + i18n.t("tr_loading") + "\n", flush=True)

    names = [n for n in st.get("languages", []) if n in NLLB_CODES] or list(NLLB_CODES)
    languages = [getattr(Language, n) for n in names]
    log.info("language detector (%d languages)…", len(languages))
    detector = Detector(languages, args.min_distance, args.short_distance)

    if args.dry_run:
        translator = DryRunTranslator()
    elif (args.model_dir / "model.bin").exists():
        translator = Ct2Translator(args.model_dir, args.threads, args.beams)
    else:
        log.warning("int8 model not found (%s): run install.bat to install it. "
                    "Meanwhile, using the old PyTorch engine (~2.5 GB of RAM).", args.model_dir)
        translator = NllbTranslator(args.model, args.device, args.threads, args.beams)
    # Warm-up: Lingua loads its language data on the first call (~5 s),
    # better do it now than on the first real chat message.
    log.info("warming up…")
    t0 = time.perf_counter()
    detector.detect("hello everyone, how are you doing today")
    detector.detect("salut")
    if not args.dry_run:
        translator.translate("Hello everyone, see you on the road.", "eng_Latn", "fra_Latn")
    log.info("ready in %.1f s", time.perf_counter() - t0)

    log.info("listening on %s (Ctrl+C to quit)", args.bridge)
    print("\n" + "=" * 64 + "\n  " + i18n.t("tr_ready") + "\n" + "=" * 64 + "\n", flush=True)

    while True:
        reqs = sorted(in_dir.glob("*.req"), key=lambda p: p.stat().st_mtime)
        for req in reqs:
            try:
                handle(req, out_dir, detector, translator)
            except Exception:
                log.exception("error on %s", req.name)
        if args.once:
            return
        if not reqs:
            time.sleep(0.1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
