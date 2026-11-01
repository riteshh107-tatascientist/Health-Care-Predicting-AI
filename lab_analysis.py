"""Lab-report parsing and reference-range comparison.

Educational only. Values are compared with ILLUSTRATIVE reference ranges unless the report
itself states a range next to the value, in which case that range is used and labelled.
"""
from __future__ import annotations

import re

import config

NUMBER = r"\d+(?:\.\d+)?"
_RANGE_RE = re.compile(rf"({NUMBER})\s*(?:-|–|—|to)\s*({NUMBER})")


def _range_for(spec: dict, sex: str | None) -> tuple[float | None, float | None, str]:
    ranges = spec["ranges"]
    if sex and sex in ranges:
        return (*ranges[sex], "illustrative")
    if "default" in ranges:
        return (*ranges["default"], "illustrative")
    # Sex unknown and only sex-specific ranges exist: use the widest combined range.
    lows = [r[0] for r in ranges.values()]
    highs = [r[1] for r in ranges.values()]
    low = min(lows) if all(v is not None for v in lows) else None
    high = max(highs) if all(v is not None for v in highs) else None
    return low, high, "illustrative (sex not set in profile)"


def parse_lab_text(text: str) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for raw_line in (text or "").splitlines():
        line = " ".join(raw_line.lower().split())
        if not line:
            continue
        for key, spec in config.LAB_REFERENCE.items():
            if key in found or any(ex in line for ex in spec.get("exclude", [])):
                continue
            alternatives = "|".join(re.escape(s) for s in sorted(spec["synonyms"], key=len, reverse=True))
            match = re.search(rf"(?<![a-z])(?:{alternatives})(?![a-z])", line)
            if not match:
                continue
            rest = line[match.end():]
            value_match = re.search(rf"[^\d]{{0,30}}?({NUMBER})", rest)
            if not value_match:
                continue
            nearby = rest[value_match.end(): value_match.end() + 40]
            range_match = _RANGE_RE.search(nearby)
            report_range = None
            if range_match:
                lo, hi = float(range_match.group(1)), float(range_match.group(2))
                if lo < hi:
                    report_range = (lo, hi)
            found[key] = {
                "key": key,
                "label": spec["label"],
                "value": float(value_match.group(1)),
                "unit": spec["unit"],
                "report_range": report_range,
            }
    return found


def evaluate(value: float, low: float | None, high: float | None) -> str:
    if low is None and high is None:
        return "No reference range available"
    if low is not None and value < low:
        return "Below range"
    if high is not None and value > high:
        return "Above range"
    return "Within range"


def analyze_report(text: str, sex: str | None = None) -> list[dict]:
    """Return one row per recognised analyte with status and reference information."""
    rows = []
    for key, item in parse_lab_text(text).items():
        spec = config.LAB_REFERENCE[key]
        if item["report_range"]:
            low, high = item["report_range"]
            source = "stated in your report"
        else:
            low, high, source = _range_for(spec, sex)
        rows.append({
            "Test": item["label"],
            "Result": item["value"],
            "Unit": item["unit"],
            "Reference low": low,
            "Reference high": high,
            "Status": evaluate(item["value"], low, high),
            "Reference source": source,
        })
    return sorted(rows, key=lambda r: r["Test"])
