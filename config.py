from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_XLSX_PATH = PROJECT_ROOT / "LCIA_Virtues_Vices_Definition.xlsx"

DEFAULT_MODEL = "claude-sonnet-5-5"
# Cheaper/faster model for Combined Analysis (stage 2)
FAST_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_TOKENS = 16000
CLASSIFICATION_MAX_TOKENS = 12000
DEFAULT_TEMPERATURE = 0
# Max dimensions processed concurrently in the assessment graph
MAX_CONCURRENT_DIMENSIONS = 4

# Cache: keep stage results keyed by narrative hash (do not wipe whole cache each run)
CACHE_POLICY = "narrative_hash"  # narrative_hash | session | off

# Anthropic pricing (USD per million tokens) used for the cost estimate
INPUT_TOKEN_PRICE_PER_M = 3.0
OUTPUT_TOKEN_PRICE_PER_M = 15.0

HIGH_THRESHOLD = 4
LOW_MAX = 2
UNCERTAINTY_SCORE = 3
# Follow-up: a dimension needs follow-up when coverage of addressed items is below this
MIN_DIMENSION_COVERAGE = 0.70
GAP_THRESHOLD = MIN_DIMENSION_COVERAGE  # alias for session.gap_threshold callers

# Evidence strength tiers (stage 1b) — Explicit / Strong-implicit / Weak
EVIDENCE_TIER_WEIGHTS = {"explicit": 1.0, "strong_implicit": 1.0, "weak": 0.3}
EVIDENCE_TIER_FALLBACK = "strong_implicit"  # used if the classifier skips a snippet
EVIDENCE_TIER_MODEL = FAST_MODEL  # Haiku; one call per dimension
HIGH_SCORE_MIN_STRENGTH = 1.0  # a class needs this strength to score 4 or 5
WEAK_ONLY_MAX_SCORE = 3  # cap for a class whose strength is below that


def _xlsx_rows(xlsx_path: Path, sheet_name: str):
    ns = {
        "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    with zipfile.ZipFile(xlsx_path) as zf:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
        }

        shared_strings = []
        if "xl/sharedStrings.xml" in zf.namelist():
            sst = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in sst.findall("a:si", ns):
                shared_strings.append("".join((t.text or "") for t in si.findall(".//a:t", ns)))

        target = None
        for sh in wb.findall("a:sheets/a:sheet", ns):
            if sh.attrib.get("name") == sheet_name:
                rid = sh.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
                target = "xl/" + rel_map[rid]
                break
        if not target:
            raise ValueError(f"Sheet '{sheet_name}' not found in {xlsx_path}")

        xml = ET.fromstring(zf.read(target))

        def value(cell):
            ctype = cell.attrib.get("t")
            v = cell.find("a:v", ns)
            if v is None:
                return ""
            raw = v.text or ""
            if ctype == "s" and raw.isdigit():
                idx = int(raw)
                return shared_strings[idx] if idx < len(shared_strings) else raw
            return raw

        def colnum(ref: str) -> int:
            letters = re.match(r"[A-Z]+", ref).group(0)
            n = 0
            for ch in letters:
                n = n * 26 + (ord(ch) - 64)
            return n

        rows = []
        for row in xml.findall("a:sheetData/a:row", ns):
            vals = {}
            for cell in row.findall("a:c", ns):
                ref = cell.attrib.get("r", "A1")
                vals[colnum(ref)] = value(cell).strip()
            if not vals:
                continue
            max_col = max(vals.keys())
            rows.append([vals.get(i, "") for i in range(1, max_col + 1)])
        return rows


def load_item_catalog_from_xlsx(xlsx_path: Path = DATA_XLSX_PATH):
    rows = _xlsx_rows(xlsx_path, "Coding")
    if not rows:
        return {}

    catalog = {}
    for row in rows[1:]:
        if len(row) < 7:
            continue
        dimension = row[0].strip()
        virtue = row[1].strip()
        item_desc = row[2].strip()
        deficit = row[3].strip()
        deficit_desc = row[4].strip()
        excess = row[5].strip()
        excess_desc = row[6].strip()
        if not dimension or not virtue:
            continue
        catalog.setdefault(dimension, []).append(
            {
                "virtue": virtue,
                "item_description": item_desc,
                "deficit_vice": deficit,
                "deficit_vice_description": deficit_desc,
                "excess_vice": excess,
                "excess_vice_definition": excess_desc,
            }
        )
    return catalog
