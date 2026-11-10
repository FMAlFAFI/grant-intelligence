"""Language tag for one text field: Arabic, English, mixed or empty (brief, Stage 1)."""
import re

ARABIC = re.compile(r"[؀-ۿ]")
LATIN = re.compile(r"[A-Za-z]")
AR, EN, MIXED, NONE = "ar", "en", "mixed", "none"
MIXED_SHARE = 0.2  # the smaller script needs at least this share of the letters to call the field mixed


def tag(text):
    """Return 'ar', 'en', 'mixed' or 'none' for a text field, from the share of Arabic and Latin letters."""
    arabic, latin = len(ARABIC.findall(text or "")), len(LATIN.findall(text or ""))
    letters = arabic + latin
    if letters == 0:
        return NONE
    if min(arabic, latin) / letters >= MIXED_SHARE:
        return MIXED
    return AR if arabic > latin else EN
