"""
extract_evidence.py — Extract structured evidence units from source blocks using LLM.

Input:  02_source/source_blocks.jsonl + document_structure.json
Output: 03_evidence/evidence_units.jsonl
"""

import json
import os
import ssl
import sys
import time
import urllib.request
from pathlib import Path

# ---- LLM backend: direct HTTP (zero dependencies) ----


def load_prompt() -> str:
    prompt_path = Path(__file__).resolve().parents[2] / "prompts" / "evidence_extraction.txt"
    return prompt_path.read_text(encoding="utf-8")


def load_source_blocks(paper_dir: Path) -> list[dict]:
    path = paper_dir / "02_source" / "source_blocks.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run build_source.py first.")
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def group_blocks_for_extraction(blocks: list[dict], max_paras_per_group: int = 2) -> list[dict]:
    """Group consecutive paragraphs within the same section_type.
    Focus on high-value sections. Figures attach to nearest paragraph group.
    Groups are limited to max_paras_per_group consecutive paragraphs to keep
    context manageable for the LLM."""

    # Sections to extract from (exclude noise)
    extract_sections = {"abstract", "introduction", "methods", "results",
                        "discussion", "conclusion", "supplementary"}

    # First pass: collect paragraphs and figures in order, filtering noise
    items = []
    for b in blocks:
        st = b.get("section_type", "body")
        if st not in extract_sections:
            continue

        if b["source_type"] == "paragraph":
            text = b.get("text", "").strip()
            if not text:
                continue
            if b.get("mineru_type") == "text" and b.get("text_level") == 2:
                continue
            items.append({
                "kind": "paragraph",
                "section_type": st,
                "section_title": b.get("section_title", ""),
                "block_id": b["block_id"],
                "text": text,
            })
        elif b["source_type"] == "figure":
            captions = b.get("chart_caption") or b.get("image_caption") or []
            cap_text = " ".join(captions).strip()
            fig_num = b.get("figure_number", "")
            if cap_text:
                items.append({
                    "kind": "figure",
                    "section_type": st,
                    "section_title": b.get("section_title", ""),
                    "block_id": b["block_id"],
                    "text": f"[{fig_num}] {cap_text}" if fig_num else f"[Figure] {cap_text}",
                })

    # Second pass: build groups of up to max_paras_per_group paragraphs,
    # plus any adjacent figures
    groups = []
    current_paras = []
    current_ids = []
    current_section_type = None
    current_section_title = ""

    def flush_group():
        nonlocal current_paras, current_ids
        if current_paras:
            groups.append({
                "section_type": current_section_type,
                "section_title": current_section_title,
                "source_block_ids": list(current_ids),
                "text": "\n\n".join(current_paras),
            })
            current_paras = []
            current_ids = []

    for item in items:
        if item["kind"] == "paragraph":
            # Flush if section changed or group is full
            if (current_section_type != item["section_type"] or
                    len(current_paras) >= max_paras_per_group):
                flush_group()
            current_section_type = item["section_type"]
            current_section_title = item["section_title"]
            current_paras.append(item["text"])
            current_ids.append(item["block_id"])
        elif item["kind"] == "figure":
            # Attach figure to current group, or start a new one
            if not current_paras:
                current_section_type = item["section_type"]
                current_section_title = item["section_title"]
            current_paras.append(item["text"])
            current_ids.append(item["block_id"])

    flush_group()
    return groups


def build_extraction_prompt(groups: list[dict]) -> str:
    """Build a batch extraction prompt for all text groups."""
    parts = []
    for i, g in enumerate(groups):
        section_label = f"[{g['section_type']}] {g['section_title']}"
        parts.append(f"## Text Block {i+1}\n**Section:** {section_label}\n\n{g['text']}")

    return "\n\n---\n\n".join(parts)


def parse_llm_output(raw_output: str, groups: list[dict],
                     paper_id: str, paper_dir: Path,
                     id_offset: int = 0) -> list[dict]:
    """Parse LLM JSON output into evidence_unit records."""
    try:
        raw = raw_output.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:]) if lines[0].startswith("```") else raw
        if raw.endswith("```"):
            raw = raw[:raw.rfind("```")].strip()
        extracted = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  WARNING: Failed to parse LLM output as JSON: {e}")
        print(f"  Raw output (first 500 chars): {raw_output[:500]}")
        return []

    if not isinstance(extracted, list):
        extracted = [extracted]

    # Infer source_block_ids and section_type from content — simplified:
    # map each extracted unit to the first group that hasn't been used,
    # based on entity overlap. Fall back to sequential assignment.
    evidence_units = []
    for i, unit in enumerate(extracted):
        if not isinstance(unit, dict):
            continue
        # Simple sequential assignment for now
        group_idx = min(i, len(groups) - 1)
        group = groups[group_idx]

        eu = {
            "evidence_id": f"{paper_id}_E{id_offset + len(evidence_units)+1:04d}",
            "paper_id": paper_id,
            "source_block_ids": group["source_block_ids"],
            "evidence_type": unit.get("evidence_type", "?"),
            "source_text": unit.get("source_text", ""),
            "section_type": group["section_type"],
            "disease": unit.get("disease"),
            "thermogenesis_phenotype": unit.get("thermogenesis_phenotype"),
            "mechanism": unit.get("mechanism"),
            "entities": unit.get("entities", []),
            "detection_method": unit.get("detection_method"),
            "detection_category": unit.get("detection_category"),
            "modulation": unit.get("modulation"),
            "statistics": unit.get("statistics"),
            "study_design": unit.get("study_design"),
            "model_system": unit.get("model_system"),
            "score": None,
            "review_status": "pending",
        }
        evidence_units.append(eu)

    return evidence_units


def call_llm_api(system_prompt: str, user_prompt: str) -> str:
    """Call OpenAI-compatible chat API via direct HTTP."""
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("EVIDENCE_LLM_MODEL", "deepseek-chat")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set.")

    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": 32768,
    }).encode("utf-8")

    for attempt in range(5):
        try:
            req = urllib.request.Request(url, data=body, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            })
            ctx = ssl.create_default_context()
            resp = urllib.request.urlopen(req, context=ctx, timeout=180)
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            if not content:
                reasoning = data["choices"][0]["message"].get("reasoning_content", "")
                finish = data["choices"][0].get("finish_reason", "?")
                raise RuntimeError(
                    f"LLM returned empty content (finish_reason={finish}). "
                    f"Reasoning consumed: {len(reasoning)} chars."
                )
            return content
        except urllib.error.HTTPError as e:
            if e.code == 403 and attempt < 4:
                wait = min(30 * (2 ** attempt), 240)
                print(f"  Rate limited (403), waiting {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Max retries exceeded")


def extract_with_llm(groups: list[dict], paper_id: str,
                     paper_dir: Path) -> list[dict]:
    """Call LLM API to extract evidence from text groups."""
    system_prompt = load_prompt()

    # Split into batches (same as original successful run)
    max_chars = 8000
    batch_groups = []
    current_batch = []
    current_chars = 0
    for g in groups:
        g_chars = len(g["text"])
        if current_chars + g_chars > max_chars and current_batch:
            batch_groups.append(current_batch)
            current_batch = []
            current_chars = 0
        current_batch.append(g)
        current_chars += g_chars
    if current_batch:
        batch_groups.append(current_batch)

    all_units = []
    for batch_idx, batch in enumerate(batch_groups):
        batch_prompt = build_extraction_prompt(batch)
        print(f"  Batch {batch_idx+1}/{len(batch_groups)}: {len(batch)} groups, "
              f"{len(batch_prompt)} chars")

        raw = call_llm_api(system_prompt, batch_prompt)
        units = parse_llm_output(raw, batch, paper_id, paper_dir,
                                 id_offset=len(all_units))
        all_units.extend(units)
        print(f"    → {len(units)} evidence units extracted")

        if batch_idx < len(batch_groups) - 1:
            time.sleep(3)

    return all_units


def extract_mock(groups: list[dict], paper_id: str,
                 paper_dir: Path) -> list[dict]:
    """Mock extraction — produce placeholder evidence units for pipeline testing."""
    id_offset = 0
    evidence_units = []
    for g in groups:
        eu = {
            "evidence_id": f"{paper_id}_E{id_offset + len(evidence_units)+1:04d}",
            "paper_id": paper_id,
            "source_block_ids": g["source_block_ids"],
            "evidence_type": "disease_association",
            "source_text": g["text"][:200],
            "section_type": g["section_type"],
            "disease": None,
            "thermogenesis_phenotype": None,
            "mechanism": None,
            "entities": [],
            "detection_method": None,
            "detection_category": None,
            "modulation": None,
            "statistics": None,
            "study_design": None,
            "model_system": None,
            "score": None,
            "review_status": "pending",
        }
        evidence_units.append(eu)
    return evidence_units


def extract_evidence(paper_dir: Path, paper_id: str, mock: bool = False):
    blocks = load_source_blocks(paper_dir)
    groups = group_blocks_for_extraction(blocks)

    print(f"  Source blocks: {len(blocks)}")
    print(f"  Extraction groups: {len(groups)} (after filtering noise sections)")

    section_counts = {}
    for g in groups:
        st = g["section_type"]
        section_counts[st] = section_counts.get(st, 0) + 1
    for st, c in sorted(section_counts.items()):
        print(f"    {st}: {c} groups")

    if mock:
        print("  Mode: MOCK (placeholder evidence units)")
        evidence_units = extract_mock(groups, paper_id, paper_dir)
    else:
        print("  Mode: LLM")
        evidence_units = extract_with_llm(groups, paper_id, paper_dir)

    # Write output
    out_dir = paper_dir / "03_evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "evidence_units.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for eu in evidence_units:
            f.write(json.dumps(eu, ensure_ascii=False) + "\n")

    # Summary by evidence_type
    from collections import Counter
    type_counts = Counter(eu["evidence_type"] for eu in evidence_units)
    print(f"\n  Evidence units: {len(evidence_units)}")
    for et, c in type_counts.most_common():
        print(f"    {et}: {c}")

    print(f"  Output: {out_path}")
    return evidence_units


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/evidence/extract_evidence.py <paper_run_dir> [paper_id] [--mock]")
        sys.exit(1)

    paper_dir = Path(sys.argv[1]).resolve()
    paper_id = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else paper_dir.parent.name
    mock = "--mock" in sys.argv

    extract_evidence(paper_dir, paper_id, mock=mock)


if __name__ == "__main__":
    main()
