#!/usr/bin/env python3
"""Regenerate keap-v2-get-endpoints-inventory.csv from the upstream Keap v2 Python SDK README.

Usage:
  curl -sSL -o /tmp/keap-v2-readme.md \\
    https://raw.githubusercontent.com/infusionsoft/keap-sdk/main/sdks/v2/python/README.md
  python3 documentation/bau/sprint-01/keap-v2-inventory-regenerate.py /tmp/keap-v2-readme.md

Output: keap-v2-get-endpoints-inventory.csv next to this script (override with second argument).
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROW_RE = re.compile(
    r"^\*([^*]+)\*\s*\|\s*\[\*\*([^\]]+)\*\*\][^|]*\|\s*\*\*(GET)\*\*\s*(\S+)\s*\|\s*(.+)$"
)


def _classify(path: str) -> tuple[str, str, str]:
    p = path.lower()
    overlap: list[str] = []
    if "contacts" in p or "contact_id" in p:
        overlap.append("contacts")
    if "/orders" in p or "order_id" in p:
        overlap.append("orders")
    if "/products" in p or "product_id" in p:
        overlap.append("products")
    if "/opportunities" in p:
        overlap.append("opportunities")
    if "/affiliates" in p:
        overlap.append("affiliates")
    if "/campaigns" in p:
        overlap.append("campaigns")
    if "/notes" in p or "note_id" in p:
        overlap.append("notes")
    if "/tags" in p or "/tag" in p:
        overlap.append("tags")
    if "/subscriptions" in p:
        overlap.append("subscriptions")
    if "/tasks" in p:
        overlap.append("tasks")
    if "customfield" in p or "custom_field" in p or "/model" in p:
        overlap.append("custom_fields")
    overlap = sorted(set(overlap))
    v1_flag = "yes" if overlap else "no"
    hints: list[str] = []
    for hint in (
        "companies",
        "automations",
        "automationcategory",
        "businessprofile",
        "discounts",
        "leadsource",
        "emails",
        "files",
        "merchants",
        "reporting",
        "settings",
        "paymentmethods",
        "productcategories",
        "productinterest",
        "locales",
    ):
        if hint in p.replace("/", "").lower():
            hints.append(hint)
    return v1_flag, "|".join(overlap), "|".join(sorted(set(hints)))


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    readme_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else script_dir / "keap-v2-get-endpoints-inventory.csv"

    rows: list[tuple[str, str, str, str, str]] = []
    with open(readme_path, encoding="utf-8") as f:
        for line in f:
            m = ROW_RE.match(line.rstrip())
            if m:
                api, op, method, pth, desc = m.groups()
                rows.append((api.strip(), op.strip(), method, pth.strip(), desc.strip()))

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "api_class",
                "operation",
                "method",
                "path",
                "description",
                "v1_domain_overlap",
                "overlapping_v1_entities",
                "v2_domain_hints",
            ]
        )
        for r in rows:
            v1f, ov, hints = _classify(r[3])
            w.writerow([r[0], r[1], r[2], r[3], r[4], v1f, ov, hints])

    print(f"Wrote {len(rows)} GET rows to {out_path}")


if __name__ == "__main__":
    main()
