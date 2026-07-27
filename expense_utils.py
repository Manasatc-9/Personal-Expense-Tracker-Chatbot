from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import dateparser
import difflib
import re


def parse_date(text):
    """
    Convert natural language date expressions into YYYY-MM-DD.

    Examples:
    yesterday morning -> yesterday's date
    this morning -> today's date
    last friday -> previous friday
    """

    if not text:
        return date.today().isoformat()

    clean_text = str(text).lower().strip()

    # Normalize repeated prefixes like "last last monday" -> "last monday"
    clean_text = re.sub(
        r"\b(last|next|this)(?:\s+\1)+\b",
        r"\1",
        clean_text,
    )

    # Normalize time-of-day expressions to the base date
    clean_text = re.sub(
        r"\b(?:this|today)\s+(?:morning|afternoon|evening|night)\b",
        "today",
        clean_text,
    )
    clean_text = re.sub(
        r"\b(yesterday|last|next)\s+(?:morning|afternoon|evening|night)\b",
        r"\1",
        clean_text,
    )

    # Remove remaining time words because we store only date
    for word in [
        "morning",
        "afternoon",
        "evening",
        "night"
    ]:
        clean_text = clean_text.replace(word, "")

    clean_text = clean_text.strip()

    date_phrase = _extract_date_phrase(clean_text)
    parse_target = date_phrase or clean_text

    parsed = dateparser.parse(
        parse_target,
        settings={
            "RELATIVE_BASE": datetime.now(tz=ZoneInfo("Asia/Kolkata")),
            "PREFER_DATES_FROM": "past",
            "TIMEZONE": "Asia/Kolkata",
            "TO_TIMEZONE": "Asia/Kolkata",
            "RETURN_AS_TIMEZONE_AWARE": True,
        },
    )

    if parsed:
        return parsed.date().isoformat()

    fallback_text = date_phrase or clean_text
    fallback = _parse_relative_weekday(fallback_text)
    if fallback:
        return fallback

    return date.today().isoformat()


def _parse_relative_weekday(text):
    if not text:
        return None

    words = text.split()
    if len(words) != 2:
        return None

    prefix, weekday = words
    prefix = prefix.lower()
    weekday = weekday.lower()

    weekday_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    if weekday not in weekday_map:
        close_match = difflib.get_close_matches(weekday, weekday_map.keys(), n=1, cutoff=0.7)
        if close_match:
            weekday = close_match[0]
        else:
            return None

    target_weekday = weekday_map[weekday]
    today = datetime.now().date()
    current_weekday = today.weekday()

    if prefix == "last":
        days_back = (current_weekday - target_weekday) % 7 or 7
        return (today - timedelta(days=days_back)).isoformat()
    if prefix == "this":
        days_forward = (target_weekday - current_weekday) % 7
        return (today + timedelta(days=days_forward)).isoformat()
    if prefix == "next":
        days_forward = (target_weekday - current_weekday) % 7 or 7
        return (today + timedelta(days=days_forward)).isoformat()

    return None


def _extract_date_phrase(text):
    if not text:
        return None

    patterns = [
        r"\b(?:today|yesterday|tomorrow)\b",
        r"\b(?:last|next|this)(?:\s+(?:last|next|this))*\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\b(?:last|next|this)\s+(?:week|month|year)\b",
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)(?:,\s*\d{4})?\b",
        r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*\d{4})?\b",
        r"\b\d+\s+days?\s+ago\b",
        r"\b\d+\s+weeks?\s+ago\b",
        r"\b\d+\s+months?\s+ago\b",
        r"\b\d+\s+years?\s+ago\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)

    return None



def normalize_category(value):
    """
    Convert category output into your fixed categories.
    """

    if not value:
        return "Other"

    normalized = str(value).strip()

    # Accept valid Gemini categories first
    valid_categories = [
        "Dining",
        "Transport",
        "Groceries",
        "Shopping",
        "Utilities",
        "Entertainment",
        "Other"
    ]

    if normalized in valid_categories:
        return normalized

    title_value = normalized.title()
    if title_value in valid_categories:
        return title_value

    return "Other"