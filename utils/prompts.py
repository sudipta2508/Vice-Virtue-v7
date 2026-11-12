import json


def _json_block(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


def format_paragraphs(paragraphs_dict):
    return "\n\n".join([f"[{k}] {v}" for k, v in paragraphs_dict.items()])


def create_evidence_collector_prompt(dimension, items, paragraphs_dict):
    rows = []
    for i, item in enumerate(items, start=1):
        rows.append(
            f"""{i}. Virtue: {item['virtue']}
   Virtue Definition: {item['item_description']}
   Deficit Vice: {item['deficit_vice']}
   Deficit Definition: {item['deficit_vice_description']}
   Excess Vice: {item['excess_vice']}
   Excess Definition: {item['excess_vice_definition']}"""
        )
    sample = {
        dimension: {
            items[0]["virtue"] if items else "Item": {
                "virtue_evidences": [{"evidence_id": 1, "text": "...", "source_position": "paragraph_1"}],
                "deficit_vice_evidences": [],
                "excess_vice_evidences": [],
            }
        }
    }
    return f"""You are an evidence collector for leadership character analysis.
Extract evidence separately for virtue, deficit vice, and excess vice for each item.

Dimension: {dimension}
Items:
{chr(10).join(rows)}

Narrative:
{format_paragraphs(paragraphs_dict)}

Rules:
- Use exact paragraph references.
- Evidence snippets should be meaningful and self-contained.
- Virtue evidence uses this strict definition: virtue = virtue AND (NOT deficit) AND (NOT excess).
- Do not place a snippet in virtue_evidences if it also indicates deficit vice or excess vice.
- If none found for a class, return empty array.
- Return only valid JSON.

Output format:
{_json_block(sample)}
"""


def _weighted_evidence_rule_block():
    return """Weighted evidence strength (use for every class):
- Each evidence snippet has strength_tier (explicit | strong_implicit | weak) and weight
  (explicit=1.0, strong_implicit=1.0, weak=0.3). Judge a class by the sum of weights,
  not by raw snippet count.
- Weak-only evidence (total strength below 1.0) must NOT produce a score of 4 or 5;
  cap at 3 unless stronger evidence is also present.
- When classes conflict, prefer the class backed by explicit or strong_implicit evidence
  over one backed only by weak snippets."""


def create_evidence_tier_prompt(dimension, items, evidence_dim):
    rows = []
    for i, item in enumerate(items, start=1):
        key = item["virtue"]
        rows.append(
            f"""{i}. Virtue: {key}
   Virtue Definition: {item.get('item_description', '')}
   Deficit Vice: {item.get('deficit_vice', '')}
   Deficit Definition: {item.get('deficit_vice_description', '')}
   Excess Vice: {item.get('excess_vice', '')}
   Excess Definition: {item.get('excess_vice_definition', '')}"""
        )
    sample_item = items[0]["virtue"] if items else "Item"
    sample = {
        dimension: {
            sample_item: {
                "tiers": [
                    {
                        "evidence_id": 1,
                        "cls": "virtue",
                        "strength_tier": "explicit|strong_implicit|weak",
                        "tier_reasoning": "Brief reason vs the class definition.",
                    }
                ]
            }
        }
    }
    return f"""You are an evidence-strength classifier for leadership character analysis.
For each evidence snippet already collected, label how strongly it matches the
definition of its class (virtue, deficit_vice, or excess_vice) for that item.

Strength tiers (pick exactly one per snippet):
- explicit: the text directly and clearly describes the behaviour in the definition
  (names or unmistakably states the trait/behaviour).
- strong_implicit: the text does not name the behaviour, but is strongly tied to the
  definition (clear behavioural signal that matches the definition closely).
- weak: the text is somehow related but only loosely correlated with the definition.

Rules:
- Judge each snippet ONLY against the definition of its class for that item.
- Return one entry per snippet; include every evidence_id from the input.
- Do not invent new snippets or change the text.
- strength_tier must be exactly one of: explicit, strong_implicit, weak.
- Return only valid JSON.

Dimension: {dimension}
Item definitions:
{chr(10).join(rows)}

Collected evidence (by item):
{_json_block(evidence_dim)}

Output format:
{_json_block(sample)}
"""


def create_behavioural_hierarchy_evidence_only_prompt(dimension, item_meta, evidence_triplet):
    virtue = item_meta.get("virtue", "Item")
    example = {
        dimension: {
            virtue: {
                "virtue_score": 3,
                "deficit_vice_score": 3,
                "excess_vice_score": 3,
                "reasoning": "Short rationale based only on definitions and evidence JSON below.",
            }
        }
    }
    meta_block = f"""Virtue: {item_meta.get('virtue', '')}
Virtue definition: {item_meta.get('item_description', '')}
Deficit vice: {item_meta.get('deficit_vice', '')} — {item_meta.get('deficit_vice_description', '')}
Excess vice: {item_meta.get('excess_vice', '')} — {item_meta.get('excess_vice_definition', '')}"""
    return f"""You are the Behavioral Hierarchy scoring agent (evidence-only mode).
Do NOT assume access to any full narrative beyond the evidence snippets provided in JSON.
Score this single item on three classes: virtue, deficit vice, excess vice.
Score scale: 0=no evidence, 1=extremely unlikely, 2=unlikely, 3=maybe/maybe not, 4=likely, 5=extremely likely.

Critical evidence rule:
- If a class has an empty evidence list, that class score MUST be 0 (never 3).
- Do not invent uncertainty scores when there is no evidence.

Critical coherence rule:
- At most one of virtue/deficit/excess can be high (4 or 5).
- Two-high and three-high are not allowed.
- Uncertainty carve-out: all three may be 3 ONLY when every class has at least some evidence.

Dimension: {dimension}

Item definitions:
{meta_block}

Evidence triplet (virtue / deficit_vice / excess_vice lists):
{_json_block({virtue: evidence_triplet})}

Return only valid JSON for this one item (use the virtue name as the key under the dimension):
{_json_block(example)}
"""


def create_dimension_clarification_evidence_prompt(dimension, items, user_answer):
    rows = []
    for i, item in enumerate(items, start=1):
        rows.append(
            f"""{i}. Virtue: {item['virtue']}
   Virtue Definition: {item['item_description']}
   Deficit Vice: {item['deficit_vice']}
   Deficit Definition: {item['deficit_vice_description']}
   Excess Vice: {item['excess_vice']}
   Excess Definition: {item['excess_vice_definition']}"""
        )
    source_pos = f"followup_{dimension.replace(' ', '_')}"
    sample = {
        dimension: {
            items[0]["virtue"] if items else "Item": {
                "virtue_evidences": [
                    {"evidence_id": 1, "text": "...", "source_position": source_pos}
                ],
                "deficit_vice_evidences": [],
                "excess_vice_evidences": [],
            }
        }
    }
    return f"""You are an evidence collector for leadership character analysis (follow-up clarification).
Extract evidence separately for virtue, deficit vice, and excess vice for each item in this dimension.
Use ONLY the leader's follow-up answer below — do not invent facts.

Dimension: {dimension}
Items:
{chr(10).join(rows)}

Leader follow-up answer:
{user_answer}

Rules:
- Evidence snippets should be meaningful and self-contained quotes or paraphrases from the answer.
- Use source_position exactly: "{source_pos}" for every snippet from this answer.
- Virtue evidence: virtue = virtue AND (NOT deficit) AND (NOT excess).
- Do not place a snippet in virtue_evidences if it also indicates deficit vice or excess vice.
- If none found for a class, return empty array.
- Return only valid JSON.

Output format:
{_json_block(sample)}
"""


def create_behavioural_hierarchy_prompt(dimension, items, paragraphs_dict):
    rows = []
    for i, item in enumerate(items, start=1):
        rows.append(
            f"{i}. {item['virtue']} | deficit={item['deficit_vice']} | excess={item['excess_vice']}"
        )
    example = {
        dimension: {
            items[0]["virtue"] if items else "Item": {
                "virtue_score": 3,
                "deficit_vice_score": 3,
                "excess_vice_score": 3,
                "reasoning": "Short rationale.",
            }
        }
    }
    return f"""You are the Behavioral Hierarchy scoring agent.
Score each item on three classes: virtue, deficit vice, excess vice.
Score scale: 0=no evidence, 1=extremely unlikely, 2=unlikely, 3=maybe/maybe not, 4=likely, 5=extremely likely.

Critical evidence rule:
- If the narrative has no evidence for a class on an item, that class score MUST be 0 (never 3).
- Do not invent uncertainty scores when there is no supporting text.

Critical coherence rule:
- At most one of virtue/deficit/excess can be high (4 or 5).
- Two-high and three-high are not allowed.
- Uncertainty carve-out: all three may be 3 ONLY when every class has at least some evidence.

Dimension: {dimension}
Items:
{chr(10).join(rows)}

Narrative:
{format_paragraphs(paragraphs_dict)}

Return only valid JSON:
{_json_block(example)}
"""


def create_combined_analysis_prompt(dimension, items_with_evidence):
    sample_item = next(iter(items_with_evidence.keys()), "Item")
    example = {
        dimension: {
            sample_item: {
                "virtue": {
                    "frequency": {"supporting": 0, "contradictory": 0, "undefined": 0},
                    "consistency": "consistent",
                    "type_counts": {"execution": 0, "intention": 0},
                    "writing_counts": {"confident": 0, "hedging": 0},
                    "level_counts": {"level_1": 0, "level_2": 0, "level_3": 0, "level_4": 0, "level_5": 0},
                    "special_flags": {
                        "situationalInconsistency": 0,
                        "socialDesirabilityFlags": {"flag": False, "reasoning": ""},
                        "negativeBehaviorFlags": {"flag": False, "reasoning": ""},
                    },
                    "specific_situation_examples": {
                        "count": 0,
                        "high_intensity_count": 0,
                        "medium_intensity_count": 0,
                        "low_intensity_count": 0,
                    },
                },
                "deficit_vice": {},
                "excess_vice": {},
            }
        }
    }
    return f"""Analyze each item's evidence triplet (virtue, deficit vice, excess vice).
For each class compute:
1) frequency labels (supporting/contradictory/undefined)
2) consistency
3) execution/intention counts
4) confident/hedging counts
5) explicitness level counts (1..5) — these are separate from strength_tier on each snippet
6) special flags (situationalInconsistency, social desirability, negative behavior)
7) specific situation examples: count evidence items that describe a specific situation
   (named/described context) + concrete actions taken by the person + the stakes or
   intensity of the situation. For each such item classify intensity as:
   high = crisis, high-stakes, rare or pressure-heavy situation;
   medium = moderate challenge or non-routine situation;
   low = routine or low-stakes situation.
   Return counts: count, high_intensity_count, medium_intensity_count, low_intensity_count.

{_weighted_evidence_rule_block()}

Input:
{_json_block(items_with_evidence)}

Return only valid JSON:
{_json_block(example)}
"""


def create_scoring_prompt(dimension, items_inputs):
    sample_item = next(iter(items_inputs.keys()), "Item")
    example = {
        dimension: {
            sample_item: {
                "virtue_score": 0,
                "deficit_vice_score": 0,
                "excess_vice_score": 0,
                "virtue_reasoning": "",
                "deficit_vice_reasoning": "",
                "excess_vice_reasoning": "",
            }
        }
    }
    return f"""You are the tri-class scoring agent.
For each item compute class-wise scores from 0..5 for virtue, deficit_vice, excess_vice.
Use evidence + analysis features to score each class independently.
Rule: no evidence for a class => score 0.
Rule: if supportive/contradictory tied, choose lower plausible score.
Rule: if social desirability or negative behavior flags are true, prefer lower score.

{_weighted_evidence_rule_block()}

Input:
{_json_block(items_inputs)}

Return only valid JSON:
{_json_block(example)}
"""


def create_coordinator_prompt(dimension, items_inputs):
    sample_item = next(iter(items_inputs.keys()), "Item")
    example = {
        dimension: {
            sample_item: {
                "final_virtue_score": 0,
                "final_deficit_vice_score": 0,
                "final_excess_vice_score": 0,
                "dominant_class": "virtue|deficit_vice|excess_vice|uncertain",
                "arbitration_reasoning": "",
            }
        }
    }
    return f"""You are the coordinator and final arbitrator.
Decide final class-wise scores for each item using:
- adjusted/initial scores
- behavioral hierarchy scores
- evidence counts and quality
- analysis reasoning and special flags

Hard constraints:
- At most one class can be high (4 or 5).
- Two-high and three-high are invalid.
- If a class has no evidence snippets, its final score MUST be 0 (never 3).
- If uncertainty is strong AND every class has some evidence, all three can be 3.
- If both deficit and excess are high, choose the more prominent one and penalize the other.
- If virtue conflicts with vice classes, reward/keep or penalize virtue based on evidence and flags.
- If multiple flags are raised (2 or more), penalize virtue and reward the more prominent vice
  (deficit_vice or excess_vice) using evidence strength and reasoning quality.

{_weighted_evidence_rule_block()}

Situational example reward (apply before enforcing the single-high constraint):
- For each class, check specific_situation_examples in the analysis.
- If high_intensity_count >= 1: reward that class +1 (clamped to 5).
- If high_intensity_count == 0 and medium_intensity_count >= 2 and current score >= 3: reward +1.
- Low-intensity examples alone do not trigger a reward.
- The reward reflects that concrete, high-stakes behavioral evidence is stronger signal than
  vague or general claims.

Input:
{_json_block(items_inputs)}

Return only valid JSON:
{_json_block(example)}
"""


def create_adjustment_prompt(dimension, items_inputs):
    sample_item = next(iter(items_inputs.keys()), "Item")
    example = {
        dimension: {
            sample_item: {
                "virtue_adjustment": 0,
                "deficit_vice_adjustment": 0,
                "excess_vice_adjustment": 0,
                "virtue_score_adjusted": 0,
                "deficit_vice_score_adjusted": 0,
                "excess_vice_score_adjusted": 0,
                "adjustment_reasoning": "",
            }
        }
    }
    return f"""You are a tri-class adjustment agent.
For each class (virtue, deficit_vice, excess_vice) assign adjustment in {{-1, 0, +1}}.
Use evidence quality, consistency, and special flags.
Clamp adjusted scores to 0..5.
Keep changes conservative — default to 0 unless evidence clearly justifies a shift.
If special flags are raised, weigh them against the strength and volume of supporting evidence
before applying any adjustment; do not penalize a class solely because flags exist.

{_weighted_evidence_rule_block()}

Input:
{_json_block(items_inputs)}

Return only valid JSON:
{_json_block(example)}
"""
