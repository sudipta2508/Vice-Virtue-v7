"""Merge dimension follow-up answers into per-item evidence."""

from __future__ import annotations

import copy
from typing import Any

EVIDENCE_CLASSES = ("virtue", "deficit_vice", "excess_vice")


def _next_evidence_id(evidence_item: dict) -> int:
    mx = 0
    for cls in EVIDENCE_CLASSES:
        for ev in evidence_item.get(f"{cls}_evidences", []) or []:
            try:
                mx = max(mx, int(ev.get("evidence_id", 0) or 0))
            except (TypeError, ValueError):
                pass
    return mx + 1


def _count_snippets(evidence_item: dict) -> int:
    total = 0
    for cls in EVIDENCE_CLASSES:
        total += len(evidence_item.get(f"{cls}_evidences", []) or [])
    return total


def merge_dimension_clarification(
    existing_dim_evidence: dict,
    new_dim_evidence: dict,
    dimension: str,
    turn: int,
) -> tuple[dict, list[str]]:
    """
    Append new snippets onto existing per-item evidence.
    Returns (updated_dim_evidence, list of item_keys that received >=1 new snippet).
    """
    updated = copy.deepcopy(existing_dim_evidence)
    reassess_targets: list[str] = []

    for item_key, new_item in (new_dim_evidence or {}).items():
        if not isinstance(new_item, dict):
            continue
        base = updated.setdefault(
            item_key,
            {
                "virtue_evidences": [],
                "deficit_vice_evidences": [],
                "excess_vice_evidences": [],
            },
        )
        before_count = _count_snippets(base)
        next_id = _next_evidence_id(base)

        for cls in EVIDENCE_CLASSES:
            key = f"{cls}_evidences"
            for ev in new_item.get(key, []) or []:
                if not isinstance(ev, dict):
                    continue
                text = (ev.get("text") or "").strip()
                if not text:
                    continue
                snippet = copy.deepcopy(ev)
                snippet["evidence_id"] = next_id
                next_id += 1
                pos = snippet.get("source_position") or f"followup_{dimension.replace(' ', '_')}_turn_{turn}"
                snippet["source_position"] = pos
                base.setdefault(key, []).append(snippet)

        if _count_snippets(base) > before_count:
            reassess_targets.append(item_key)

    return updated, reassess_targets


def normalize_dimension_evidence(raw: Any, dimension: str) -> dict:
    if isinstance(raw, dict) and dimension in raw:
        return raw[dimension]
    return raw if isinstance(raw, dict) else {}
