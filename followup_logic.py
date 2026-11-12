"""Follow-up Q&A logic (API-agnostic helpers used by the session graph)."""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

from api.dimension_metadata import JUDGMENT_NAME, WHEEL_ORDER
from config import GAP_THRESHOLD
from followup_evidence import merge_dimension_clarification
from gap_detection import (
    build_followup_queue,
    build_gap_queue,
    needs_followup,
)
from graph.clarification import extract_clarification_evidence
from graph.reassessment_graph import reassess_items_parallel

CONSENT_MESSAGE = (
    "Can I ask you a few more questions for better assessment of your leader character?"
)

NO_GAPS_MESSAGE = (
    "Your narrative covered the leader character dimensions reasonably well "
    "(most items had supporting evidence). No follow-up questions are needed. "
    "Your assessment results are ready."
)

ADD_MORE_CONSENT_MESSAGE = (
    "Would you like to add anything more about your leader character? "
    "Reply **yes** or **no**."
)

ADD_MORE_AGAIN_MESSAGE = (
    "Do you want to add anything more? Reply **yes** or **no**."
)

AMBIGUOUS_YES_NO_MESSAGE = (
    "I didn't catch that — please reply **yes** or **no** (or tap a quick-reply button)."
)


def build_combined_narrative(base_narrative: str, pre_additions: list) -> str:
    """Merge initial narrative with pre-baseline dimension additions for Stage 1."""
    text = (base_narrative or "").strip()
    for entry in pre_additions or []:
        dim = entry.get("dimension", "")
        addition = (entry.get("text") or "").strip()
        if not addition:
            continue
        label = dim or "Additional"
        text += f"\n\n--- Additional: {label} ---\n{addition}"
    return text


def optional_dimension_prompt(catalog: dict) -> str:
    names = sorted(catalog.keys())
    listed = ", ".join(f"**{n}**" for n in names)
    return (
        "Which dimension would you like to tell me more about? "
        f"Choose one of: {listed}."
    )


def optional_narrative_prompt(dimension: str) -> str:
    return f"Sure — tell me more about your **{dimension}**."


def gap_dimension_add_more_prompt(dimension: str) -> str:
    return (
        f"Do you want to add anything more about your **{dimension}**? "
        "Reply **yes** or **no**."
    )


def dimension_consent_prompt(dimension: str) -> str:
    return (
        f"Would you like to tell me more about your **{dimension}**? "
        "Reply **yes** or **no**."
    )


def order_gap_dimensions(dims: list[str]) -> list[str]:
    """Judgment first, then WHEEL_ORDER, then any remaining names alphabetically."""
    remaining = list(dims)
    ordered: list[str] = []
    if JUDGMENT_NAME in remaining:
        ordered.append(JUDGMENT_NAME)
        remaining.remove(JUDGMENT_NAME)
    for name in WHEEL_ORDER:
        if name in remaining:
            ordered.append(name)
            remaining.remove(name)
    ordered.extend(sorted(remaining))
    return ordered


def match_dimension_from_text(text: str, catalog: dict) -> str | None:
    """Match user text to a catalog dimension name."""
    t = (text or "").strip().lower()
    if not t:
        return None
    names = list(catalog.keys())
    for name in names:
        if t == name.lower():
            return name
    for name in names:
        nl = name.lower()
        if nl in t or t in nl:
            return name
    t_words = set(re.findall(r"[a-z]+", t))
    best = None
    best_score = 0
    for name in names:
        n_words = set(re.findall(r"[a-z]+", name.lower()))
        overlap = len(t_words & n_words)
        if overlap > best_score:
            best_score = overlap
            best = name
    if best_score >= 1:
        return best
    return None


def dimension_question(
    dimension: str,
    catalog: dict | None = None,
    evidence: dict | None = None,
) -> str:
    """Ask about the dimension without naming individual leader character items."""
    _ = catalog, evidence  # kept for call-site compatibility
    return (
        f"Can you tell me more about your **{dimension}**? "
        "You can specify different moments or situations when this dimension of leader character "
        "was portrayed. You can also tell me the situations when you couldn't."
    )


def parse_wants_to_end(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    end_phrases = [
        "show me the report",
        "show the report",
        "show report",
        "see the report",
        "view the report",
        "get the report",
        "end the conversation",
        "end conversation",
        "end this conversation",
        "stop the conversation",
        "stop here",
        "stop now",
        "i'm done",
        "im done",
        "i am done",
        "that's all",
        "thats all",
        "that is all",
        "no more questions",
        "don't have time",
        "dont have time",
        "do not have time",
        "no time",
        "not enough time",
        "finish now",
        "generate report",
        "view results",
        "see results",
        "enough for now",
        "let's finish",
        "lets finish",
        "wrap up",
        "skip the rest",
        "skip remaining",
    ]
    if any(p in t for p in end_phrases):
        return True
    if re.search(r"\b(show|see|view|get)\b.*\breport\b", t):
        return True
    if re.search(r"\b(end|stop|finish|quit)\b.*\b(conversation|chat|questions?)\b", t):
        return True
    return False


def parse_yes_no(text: str) -> str | None:
    """Alias for yes/no parsing used in consent and optional add-more flows."""
    return parse_consent_reply(text)


def parse_consent_reply(text: str) -> str | None:
    """Looser yes/no parsing — accepts buttons and common conversational replies."""
    t = (text or "").strip().lower()
    if not t:
        return None
    # Strip markdown bold / punctuation wrappers from quick replies
    t = re.sub(r"[*_`]", "", t).strip()
    t = t.strip(".!?,;:\"'()[]{}")

    yes_patterns = [
        r"^y(es)?\.?$",
        r"^sure\.?$",
        r"^ok(ay)?\.?$",
        r"^please\.?$",
        r"^go ahead\.?$",
        r"^of course\.?$",
        r"^absolutely\.?$",
        r"^certainly\.?$",
        r"^yeah\.?$",
        r"^yep\.?$",
        r"^yup\.?$",
        r"^affirmative\.?$",
        r"^sounds good\.?$",
        r"^why not\.?$",
        r"^let'?s do it\.?$",
        r"^i('d| would) like( to)?\.?$",
        r"^happy to\.?$",
    ]
    no_patterns = [
        r"^n(o)?\.?$",
        r"^nope\.?$",
        r"^nah\.?$",
        r"^skip\.?$",
        r"^not now\.?$",
        r"^no thanks\.?$",
        r"^no thank you\.?$",
        r"^decline\.?$",
        r"^pass\.?$",
        r"^i'?m good\.?$",
        r"^im good\.?$",
        r"^not really\.?$",
        r"^prefer not\.?$",
    ]
    for pat in yes_patterns:
        if re.search(pat, t):
            return "yes"
    for pat in no_patterns:
        if re.search(pat, t):
            return "no"
    if any(
        w in t
        for w in (
            "yes",
            "sure",
            "okay",
            "ok ",
            "please",
            "go ahead",
            "happy to",
            "sounds good",
            "of course",
            "absolutely",
        )
    ):
        return "yes"
    if any(
        w in t
        for w in (
            "no ",
            "nope",
            "skip",
            "decline",
            "not now",
            "don't",
            "dont ",
            "no thanks",
            "pass",
        )
    ):
        return "no"
    # Lone "no" after stripping
    if t == "no":
        return "no"
    return None


def looks_like_api_key(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 20:
        return False
    if t.startswith("sk-"):
        return True
    if " " in t or "\n" in t:
        return False
    return len(t) >= 30


def init_followup_state(session: dict, catalog: dict, out_baseline: dict) -> list[dict]:
    """Initialize follow-up fields on session. Returns assistant messages to append."""
    evidence = out_baseline.get("evidence", {})
    threshold = session.get("gap_threshold")
    if threshold is None:
        threshold = GAP_THRESHOLD
    threshold = float(threshold)
    gap_dims = order_gap_dimensions(build_gap_queue(evidence, catalog, threshold=threshold))
    session["followup_gap_dims"] = gap_dims
    session["followup_queue"] = []
    session["followup_asked"] = []
    session["followup_audit"] = []
    session["followup_reassess_targets"] = {}
    session["followup_pending_dim"] = None
    session["followup_token_usage"] = {"input_tokens": 0, "output_tokens": 0}

    if not gap_dims:
        session["followup_phase"] = "skipped_no_gaps"
        session["out_final"] = session.get("out_working")
        return [{"role": "assistant", "content": NO_GAPS_MESSAGE}]

    session["followup_phase"] = "await_consent"
    return [{"role": "assistant", "content": CONSENT_MESSAGE}]


def advance_to_next_dimension_question(session: dict, catalog: dict | None = None) -> list[dict]:
    """Advance follow-up queue to the next dimension's consent prompt. Returns messages to append."""
    _ = catalog  # kept for call-site compatibility
    queue = session.get("followup_queue") or []
    asked = set(session.get("followup_asked") or [])

    for dim in queue:
        if dim not in asked:
            session["followup_asked"] = list(asked | {dim})
            session["followup_pending_dim"] = dim
            session["followup_phase"] = "await_dim_consent"
            return [
                {
                    "role": "assistant",
                    "content": dimension_consent_prompt(dim),
                }
            ]
    session["followup_pending_dim"] = None
    session["followup_phase"] = "reassessing"
    return []


async def process_dimension_answer(
    api_key: str,
    model: str,
    dimension: str,
    user_answer: str,
    catalog: dict,
    working_out: dict,
    session: dict,
    *,
    source: str = "gap",
) -> dict[str, Any]:
    items = catalog[dimension]
    turn = len(session.get("followup_audit", [])) + 1
    existing = working_out["evidence"].get(dimension, {})

    new_ev = {}
    if (user_answer or "").strip():
        new_ev = await extract_clarification_evidence(
            api_key, model, dimension, items, user_answer.strip(), session
        )

    updated_dim, targets = merge_dimension_clarification(existing, new_ev, dimension, turn)
    working_out["evidence"][dimension] = updated_dim

    # Only keep items that actually received new evidence snippets
    all_targets = session.get("followup_reassess_targets") or {}
    prev = set(all_targets.get(dimension, []))
    all_targets[dimension] = list(prev | set(targets))
    # Drop empty dimension keys
    all_targets = {d: keys for d, keys in all_targets.items() if keys}
    session["followup_reassess_targets"] = all_targets

    return {
        "dimension": dimension,
        "user_answer": user_answer,
        "turn": turn,
        "source": source,
        "items_with_new_evidence": targets,
        "new_item_count": len(targets),
    }


async def run_final_reassessment(
    api_key: str,
    model: str,
    catalog: dict,
    working_out: dict,
    session: dict,
    on_progress: Optional[Callable[[str, float, str], None]] = None,
) -> dict[str, int]:
    targets = session.get("followup_reassess_targets") or {}
    # Minimal targets: only items with new evidence
    targets = {d: keys for d, keys in targets.items() if keys}
    if not targets:
        return {"input_tokens": 0, "output_tokens": 0}

    def _status(msg: str):
        if on_progress:
            on_progress("reassessing", 0.5, msg)

    usage = await reassess_items_parallel(
        api_key,
        model,
        catalog,
        working_out,
        targets,
        status_callback=_status,
    )
    prev = session.setdefault("followup_token_usage", {"input_tokens": 0, "output_tokens": 0})
    prev["input_tokens"] += usage["input_tokens"]
    prev["output_tokens"] += usage["output_tokens"]
    return usage
