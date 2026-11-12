"""Per-dimension mean scores from item-level coordinator results.

Means are taken only over items that have evidence for that class.
Items with no evidence for a class are excluded (not treated as 0).
"""

from __future__ import annotations

from gap_detection import EVIDENCE_CLASSES

CLASS_TO_COORDINATOR_KEY = {
    "virtue": "final_virtue_score",
    "deficit_vice": "final_deficit_vice_score",
    "excess_vice": "final_excess_vice_score",
}


def class_has_evidence(evidence_item: dict, cls: str) -> bool:
    if not isinstance(evidence_item, dict):
        return False
    return len(evidence_item.get(f"{cls}_evidences", []) or []) > 0


def _coordinator_score(co_item: dict, score_key: str) -> int:
    try:
        return int(co_item.get(score_key, 0))
    except (TypeError, ValueError):
        return 0


def compute_dimension_means(output: dict, catalog: dict) -> dict:
    """
    For each dimension, compute class means over items that have evidence:

    - mean virtue: sum(final_virtue_score) / count(items with virtue evidence)
    - same for deficit_vice and excess_vice

    If no item has evidence for a class, that mean is None.
    """
    result = {}
    coordinator_root = output.get("coordinator", {})
    evidence_root = output.get("evidence", {})

    for dimension, items in catalog.items():
        coordinator_dim = coordinator_root.get(dimension, {})
        evidence_dim = evidence_root.get(dimension, {})
        n = len(items)
        entry = {
            "virtue": None,
            "deficit_vice": None,
            "excess_vice": None,
            "item_counts": {cls: 0 for cls in EVIDENCE_CLASSES},
        }
        entry["item_counts"]["total_items"] = n

        if n == 0:
            result[dimension] = entry
            continue

        for cls in EVIDENCE_CLASSES:
            score_key = CLASS_TO_COORDINATOR_KEY[cls]
            total = 0
            counted = 0
            for item in items:
                key = item["virtue"]
                ev_item = evidence_dim.get(key, {})
                if not class_has_evidence(ev_item, cls):
                    continue
                co_item = coordinator_dim.get(key, {})
                total += _coordinator_score(co_item, score_key)
                counted += 1
            entry["item_counts"][cls] = counted
            if counted > 0:
                entry[cls] = round(total / counted, 2)

        result[dimension] = entry

    return result


def _format_mean(value) -> str:
    if value is None:
        return "-"
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}"


def render_dimension_means_table(means: dict, label: str):
    """Render dimension means in Streamlit."""
    import streamlit as st

    if not means:
        return

    st.markdown(
        f"**{label}** — dimension means "
        "(mean over items with evidence for each class; no evidence shown as -)"
    )
    rows = []
    for dimension, data in means.items():
        counts = data.get("item_counts", {})
        rows.append(
            {
                "Dimension": dimension,
                "Mean virtue": _format_mean(data.get("virtue")),
                "Mean deficit vice": _format_mean(data.get("deficit_vice")),
                "Mean excess vice": _format_mean(data.get("excess_vice")),
                "Items with virtue evidence": counts.get("virtue", 0),
                "Items with deficit evidence": counts.get("deficit_vice", 0),
                "Items with excess evidence": counts.get("excess_vice", 0),
                "Items (n)": counts.get("total_items", 0),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
