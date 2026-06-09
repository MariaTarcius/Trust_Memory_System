"""
Deterministic claim analysis used when LLM calls fail or as the primary signal.
Ensures merge, revise, downgrade, reject, and forget decisions are rule-driven.
"""
import re
from typing import Optional

NEGATION_MARKERS = (
    "failed", "no funding", "none", "did not", "never", "not raised",
    "funding attempt failed", "no raise",
)
SUBSET_MARKERS = ("only", "just", "merely")

WORD_RE = re.compile(r"[a-z0-9]+")
YEAR_RE = re.compile(r"\b(20\d{2})\b")
MONEY_RE = re.compile(
    r"(?:(\$|usd\s*)?(\d+(?:\.\d+)?)\s*(million|billion|m|b|k|thousand))|"
    r"((?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion)"
    r"(?:\s+(?:one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|million|billion))*"
    r"\s+(?:dollars?|usd))"
    ,
    re.IGNORECASE,
)

WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
    "million": 1_000_000, "billion": 1_000_000_000,
}


def normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    cleaned = text.lower().strip()
    cleaned = cleaned.replace("—", "-").replace("–", "-")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def token_set(text: str) -> set[str]:
    return set(WORD_RE.findall(normalize_text(text)))


def jaccard_similarity(a: str, b: str) -> float:
    ta, tb = token_set(a), token_set(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _scale_amount(value: float, unit: str) -> float:
    unit = unit.lower()
    if unit in ("k", "thousand"):
        return value * 1_000
    if unit in ("m", "million"):
        return value * 1_000_000
    if unit in ("b", "billion"):
        return value * 1_000_000_000
    return value


def _words_to_number(words: str) -> Optional[float]:
    total = 0
    current = 0
    for word in words.lower().split():
        if word not in WORD_TO_NUM:
            continue
        val = WORD_TO_NUM[word]
        if val == 100:
            current = max(current, 1) * 100
        elif val >= 1000:
            current = max(current, 1) * val
            total += current
            current = 0
        else:
            current += val
    total += current
    return float(total) if total > 0 else None


def extract_amount(text: str) -> Optional[float]:
    text = normalize_text(text)
    for match in MONEY_RE.finditer(text):
        if match.group(2):
            value = float(match.group(2))
            unit = (match.group(3) or "").lower()
            return _scale_amount(value, unit)
        if match.group(4):
            return _words_to_number(match.group(4))
    return None


def extract_year(text: str) -> Optional[str]:
    match = YEAR_RE.search(normalize_text(text))
    return match.group(1) if match else None


def extract_count(text: str) -> Optional[float]:
    amount = extract_amount(text)
    if amount is not None:
        return amount
    match = re.search(r"(\d+(?:\.\d+)?)\s*million", normalize_text(text))
    if match:
        return float(match.group(1)) * 1_000_000
    return None


def is_negation_object(text: str) -> bool:
    norm = normalize_text(text)
    return any(marker in norm for marker in NEGATION_MARKERS)


def objects_are_duplicate(obj1: Optional[str], obj2: Optional[str]) -> bool:
    if not obj1 or not obj2:
        return False

    n1, n2 = normalize_text(obj1), normalize_text(obj2)
    if n1 == n2:
        return True

    if jaccard_similarity(obj1, obj2) >= 0.92:
        return True

    amt1, amt2 = extract_amount(obj1), extract_amount(obj2)
    year1, year2 = extract_year(obj1), extract_year(obj2)
    if amt1 is not None and amt2 is not None:
        same_amount = abs(amt1 - amt2) < 1
        same_year = year1 == year2 or (year1 is None and year2 is None)
        if same_amount and same_year:
            return True

    count1, count2 = extract_count(obj1), extract_count(obj2)
    if count1 is not None and count2 is not None and abs(count1 - count2) < 1:
        if year1 == year2 or year1 is None or year2 is None:
            return True

    return False


def is_subset_conflict(existing: str, incoming: str) -> bool:
    inc = normalize_text(incoming)
    if not any(marker in inc for marker in SUBSET_MARKERS):
        return False
    overlap = jaccard_similarity(existing, incoming)
    return 0.25 <= overlap < 0.85


def is_corroboration(existing: str, incoming: str) -> bool:
    if objects_are_duplicate(existing, incoming):
        return True
    if is_negation_object(existing) or is_negation_object(incoming):
        return False

    ex_amt, in_amt = extract_amount(existing), extract_amount(incoming)
    ex_year, in_year = extract_year(existing), extract_year(incoming)
    if ex_amt is not None and in_amt is not None and abs(ex_amt - in_amt) >= 1:
        return False
    if ex_year and in_year and ex_year != in_year:
        return False

    ex_count, in_count = extract_count(existing), extract_count(incoming)
    if ex_count is not None and in_count is not None and abs(ex_count - in_count) >= 1:
        return False

    ex_tokens = token_set(existing)
    in_tokens = token_set(incoming)
    if not ex_tokens or not in_tokens:
        return False
    if in_tokens.issubset(ex_tokens) or ex_tokens.issubset(in_tokens):
        return True

    overlap = len(ex_tokens & in_tokens) / min(len(ex_tokens), len(in_tokens))
    return overlap >= 0.5


def detect_conflict(existing_object: str, incoming_object: str) -> dict:
    """Return contradiction metadata between two object values."""
    if not existing_object or not incoming_object:
        return {
            "is_contradiction": False,
            "type": "NONE",
            "explanation": "Missing object values.",
        }

    if objects_are_duplicate(existing_object, incoming_object):
        return {
            "is_contradiction": False,
            "type": "NONE",
            "explanation": "Semantically equivalent values.",
        }

    ex_neg = is_negation_object(existing_object)
    in_neg = is_negation_object(incoming_object)
    if ex_neg != in_neg:
        return {
            "is_contradiction": True,
            "type": "NEGATION",
            "explanation": "One value affirms the fact while the other negates it.",
        }

    if is_subset_conflict(existing_object, incoming_object):
        return {
            "is_contradiction": True,
            "type": "SUBSET_CONFLICT",
            "explanation": "Incoming claim is an incomplete or narrowed version of the stored fact.",
        }

    ex_amt, in_amt = extract_amount(existing_object), extract_amount(incoming_object)
    ex_year, in_year = extract_year(existing_object), extract_year(incoming_object)
    if ex_amt is not None and in_amt is not None:
        if abs(ex_amt - in_amt) >= 1:
            conflict_type = "TEMPORAL_UPDATE" if ex_year and in_year and ex_year != in_year else "VALUE_CONFLICT"
            return {
                "is_contradiction": True,
                "type": conflict_type,
                "explanation": f"Conflicting amounts: {existing_object} vs {incoming_object}.",
            }

    ex_count, in_count = extract_count(existing_object), extract_count(incoming_object)
    if ex_count is not None and in_count is not None and abs(ex_count - in_count) >= 1:
        return {
            "is_contradiction": True,
            "type": "TEMPORAL_UPDATE",
            "explanation": f"Numeric value changed over time: {existing_object} vs {incoming_object}.",
        }

    if ex_year and in_year and ex_year != in_year:
        return {
            "is_contradiction": True,
            "type": "TEMPORAL_UPDATE",
            "explanation": f"Conflicting years: {ex_year} vs {in_year}.",
        }

    if is_corroboration(existing_object, incoming_object):
        return {
            "is_contradiction": False,
            "type": "CORROBORATION",
            "explanation": "Compatible corroborating detail.",
        }

    if jaccard_similarity(existing_object, incoming_object) < 0.35:
        return {
            "is_contradiction": True,
            "type": "VALUE_CONFLICT",
            "explanation": f"Distinct incompatible values: {existing_object} vs {incoming_object}.",
        }

    return {
        "is_contradiction": False,
        "type": "NONE",
        "explanation": "No deterministic conflict detected.",
    }


def merge_conflict_with_llm(rule_result: dict, llm_result: dict) -> dict:
    """Prefer deterministic rules; use LLM only when rules are inconclusive."""
    if rule_result.get("is_contradiction"):
        return rule_result
    if llm_result.get("is_contradiction"):
        return llm_result
    if rule_result.get("type") == "CORROBORATION":
        return rule_result
    return rule_result
