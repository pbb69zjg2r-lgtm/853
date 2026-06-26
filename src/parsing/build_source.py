"""
build_source.py — Convert raw_parse.json → source_blocks.jsonl + document_structure.json.

Input:  raw_parse.json
Output: source_blocks.jsonl + document_structure.json
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.core.contracts import stage_input_paths, stage_output_paths

TEXT_LIKE = {"text", "title", "list", "list_text", "interline_equation",
             "inline_equation", "code", "algorithm", "footnote", "aside_text"}
FIGURE_LIKE = {"image", "image_body", "image_caption", "chart", "chart_body"}
TABLE_LIKE = {"table", "table_body", "table_caption", "table_footnote"}

# Keyword-based section type classification (ordered by priority)
ABSTRACT_PATTERN = re.compile(r"\bABSTRACT\b", re.IGNORECASE)


SECTION_TYPE_RULES = [
    ("abstract",           [r"\babstract\b"]),
    ("introduction",       [r"\bintroduction\b", r"\bbackground\b"]),
    ("methods",            [r"\bmethods?\b", r"\bmaterials?\s+(and|&)\s+methods?\b",
                             r"\bexperimental\s+(procedures?|section)\b"]),
    ("results",            [r"\bresults?\b", r"\bfindings\b"]),
    ("discussion",         [r"\bdiscussion\b"]),
    ("conclusion",         [r"\bconclusion\b", r"\bconcluding\s+remarks\b",
                             r"\bsummary\b"]),
    ("supplementary",      [r"\bsupporting\s+information\b", r"\bsupplementary\b",
                             r"\bappendix\b", r"\bsupplemental\b"]),
    ("back_matter",        [r"\bauthor\s+(information|contributions)\b",
                             r"\bcorresponding\s+author", r"\bfunding\b",
                             r"\backnowledgments?\b", r"\bnotes\b",
                             r"\bconflict[s]?\s+of\s+interest\b",
                             r"\bauthors\b"]),
    ("references",         [r"\breferences?\b", r"\bbibliography\b"]),
]


def classify_section_type(title: str) -> str:
    """Classify a section title into a standard IMRaD type."""
    clean = title.strip().lower()
    for stype, patterns in SECTION_TYPE_RULES:
        for pat in patterns:
            if re.search(pat, clean):
                return stype
    return "body"


def extract_figure_number(block: dict) -> str:
    """Extract figure/table number from caption text."""
    captions = block.get("chart_caption") or block.get("image_caption") or []
    text = " ".join(captions)
    m = re.search(r"(?:Figure|Fig\.?)\s*(\d+[A-Za-z]?)", text, re.IGNORECASE)
    if m:
        return f"Figure {m.group(1)}"
    m = re.search(r"(?:Table)\s*(\d+[A-Za-z]?)", text, re.IGNORECASE)
    if m:
        return f"Table {m.group(1)}"
    return ""


def detect_sections(blocks: list) -> list[dict]:
    """Find section boundaries from text_level or markdown-style headers."""
    sections = []
    current_section = {"section_id": "S01", "title": "Preamble", "start_block": 0,
                       "section_type": "preamble"}

    for b in blocks:
        if not b.get("keep"):
            continue
        t = b.get("type", "")
        text = b.get("text", "").strip()
        level = b.get("text_level")

        if level == 1:
            current_section = {"section_id": "S00", "title": text, "start_block": b["block_id"],
                               "section_type": "title"}
        elif level == 2 and t in TEXT_LIKE:
            sections.append(current_section)
            section_num = len(sections) + 1
            clean = text.replace("■", "").strip()
            current_section = {
                "section_id": f"S{section_num:02d}",
                "title": clean,
                "start_block": b["block_id"],
                "section_type": classify_section_type(clean),
            }

    sections.append(current_section)
    return sections


def classify_source_type(block: dict) -> str:
    t = block.get("type", "")
    if t in FIGURE_LIKE:
        return "figure"
    elif t in TABLE_LIKE:
        return "table"
    else:
        return "paragraph"


def build_source(paper_dir: Path, paper_id: str):
    inputs = stage_input_paths("source_normalization", str(paper_dir))
    outputs = stage_output_paths("source_normalization", str(paper_dir))
    raw_path = Path(inputs["raw_parse.json"])
    if not raw_path.exists():
        raise FileNotFoundError(f"{raw_path} not found. Run build_raw_parse.py first.")

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    blocks = raw["blocks"]
    kept = [b for b in blocks if b.get("keep")]

    sections = detect_sections(kept)

    # Assign each kept block to a section
    section_idx = 0
    for b in kept:
        while section_idx + 1 < len(sections) and b["block_id"] >= sections[section_idx + 1]["start_block"]:
            section_idx += 1
        section_info = sections[section_idx]
        b["_section_id"] = section_info["section_id"]
        b["_section_title"] = section_info["title"]
        b["_section_type"] = section_info["section_type"]

    # Override: detect abstract paragraphs in the preamble/title section
    for b in kept:
        if b["_section_type"] in ("title", "preamble") and ABSTRACT_PATTERN.search(b.get("text", "")):
            b["_section_type"] = "abstract"

    # Build source_blocks
    source_blocks = []
    sb_idx = 0
    for b in kept:
        sb_idx += 1
        src_type = classify_source_type(b)
        sb = {
            "block_id": f"{paper_id}_SB{sb_idx:04d}",
            "paper_id": paper_id,
            "source_block_id": b["block_id"],
            "page": (b.get("page_idx", 0) or 0) + 1,
            "section": b.get("_section_id", "?"),
            "section_title": b.get("_section_title", ""),
            "section_type": b.get("_section_type", "body"),
            "text": b.get("text", ""),
            "source_type": src_type,
            "figure_number": extract_figure_number(b) if src_type in ("figure", "table") else "",
            "img_path": b.get("img_path"),
            "image_caption": b.get("image_caption", []),
            "image_footnote": b.get("image_footnote", []),
            "chart_caption": b.get("chart_caption", []),
            "chart_footnote": b.get("chart_footnote", []),
            "mineru_type": b.get("type", ""),
        }
        source_blocks.append(sb)

    # Build document_structure
    paragraphs = []
    figures = []
    tables = []
    p_idx = 0
    for b in kept:
        st = classify_source_type(b)
        if st == "figure":
            captions = b.get("chart_caption") or b.get("image_caption") or []
            figures.append({
                "figure_id": f"{paper_id}_F{len(figures)+1:04d}",
                "source_block_id": b["block_id"],
                "page": (b.get("page_idx", 0) or 0) + 1,
                "figure_number": extract_figure_number(b),
                "caption_text": " ".join(captions) if captions else "",
                "img_path": b.get("img_path", ""),
                "section": b.get("_section_id", "?"),
                "section_type": b.get("_section_type", "body"),
            })
        elif st == "table":
            tables.append({
                "table_id": f"{paper_id}_T{len(tables)+1:04d}",
                "source_block_id": b["block_id"],
                "page": (b.get("page_idx", 0) or 0) + 1,
                "figure_number": extract_figure_number(b),
                "caption": "",
                "section": b.get("_section_id", "?"),
                "section_type": b.get("_section_type", "body"),
            })
        else:
            p_idx += 1
            paragraphs.append({
                "paragraph_id": f"{paper_id}_P{p_idx:04d}",
                "source_block_id": b["block_id"],
                "page": (b.get("page_idx", 0) or 0) + 1,
                "section": b.get("_section_id", "?"),
                "section_title": b.get("_section_title", ""),
                "section_type": b.get("_section_type", "body"),
                "text": b.get("text", ""),
                "text_level": b.get("text_level"),
                "mineru_type": b.get("type", ""),
            })

    doc_structure = {
        "paper_id": paper_id,
        "schema_version": "0.1.0",
        "contract_version": "2026-06-26",
        "sections": [{"section_id": s["section_id"], "title": s["title"],
                       "section_type": s["section_type"]} for s in sections],
        "paragraphs": paragraphs,
        "figures": figures,
        "tables": tables,
    }

    # Write outputs
    sbs_path = Path(outputs["source_blocks.jsonl"])
    sbs_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sbs_path, "w", encoding="utf-8") as f:
        for sb in source_blocks:
            f.write(json.dumps(sb, ensure_ascii=False) + "\n")

    doc_path = Path(outputs["document_structure.json"])
    doc_path.write_text(json.dumps(doc_structure, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  Sections: {len(sections)}")
    for s in sections:
        print(f"    {s['section_id']} [{s['section_type']:16s}] {s['title'][:60]}")
    print(f"  Source blocks: {len(source_blocks)} ({len(paragraphs)} paragraphs, {len(figures)} figures, {len(tables)} tables)")
    print(f"  Output: {sbs_path}")
    print(f"  Output: {doc_path}")

    return source_blocks, doc_structure


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/parsing/build_source.py <paper_run_dir> [paper_id]")
        sys.exit(1)

    paper_dir = Path(sys.argv[1]).resolve()
    paper_id = sys.argv[2] if len(sys.argv) > 2 else paper_dir.parent.name
    build_source(paper_dir, paper_id)


if __name__ == "__main__":
    main()
