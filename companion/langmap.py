"""Mapping between the languages detected by Lingua and the NLLB-200 (FLORES-200) codes."""

# Lingua language name -> NLLB code
NLLB_CODES = {
    "AFRIKAANS": "afr_Latn", "ALBANIAN": "als_Latn", "ARABIC": "arb_Arab",
    "ARMENIAN": "hye_Armn", "AZERBAIJANI": "azj_Latn", "BASQUE": "eus_Latn",
    "BELARUSIAN": "bel_Cyrl", "BENGALI": "ben_Beng", "BOKMAL": "nob_Latn",
    "BOSNIAN": "bos_Latn", "BULGARIAN": "bul_Cyrl", "CATALAN": "cat_Latn",
    "CHINESE": "zho_Hans", "CROATIAN": "hrv_Latn", "CZECH": "ces_Latn",
    "DANISH": "dan_Latn", "DUTCH": "nld_Latn", "ENGLISH": "eng_Latn",
    "ESPERANTO": "epo_Latn", "ESTONIAN": "est_Latn", "FINNISH": "fin_Latn",
    "FRENCH": "fra_Latn", "GANDA": "lug_Latn", "GEORGIAN": "kat_Geor",
    "GERMAN": "deu_Latn", "GREEK": "ell_Grek", "GUJARATI": "guj_Gujr",
    "HEBREW": "heb_Hebr", "HINDI": "hin_Deva", "HUNGARIAN": "hun_Latn",
    "ICELANDIC": "isl_Latn", "INDONESIAN": "ind_Latn", "IRISH": "gle_Latn",
    "ITALIAN": "ita_Latn", "JAPANESE": "jpn_Jpan", "KAZAKH": "kaz_Cyrl",
    "KOREAN": "kor_Hang", "LATVIAN": "lvs_Latn", "LITHUANIAN": "lit_Latn",
    "MACEDONIAN": "mkd_Cyrl", "MALAY": "zsm_Latn", "MAORI": "mri_Latn",
    "MARATHI": "mar_Deva", "MONGOLIAN": "khk_Cyrl", "NYNORSK": "nno_Latn",
    "PERSIAN": "pes_Arab", "POLISH": "pol_Latn", "PORTUGUESE": "por_Latn",
    "PUNJABI": "pan_Guru", "ROMANIAN": "ron_Latn", "RUSSIAN": "rus_Cyrl",
    "SERBIAN": "srp_Cyrl", "SHONA": "sna_Latn", "SLOVAK": "slk_Latn",
    "SLOVENE": "slv_Latn", "SOMALI": "som_Latn", "SOTHO": "sot_Latn",
    "SPANISH": "spa_Latn", "SWAHILI": "swh_Latn", "SWEDISH": "swe_Latn",
    "TAGALOG": "tgl_Latn", "TAMIL": "tam_Taml", "TELUGU": "tel_Telu",
    "THAI": "tha_Thai", "TSONGA": "tso_Latn", "TSWANA": "tsn_Latn",
    "TURKISH": "tur_Latn", "UKRAINIAN": "ukr_Cyrl", "URDU": "urd_Arab",
    "VIETNAMESE": "vie_Latn", "WELSH": "cym_Latn", "XHOSA": "xho_Latn",
    "YORUBA": "yor_Latn", "ZULU": "zul_Latn",
}

# Quick installation: the most common languages on Motor Town servers
QUICK_LANGS = [
    "ENGLISH", "FRENCH", "GERMAN", "SPANISH", "PORTUGUESE", "ITALIAN", "RUSSIAN", "POLISH",
    "DUTCH", "TURKISH", "UKRAINIAN", "CZECH", "JAPANESE", "KOREAN", "CHINESE",
]

# Name shown in the installer (French)
DISPLAY_NAMES = {
    "AFRIKAANS": "Afrikaans", "ALBANIAN": "Albanais", "ARABIC": "Arabe", "ARMENIAN": "Arménien",
    "AZERBAIJANI": "Azéri", "BASQUE": "Basque", "BELARUSIAN": "Biélorusse", "BENGALI": "Bengali",
    "BOKMAL": "Norvégien (bokmål)", "BOSNIAN": "Bosnien", "BULGARIAN": "Bulgare", "CATALAN": "Catalan",
    "CHINESE": "Chinois", "CROATIAN": "Croate", "CZECH": "Tchèque", "DANISH": "Danois",
    "DUTCH": "Néerlandais", "ENGLISH": "Anglais", "ESPERANTO": "Espéranto", "ESTONIAN": "Estonien",
    "FINNISH": "Finnois", "FRENCH": "Français", "GANDA": "Luganda", "GEORGIAN": "Géorgien",
    "GERMAN": "Allemand", "GREEK": "Grec", "GUJARATI": "Gujarati", "HEBREW": "Hébreu",
    "HINDI": "Hindi", "HUNGARIAN": "Hongrois", "ICELANDIC": "Islandais", "INDONESIAN": "Indonésien",
    "IRISH": "Irlandais", "ITALIAN": "Italien", "JAPANESE": "Japonais", "KAZAKH": "Kazakh",
    "KOREAN": "Coréen", "LATVIAN": "Letton", "LITHUANIAN": "Lituanien", "MACEDONIAN": "Macédonien",
    "MALAY": "Malais", "MAORI": "Maori", "MARATHI": "Marathi", "MONGOLIAN": "Mongol",
    "NYNORSK": "Norvégien (nynorsk)", "PERSIAN": "Persan", "POLISH": "Polonais",
    "PORTUGUESE": "Portugais", "PUNJABI": "Pendjabi", "ROMANIAN": "Roumain", "RUSSIAN": "Russe",
    "SERBIAN": "Serbe", "SHONA": "Shona", "SLOVAK": "Slovaque", "SLOVENE": "Slovène",
    "SOMALI": "Somali", "SOTHO": "Sotho", "SPANISH": "Espagnol", "SWAHILI": "Swahili",
    "SWEDISH": "Suédois", "TAGALOG": "Tagalog", "TAMIL": "Tamoul", "TELUGU": "Télougou",
    "THAI": "Thaï", "TSONGA": "Tsonga", "TSWANA": "Tswana", "TURKISH": "Turc",
    "UKRAINIAN": "Ukrainien", "URDU": "Ourdou", "VIETNAMESE": "Vietnamien", "WELSH": "Gallois",
    "XHOSA": "Xhosa", "YORUBA": "Yoruba", "ZULU": "Zoulou",
}

# Name of each language in that language (readable whatever the installer language)
ENDONYMS = {
    "AFRIKAANS": "Afrikaans", "ALBANIAN": "Shqip", "ARABIC": "العربية", "ARMENIAN": "Հայերեն",
    "AZERBAIJANI": "Azərbaycanca", "BASQUE": "Euskara", "BELARUSIAN": "Беларуская", "BENGALI": "বাংলা",
    "BOKMAL": "Norsk bokmål", "BOSNIAN": "Bosanski", "BULGARIAN": "Български", "CATALAN": "Català",
    "CHINESE": "中文", "CROATIAN": "Hrvatski", "CZECH": "Čeština", "DANISH": "Dansk",
    "DUTCH": "Nederlands", "ENGLISH": "English", "ESPERANTO": "Esperanto", "ESTONIAN": "Eesti",
    "FINNISH": "Suomi", "FRENCH": "Français", "GANDA": "Luganda", "GEORGIAN": "ქართული",
    "GERMAN": "Deutsch", "GREEK": "Ελληνικά", "GUJARATI": "ગુજરાતી", "HEBREW": "עברית",
    "HINDI": "हिन्दी", "HUNGARIAN": "Magyar", "ICELANDIC": "Íslenska", "INDONESIAN": "Bahasa Indonesia",
    "IRISH": "Gaeilge", "ITALIAN": "Italiano", "JAPANESE": "日本語", "KAZAKH": "Қазақша",
    "KOREAN": "한국어", "LATVIAN": "Latviešu", "LITHUANIAN": "Lietuvių", "MACEDONIAN": "Македонски",
    "MALAY": "Bahasa Melayu", "MAORI": "Te reo Māori", "MARATHI": "मराठी", "MONGOLIAN": "Монгол",
    "NYNORSK": "Norsk nynorsk", "PERSIAN": "فارسی", "POLISH": "Polski", "PORTUGUESE": "Português",
    "PUNJABI": "ਪੰਜਾਬੀ", "ROMANIAN": "Română", "RUSSIAN": "Русский", "SERBIAN": "Српски",
    "SHONA": "chiShona", "SLOVAK": "Slovenčina", "SLOVENE": "Slovenščina", "SOMALI": "Soomaali",
    "SOTHO": "Sesotho", "SPANISH": "Español", "SWAHILI": "Kiswahili", "SWEDISH": "Svenska",
    "TAGALOG": "Tagalog", "TAMIL": "தமிழ்", "TELUGU": "తెలుగు", "THAI": "ไทย",
    "TSONGA": "Xitsonga", "TSWANA": "Setswana", "TURKISH": "Türkçe", "UKRAINIAN": "Українська",
    "URDU": "اردو", "VIETNAMESE": "Tiếng Việt", "WELSH": "Cymraeg", "XHOSA": "isiXhosa",
    "YORUBA": "Yorùbá", "ZULU": "isiZulu",
}

# Approximate Lingua RAM per loaded language (high accuracy mode), in MB
LINGUA_MB_PER_LANG = 13

# UE culture codes that cannot simply be derived from the ISO 639-1 code
SPECIAL_TARGETS = {
    "zh-hant": "zho_Hant", "zh-tw": "zho_Hant", "zh-hk": "zho_Hant",
    "no": "nob_Latn", "pt-br": "por_Latn",
}
