"""
build_raw_parse.py — Normalize MinerU content_list into raw_parse.json.

Input:  01_raw_parse/content_list.json + full.md
Output: 01_raw_parse/raw_parse.json
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.core.contracts import stage_output_paths

# All known MinerU BlockTypes from official docs
MINERU_TYPES = {
    "text", "title", "image", "image_body", "image_caption",
    "chart", "chart_body", "table", "table_body", "table_caption",
    "table_footnote", "caption", "ref_text", "header", "footer",
    "page_number", "page_footnote", "footnote", "aside_text",
    "interline_equation", "inline_equation", "code", "algorithm",
    "list", "list_text", "discarded",
}

# Types to keep as source blocks
KEEP_TYPES = {
    "text", "title", "list", "list_text",
    "interline_equation", "inline_equation", "code", "algorithm",
    "footnote", "aside_text",
    "image", "image_body", "image_caption",
    "chart", "chart_body",
    "table", "table_body", "table_caption", "table_footnote",
}

# Types to drop as noise
DROP_TYPES = {
    "header", "footer", "page_number", "page_footnote",
    "ref_text", "discarded",
}


def build_raw_parse(input_dir: Path, output_dir: Path, paper_id: str) -> dict:
    content_list_path = input_dir / "content_list.json"
    full_md_path = input_dir / "full.md"

    if not content_list_path.exists():
        raise FileNotFoundError(f"content_list.json not found at {content_list_path}")

    content_list = json.loads(content_list_path.read_text(encoding="utf-8"))
    full_md = full_md_path.read_text(encoding="utf-8") if full_md_path.exists() else ""

    blocks = []
    unknown_types = set()
    type_counts = {}

    for i, item in enumerate(content_list):
        t = item.get("type", "?")
        type_counts[t] = type_counts.get(t, 0) + 1

        if t not in MINERU_TYPES:
            unknown_types.add(t)

        block = {
            "block_id": f"{paper_id}_B{i+1:04d}",
            "type": t,
            "page_idx": item.get("page_idx"),
            "bbox": item.get("bbox"),
            "text": item.get("text", ""),
            "text_level": item.get("text_level"),
            "img_path": item.get("img_path"),
            "image_caption": item.get("image_caption", []),
            "image_footnote": item.get("image_footnote", []),
            "chart_caption": item.get("chart_caption", []),
            "chart_footnote": item.get("chart_footnote", []),
            "content": item.get("content", ""),
            "keep": t in KEEP_TYPES,
        }
        blocks.append(block)

    raw_parse = {
        "paper_id": paper_id,
        "schema_version": "0.1.0",
        "contract_version": "2026-06-26",
        "source": "MinerU",
        "total_blocks": len(blocks),
        "type_counts": type_counts,
        "kept_blocks": sum(1 for b in blocks if b["keep"]),
        "dropped_blocks": sum(1 for b in blocks if not b["keep"]),
        "unknown_types": sorted(unknown_types),
        "blocks": blocks,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "raw_parse.json"
    out_path.write_text(json.dumps(raw_parse, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  Blocks: {len(blocks)} total ({raw_parse['kept_blocks']} keep, {raw_parse['dropped_blocks']} drop)")
    print(f"  Types found: {json.dumps(type_counts)}")
    if unknown_types:
        print(f"  Unknown types: {unknown_types}")
    print(f"  Output: {out_path}")

    return raw_parse


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/parsing/build_raw_parse.py <paper_run_dir> [paper_id]")
        sys.exit(1)

    run_dir = Path(sys.argv[1]).resolve()
    paper_id = sys.argv[2] if len(sys.argv) > 2 else run_dir.parent.name

    outputs = stage_output_paths("raw_parse", str(run_dir))
    output_path = Path(outputs["raw_parse.json"])
    input_dir = output_path.parent

    build_raw_parse(input_dir, output_path.parent, paper_id)


if __name__ == "__main__":
    main()
