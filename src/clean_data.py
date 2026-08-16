from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable

ALLOWED_CATEGORIES = {"automation-heavy", "web dev", "data"}

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

CITY_MAP = {
    "gurgaon": "gurugram",
    "gurugram": "gurugram",
    "new delhi": "delhi",
    "delhi ncr": "delhi",
    "bangalore": "bengaluru",
    "bengaluru": "bengaluru",
    "pune": "pune",
    "noida": "noida",
    "delhi": "delhi",
}


def normalize_whitespace(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return re.sub(r"\s+", " ", text)


def normalize_name(value: Any) -> str | None:
    text = normalize_whitespace(value)
    if not text:
        return None

    parts = []
    for token in text.split(" "):
        if len(token) == 2 and token.endswith("."):
            parts.append(token.upper())
        else:
            parts.append(token.capitalize())
    return " ".join(parts)


def normalize_email(value: Any) -> str | None:
    text = normalize_whitespace(value)
    if not text:
        return None
    text = text.lower()
    if not EMAIL_REGEX.match(text):
        return None
    return text


def normalize_phone(value: Any) -> str | None:
    text = normalize_whitespace(value)
    if not text:
        return None

    digits = re.sub(r"\D", "", text)
    if not digits:
        return None

    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    if len(digits) != 10:
        return None

    return digits


def normalize_city(value: Any) -> str | None:
    text = normalize_whitespace(value)
    if not text:
        return None
    key = text.lower()
    return CITY_MAP.get(key, key)


def parse_float(value: Any) -> float | None:
    text = normalize_whitespace(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: Any) -> int | None:
    text = normalize_whitespace(value)
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_date_to_iso(value: Any) -> str | None:
    text = normalize_whitespace(value)
    if not text:
        return None

    formats = [
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d %b %Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%d %B %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_status(value: Any) -> str | None:
    text = normalize_whitespace(value)
    if not text:
        return None
    t = text.lower()
    if t in {"active", "inactive", "paused"}:
        return t
    return None


def normalize_verified(value: Any) -> int | None:
    text = normalize_whitespace(value)
    if not text:
        return None
    t = text.lower()
    if t in {"y", "yes", "true", "1"}:
        return 1
    if t in {"n", "no", "false", "0"}:
        return 0
    return None


def normalize_skill_list(value: Any) -> list[str]:
    text = normalize_whitespace(value)
    if not text:
        return []
    skills = []
    for part in str(text).split(","):
        normalized = normalize_whitespace(part)
        if normalized:
            skills.append(normalized.lower())
    return sorted(set(skills))


def merge_skill_lists(*skill_lists: Iterable[str]) -> list[str]:
    merged: set[str] = set()
    for items in skill_lists:
        merged.update(items)
    return sorted(merged)


def normalize_skill_category(value: Any) -> str | None:
    text = normalize_whitespace(value)
    if not text:
        return None
    normalized = text.lower()
    if normalized in ALLOWED_CATEGORIES:
        return normalized
    return None
