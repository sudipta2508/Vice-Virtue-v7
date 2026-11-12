"""Detect dimensions with insufficient evidence for follow-up Q&A."""

from config import EVIDENCE_TIER_FALLBACK, GAP_THRESHOLD, MIN_DIMENSION_COVERAGE

EVIDENCE_CLASSES = ("virtue", "deficit_vice", "excess_vice")
_ADDRESSED_TIERS = frozenset({"explicit", "strong_implicit"})


def item_has_no_evidence(evidence_item: dict) -> bool:
    """True when no snippets exist in any of the three evidence classes."""
    if not isinstance(evidence_item, dict):
        return True
    return all(
        len(evidence_item.get(f"{cls}_evidences", []) or []) == 0 for cls in EVIDENCE_CLASSES
    )


def _snippet_tier(ev: dict) -> str:
    raw = ev.get("strength_tier") if isinstance(ev, dict) else None
    if isinstance(raw, str) and raw.strip():
        key = raw.strip().lower().replace("-", "_").replace(" ", "_")
        if key in ("explicit",):
            return "explicit"
        if key in ("strong_implicit", "strongimplicit", "implicit"):
            return "strong_implicit"
        if key in ("weak", "weak_implicit"):
            return "weak"
    return EVIDENCE_TIER_FALLBACK


def item_is_addressed(evidence_item: dict) -> bool:
    """True when any class has at least one explicit or strong_implicit snippet.

    Weak snippets never count. Missing tier uses the fallback (strong_implicit).
    """
    if not isinstance(evidence_item, dict):
        return False
    for cls in EVIDENCE_CLASSES:
        snippets = evidence_item.get(f"{cls}_evidences", []) or []
        if not isinstance(snippets, list):
            continue
        for ev in snippets:
            if not isinstance(ev, dict):
                continue
            if _snippet_tier(ev) in _ADDRESSED_TIERS:
                return True
    return False


def dimension_coverage(evidence_dim: dict, catalog_items: list) -> float:
    """Fraction of catalog items that are addressed (explicit / strong-implicit)."""
    if not catalog_items:
        return 0.0
    addressed = sum(
        1
        for it in catalog_items
        if item_is_addressed((evidence_dim or {}).get(it["virtue"], {}))
    )
    return addressed / len(catalog_items)


def build_gap_queue(
    evidence: dict,
    catalog: dict,
    threshold: float = None,
) -> list[str]:
    """Dimensions whose coverage of addressed items is below the threshold."""
    if threshold is None:
        threshold = MIN_DIMENSION_COVERAGE
    gaps = []
    for dimension, items in catalog.items():
        dim_evidence = (evidence or {}).get(dimension, {})
        if dimension_coverage(dim_evidence, items) < float(threshold):
            gaps.append(dimension)
    return gaps


def needs_followup(evidence: dict, catalog: dict, threshold: float = None) -> bool:
    """True when at least one dimension is below the coverage threshold."""
    return len(build_gap_queue(evidence, catalog, threshold)) > 0


def build_followup_queue(
    evidence: dict,
    catalog: dict,
    *,
    threshold: float = None,
) -> list[str]:
    """Return dimension names that need follow-up (gap dimensions only)."""
    if threshold is None:
        threshold = GAP_THRESHOLD
    return build_gap_queue(evidence, catalog, threshold)
