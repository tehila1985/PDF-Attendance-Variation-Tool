from __future__ import annotations

import re

from bidi.algorithm import get_display


HEBREW_PATTERN = re.compile(r"[\u0590-\u05FF]")


def rtl(text: str) -> str:
    if not text:
        return ""
    if not HEBREW_PATTERN.search(text):
        return text
    return get_display(text)